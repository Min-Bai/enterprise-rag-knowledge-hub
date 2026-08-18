from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ...database import get_db
from ...exceptions import DuplicateUsernameError, EmptyUserUpdateError, IncorrectPasswordError, InvalidCredentialsError, UserInactiveError, UserNotFoundError
from ...models.user import UserORM
from ...models.audit_log import AuditLogORM
from ...models.document import DocumentORM
from ...models.knowledge_base import KnowledgeBaseORM
from ...models.user_invitation import UserInvitationORM
from ...models.password_reset import PasswordResetORM
from ...models.password_reset_request import PasswordResetRequestORM
from ...models.registration_request import RegistrationRequestORM
from ...schemas.model_provider import ModelProviderUpsert
from ...schemas.user import AccountRequestReview, AdminUserCreate, InvitationCreate, PasswordChange, PasswordResetLinkCreate, UserLogin, UserProfileUpdate, UserResponse, UserRoleUpdate, UserUpdate
from ...services.auth_sessions import clear_refresh_cookie, issue_session, revoke_session, rotate_session, set_refresh_cookie
from ...services.users import change_password_service, create_user_from_password_hash_service, create_user_with_role_service, delete_user_service, login_user_service, update_my_profile_service, update_user_role_service, update_user_service
from ...services.audit_logs import write_audit_log
from ...services.email_delivery import EmailDeliveryError, send_password_reset_email
from ...services.model_providers import list_model_providers, upsert_model_provider
from ...celery_app import celery_app
from ...rate_limit import enforce_account_login_rate_limit, enforce_login_rate_limit
from ..common.response import ok
from ..dependencies import require_admin_access, require_admin_user

router = APIRouter()


def _admin_login(payload: UserLogin, request: Request, response: Response, db: Session):
    try:
        user = login_user_service(user_login=payload, db=db)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="invalid username or password")
    except UserInactiveError:
        raise HTTPException(status_code=403, detail="user is inactive")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin permission required")
    result, refresh = issue_session(user=user, audience="admin-api", request=request, db=db)
    result["csrf_token"] = set_refresh_cookie(response, refresh, "admin-api")
    return ok(result)


@router.post("/auth/login")
def login(payload: Annotated[UserLogin, Body()], request: Request, response: Response, _: None = Depends(enforce_login_rate_limit), db: Session = Depends(get_db)):
    enforce_account_login_rate_limit(payload.username)
    return _admin_login(payload, request, response, db)


@router.post("/auth/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    result, refresh_token = rotate_session(request=request, audience="admin-api", db=db)
    result["csrf_token"] = set_refresh_cookie(response, refresh_token, "admin-api")
    return ok(result)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, user: UserORM = Depends(require_admin_access), db: Session = Depends(get_db)):
    from ...security import decode_v1_token
    token = request.headers["authorization"].split(" ", 1)[1]
    session_id = str(decode_v1_token(token, expected_audience="admin-api", expected_type="access")["sid"])
    revoke_session(session_id=session_id, user_id=user.id, audience="admin-api", db=db)
    clear_refresh_cookie(response, "admin-api")


@router.get("/me")
def me(user: UserORM = Depends(require_admin_user)):
    return ok(UserResponse.model_validate(user, from_attributes=True))


@router.get("/model-providers")
def model_providers(
    db: Session = Depends(get_db),
    _: UserORM = Depends(require_admin_user),
):
    return ok(list_model_providers(db))


@router.put("/model-providers/{slug}")
def save_model_provider(
    slug: str,
    payload: ModelProviderUpsert,
    db: Session = Depends(get_db),
    admin: UserORM = Depends(require_admin_user),
):
    normalized_slug = slug.strip().lower()
    if not normalized_slug or not normalized_slug.replace("-", "").isalnum():
        raise HTTPException(status_code=422, detail="model provider slug is invalid")
    provider = upsert_model_provider(db, normalized_slug, payload)
    write_audit_log(
        actor_user_id=admin.id,
        action="admin.model_provider.updated",
        target_type="model_provider",
        target_id=None,
        knowledge_base_id=None,
        details={"slug": normalized_slug, "is_active": provider["is_active"]},
        db=db,
    )
    return ok(provider)


@router.patch("/me")
def update_me(payload: UserProfileUpdate, db: Session = Depends(get_db), user: UserORM = Depends(require_admin_user)):
    try:
        updated = update_my_profile_service(current_user=user, profile_update=payload, db=db)
    except DuplicateUsernameError:
        raise HTTPException(status_code=409, detail="username already exists")
    except EmptyUserUpdateError:
        raise HTTPException(status_code=422, detail="provide at least one field to update")
    return ok(UserResponse.model_validate(updated, from_attributes=True))


@router.patch("/me/password", status_code=204)
def change_me_password(payload: PasswordChange, db: Session = Depends(get_db), user: UserORM = Depends(require_admin_user)):
    try:
        change_password_service(current_user=user, password_change=payload, db=db)
    except IncorrectPasswordError:
        raise HTTPException(status_code=400, detail="old password is incorrect")


@router.get("/users")
def users(limit: int = 20, cursor: int | None = None, db: Session = Depends(get_db), _: UserORM = Depends(require_admin_user)):
    bounded_limit = min(max(limit, 1), 100)
    statement = select(UserORM).order_by(UserORM.id.desc()).limit(bounded_limit + 1)
    if cursor is not None:
        statement = statement.where(UserORM.id < cursor)
    rows = db.scalars(statement).all()
    has_more = len(rows) > bounded_limit
    items = rows[:bounded_limit]
    return ok({"items": [UserResponse.model_validate(item, from_attributes=True) for item in items], "page": {
        "next_cursor": items[-1].id if has_more and items else None,
        "has_more": has_more, "limit": bounded_limit,
    }})


@router.post("/users", status_code=201)
def create_user(payload: AdminUserCreate, db: Session = Depends(get_db), admin: UserORM = Depends(require_admin_user)):
    try:
        user = create_user_with_role_service(user=payload, role=payload.role, db=db)
    except DuplicateUsernameError:
        raise HTTPException(status_code=409, detail="username already exists")
    write_audit_log(actor_user_id=admin.id, action="admin.user.created", target_type="user", target_id=user.id,
                    knowledge_base_id=None, details={"role": user.role}, db=db)
    return ok(UserResponse.model_validate(user, from_attributes=True))


@router.patch("/users/{user_id}/role")
def update_role(user_id: int, payload: UserRoleUpdate, db: Session = Depends(get_db), admin: UserORM = Depends(require_admin_user)):
    if user_id == admin.id and payload.role != "admin":
        raise HTTPException(status_code=409, detail="admin cannot remove own admin role")
    try:
        user = update_user_role_service(user_id, payload, db)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    write_audit_log(actor_user_id=admin.id, action="admin.user.role_updated", target_type="user", target_id=user.id,
                    knowledge_base_id=None, details={"role": user.role}, db=db)
    return ok(UserResponse.model_validate(user, from_attributes=True))


@router.patch("/users/{user_id}/status")
def update_status(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), admin: UserORM = Depends(require_admin_user)):
    if payload.is_active is None:
        raise HTTPException(status_code=422, detail="is_active is required")
    if user_id == admin.id and not payload.is_active:
        raise HTTPException(status_code=409, detail="admin cannot deactivate own account")
    try:
        user = update_user_service(user_id, UserUpdate(is_active=payload.is_active), db)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    write_audit_log(actor_user_id=admin.id, action="admin.user.status_updated", target_type="user", target_id=user.id,
                    knowledge_base_id=None, details={"is_active": user.is_active}, db=db)
    return ok(UserResponse.model_validate(user, from_attributes=True))


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), admin: UserORM = Depends(require_admin_user)):
    if user_id == admin.id:
        raise HTTPException(status_code=409, detail="admin cannot delete own account")
    try:
        delete_user_service(user_id, db)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    write_audit_log(actor_user_id=admin.id, action="admin.user.deleted", target_type="user", target_id=user_id,
                    knowledge_base_id=None, details=None, db=db)


@router.post("/users/{user_id}/password-reset", status_code=201)
def create_password_reset_link(
    user_id: int,
    payload: PasswordResetLinkCreate,
    db: Session = Depends(get_db),
    admin: UserORM = Depends(require_admin_user),
):
    user = db.get(UserORM, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if not user.is_active:
        raise HTTPException(status_code=409, detail="inactive user cannot reset password")

    now = datetime.now(UTC).replace(tzinfo=None)
    db.execute(
        update(PasswordResetORM)
        .where(
            PasswordResetORM.user_id == user.id,
            PasswordResetORM.used_at.is_(None),
            PasswordResetORM.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    token = token_urlsafe(32)
    reset = PasswordResetORM(
        user_id=user.id,
        created_by_user_id=admin.id,
        token_hash=sha256(token.encode("utf-8")).hexdigest(),
        expires_at=now + timedelta(hours=payload.expires_in_hours),
    )
    db.add(reset)
    db.flush()
    write_audit_log(
        actor_user_id=admin.id,
        action="admin.password_reset.created",
        target_type="password_reset",
        target_id=None,
        knowledge_base_id=None,
        details={"password_reset_id": reset.id, "user_id": user.id},
        db=db,
        commit=False,
    )
    db.commit()
    return ok({"expires_at": reset.expires_at, "reset_token": token})


def _registration_request_response(item: RegistrationRequestORM) -> dict:
    return {
        "id": item.id,
        "username": item.username,
        "email": item.email,
        "status": item.status,
        "reviewed_by_user_id": item.reviewed_by_user_id,
        "reviewed_at": item.reviewed_at,
        "rejection_reason": item.rejection_reason,
        "created_at": item.created_at,
    }


@router.get("/registration-requests")
def registration_requests(db: Session = Depends(get_db), _: UserORM = Depends(require_admin_user)):
    rows = db.scalars(
        select(RegistrationRequestORM).order_by(RegistrationRequestORM.created_at.desc()).limit(100)
    ).all()
    return ok([_registration_request_response(item) for item in rows])


@router.post("/registration-requests/{request_id}/approve", status_code=201)
def approve_registration_request(
    request_id: str,
    db: Session = Depends(get_db),
    admin: UserORM = Depends(require_admin_user),
):
    request_item = db.scalar(
        select(RegistrationRequestORM).where(RegistrationRequestORM.id == request_id).with_for_update()
    )
    if request_item is None:
        raise HTTPException(status_code=404, detail="registration request not found")
    if request_item.status != "pending":
        raise HTTPException(status_code=409, detail="registration request has already been reviewed")
    if db.scalar(select(UserORM.id).where(
        (UserORM.username == request_item.username) | (func.lower(UserORM.email) == request_item.email)
    )) is not None:
        raise HTTPException(status_code=409, detail="username or email already exists")
    try:
        user = create_user_from_password_hash_service(
            username=request_item.username,
            email=request_item.email,
            password_hash=request_item.password_hash,
            db=db,
            commit=False,
        )
    except DuplicateUsernameError:
        raise HTTPException(status_code=409, detail="username or email already exists")
    now = datetime.now(UTC).replace(tzinfo=None)
    request_item.status = "approved"
    request_item.reviewed_by_user_id = admin.id
    request_item.reviewed_at = now
    write_audit_log(
        actor_user_id=admin.id,
        action="admin.registration_request.approved",
        target_type="registration_request",
        target_id=None,
        knowledge_base_id=None,
        details={"registration_request_id": request_item.id, "user_id": user.id},
        db=db,
        commit=False,
    )
    db.commit()
    return ok(UserResponse.model_validate(user, from_attributes=True))


@router.post("/registration-requests/{request_id}/reject", status_code=204)
def reject_registration_request(
    request_id: str,
    payload: AccountRequestReview,
    db: Session = Depends(get_db),
    admin: UserORM = Depends(require_admin_user),
):
    request_item = db.scalar(
        select(RegistrationRequestORM).where(RegistrationRequestORM.id == request_id).with_for_update()
    )
    if request_item is None:
        raise HTTPException(status_code=404, detail="registration request not found")
    if request_item.status != "pending":
        raise HTTPException(status_code=409, detail="registration request has already been reviewed")
    request_item.status = "rejected"
    request_item.reviewed_by_user_id = admin.id
    request_item.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    request_item.rejection_reason = payload.rejection_reason.strip() if payload.rejection_reason else None
    write_audit_log(
        actor_user_id=admin.id,
        action="admin.registration_request.rejected",
        target_type="registration_request",
        target_id=None,
        knowledge_base_id=None,
        details={"registration_request_id": request_item.id},
        db=db,
        commit=False,
    )
    db.commit()


@router.get("/password-reset-requests")
def password_reset_requests(db: Session = Depends(get_db), _: UserORM = Depends(require_admin_user)):
    rows = db.scalars(
        select(PasswordResetRequestORM).order_by(PasswordResetRequestORM.created_at.desc()).limit(100)
    ).all()
    return ok([{
        "id": item.id, "email": item.email, "status": item.status,
        "reviewed_by_user_id": item.reviewed_by_user_id, "reviewed_at": item.reviewed_at,
        "created_at": item.created_at,
    } for item in rows])


@router.delete("/registration-requests/{request_id}", status_code=204)
def delete_registration_request(
    request_id: str,
    db: Session = Depends(get_db),
    admin: UserORM = Depends(require_admin_user),
):
    request_item = db.get(RegistrationRequestORM, request_id)
    if request_item is None:
        raise HTTPException(status_code=404, detail="registration request not found")
    write_audit_log(
        actor_user_id=admin.id,
        action="admin.registration_request.deleted",
        target_type="registration_request",
        target_id=None,
        knowledge_base_id=None,
        details={"registration_request_id": request_item.id, "username": request_item.username},
        db=db,
        commit=False,
    )
    db.delete(request_item)
    db.commit()


@router.delete("/password-reset-requests/{request_id}", status_code=204)
def delete_password_reset_request(
    request_id: str,
    db: Session = Depends(get_db),
    admin: UserORM = Depends(require_admin_user),
):
    request_item = db.get(PasswordResetRequestORM, request_id)
    if request_item is None:
        raise HTTPException(status_code=404, detail="password reset request not found")
    write_audit_log(
        actor_user_id=admin.id,
        action="admin.password_reset_request.deleted",
        target_type="password_reset_request",
        target_id=None,
        knowledge_base_id=None,
        details={"password_reset_request_id": request_item.id, "email": request_item.email},
        db=db,
        commit=False,
    )
    db.delete(request_item)
    db.commit()


@router.post("/password-reset-requests/{request_id}/approve", status_code=201)
def approve_password_reset_request(
    request_id: str,
    payload: PasswordResetLinkCreate,
    db: Session = Depends(get_db),
    admin: UserORM = Depends(require_admin_user),
):
    request_item = db.scalar(
        select(PasswordResetRequestORM).where(PasswordResetRequestORM.id == request_id).with_for_update()
    )
    if request_item is None:
        raise HTTPException(status_code=404, detail="password reset request not found")
    if request_item.status != "pending":
        raise HTTPException(status_code=409, detail="password reset request has already been reviewed")
    user = db.scalar(select(UserORM).where(func.lower(UserORM.email) == request_item.email))
    if user is None or not user.is_active:
        raise HTTPException(status_code=409, detail="inactive user cannot reset password")
    now = datetime.now(UTC).replace(tzinfo=None)
    db.execute(update(PasswordResetORM).where(
        PasswordResetORM.user_id == user.id,
        PasswordResetORM.used_at.is_(None),
        PasswordResetORM.revoked_at.is_(None),
    ).values(revoked_at=now))
    token = token_urlsafe(32)
    reset = PasswordResetORM(
        user_id=user.id, created_by_user_id=admin.id,
        token_hash=sha256(token.encode("utf-8")).hexdigest(),
        expires_at=now + timedelta(hours=payload.expires_in_hours),
    )
    request_item.status = "approved"
    request_item.reviewed_by_user_id = admin.id
    request_item.reviewed_at = now
    db.add(reset)
    db.flush()
    write_audit_log(
        actor_user_id=admin.id,
        action="admin.password_reset_request.approved",
        target_type="password_reset_request",
        target_id=None,
        knowledge_base_id=None,
        details={"password_reset_request_id": request_item.id, "user_id": user.id},
        db=db,
        commit=False,
    )
    try:
        send_password_reset_email(
            recipient_email=request_item.email,
            reset_token=token,
            expires_at=reset.expires_at,
        )
    except EmailDeliveryError:
        db.rollback()
        raise HTTPException(status_code=503, detail="password reset email delivery failed")

    db.commit()
    return ok({"expires_at": reset.expires_at, "delivery": "email"})


def _invitation_response(invitation: UserInvitationORM) -> dict:
    return {
        "id": invitation.id,
        "email": invitation.email,
        "expires_at": invitation.expires_at,
        "accepted_at": invitation.accepted_at,
        "revoked_at": invitation.revoked_at,
        "created_at": invitation.created_at,
        "created_by_user_id": invitation.created_by_user_id,
    }


@router.get("/invitations")
def invitations(db: Session = Depends(get_db), _: UserORM = Depends(require_admin_user)):
    rows = db.scalars(
        select(UserInvitationORM).order_by(UserInvitationORM.created_at.desc()).limit(100)
    ).all()
    return ok([_invitation_response(item) for item in rows])


@router.post("/invitations", status_code=201)
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    admin: UserORM = Depends(require_admin_user),
):
    token = token_urlsafe(32)
    now = datetime.now(UTC).replace(tzinfo=None)
    invitation = UserInvitationORM(
        email=payload.email,
        token_hash=sha256(token.encode("utf-8")).hexdigest(),
        created_by_user_id=admin.id,
        expires_at=now + timedelta(hours=payload.expires_in_hours),
    )
    db.add(invitation)
    db.flush()
    write_audit_log(
        actor_user_id=admin.id,
        action="admin.invitation.created",
        target_type="user_invitation",
        target_id=None,
        knowledge_base_id=None,
        details={"invitation_id": invitation.id, "email": invitation.email},
        db=db,
        commit=False,
    )
    db.commit()
    db.refresh(invitation)
    return ok({**_invitation_response(invitation), "invitation_token": token})


@router.delete("/invitations/{invitation_id}", status_code=204)
def revoke_invitation(
    invitation_id: str,
    db: Session = Depends(get_db),
    admin: UserORM = Depends(require_admin_user),
):
    invitation = db.get(UserInvitationORM, invitation_id)
    if invitation is None:
        raise HTTPException(status_code=404, detail="invitation not found")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="accepted invitation cannot be revoked")
    if invitation.revoked_at is None:
        invitation.revoked_at = datetime.now(UTC).replace(tzinfo=None)
        write_audit_log(
            actor_user_id=admin.id,
            action="admin.invitation.revoked",
            target_type="user_invitation",
            target_id=None,
            knowledge_base_id=None,
            details={"invitation_id": invitation.id, "email": invitation.email},
            db=db,
            commit=False,
        )
        db.commit()


@router.get("/operations/worker-status")
def worker_status(_: UserORM = Depends(require_admin_user)):
    inspector = celery_app.control.inspect(timeout=1.0)
    registered = inspector.ping() or {}
    active = inspector.active() or {}
    reserved = inspector.reserved() or {}
    return ok({
        "registered_workers": sorted(registered.keys()),
        "active_tasks": sum(len(tasks) for tasks in active.values()),
        "reserved_tasks": sum(len(tasks) for tasks in reserved.values()),
    })


@router.get("/operations/jobs")
def document_jobs(limit: int = 20, db: Session = Depends(get_db), _: UserORM = Depends(require_admin_user)):
    status_counts = dict(db.execute(
        select(DocumentORM.status, func.count()).group_by(DocumentORM.status)
    ).all())
    recent = db.scalars(
        select(DocumentORM).where(DocumentORM.status.in_(("uploaded", "processing", "failed")))
        .order_by(DocumentORM.created_at.desc()).limit(min(max(limit, 1), 100))
    ).all()
    return ok({
        "status_counts": status_counts,
        "recent": [{"id": item.id, "filename": item.filename, "status": item.status,
                    "error_message": item.error_message, "created_at": item.created_at,
                    "knowledge_base_id": item.knowledge_base_id} for item in recent],
    })


@router.get("/audit-logs")
def audit_logs(limit: int = 50, db: Session = Depends(get_db), _: UserORM = Depends(require_admin_user)):
    rows = db.execute(select(AuditLogORM, UserORM.username).join(UserORM, UserORM.id == AuditLogORM.actor_user_id)
                      .order_by(AuditLogORM.id.desc()).limit(min(max(limit, 1), 100))).all()
    return ok([{ "id": item.id, "actor_user_id": item.actor_user_id, "actor_username": username, "action": item.action,
                "target_type": item.target_type, "target_id": item.target_id,
                "details": item.details, "created_at": item.created_at } for item, username in rows])


@router.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db), _: UserORM = Depends(require_admin_user)):
    return ok({
        "users": db.scalar(select(func.count()).select_from(UserORM)),
        "knowledge_bases": db.scalar(select(func.count()).select_from(KnowledgeBaseORM)),
        "documents": db.scalar(select(func.count()).select_from(DocumentORM)),
        "ready_documents": db.scalar(select(func.count()).select_from(DocumentORM).where(DocumentORM.status == "ready")),
    })

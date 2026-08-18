from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...database import get_db
from ...config import ALLOW_REGISTRATION_REQUESTS
from ...exceptions import DuplicateUsernameError, InvalidCredentialsError, UserInactiveError
from ...models.user import UserORM
from ...models.user_invitation import UserInvitationORM
from ...models.password_reset import PasswordResetORM
from ...models.password_reset_request import PasswordResetRequestORM
from ...models.registration_request import RegistrationRequestORM
from ...schemas.user import InvitationAccept, PasswordResetConfirm, PasswordResetRequestCreate, RefreshTokenRequest, RegistrationRequestCreate, UserCreate, UserLogin, UserResponse
from ...security import hash_password
from ...services.audit_logs import write_audit_log
from ...services.auth_sessions import issue_session, revoke_session, rotate_session
from ...services.users import create_user_service, login_user_service
from ...rate_limit import enforce_account_login_rate_limit, enforce_login_rate_limit
from ..common.response import ok
from ..dependencies import require_client_access

router = APIRouter()


@router.get("/auth/registration-status")
def registration_status():
    return ok({"enabled": ALLOW_REGISTRATION_REQUESTS, "approval_required": True})


@router.post("/auth/register", status_code=202)
def register(payload: RegistrationRequestCreate, _: None = Depends(enforce_login_rate_limit), db: Session = Depends(get_db)):
    if not ALLOW_REGISTRATION_REQUESTS:
        raise HTTPException(status_code=403, detail="registration requests are disabled")
    username_exists = db.scalar(select(UserORM.id).where(UserORM.username == payload.username))
    email_exists = db.scalar(select(UserORM.id).where(func.lower(UserORM.email) == payload.email))
    request_exists = db.scalar(select(RegistrationRequestORM.id).where(
        RegistrationRequestORM.status == "pending",
        (RegistrationRequestORM.username == payload.username) | (RegistrationRequestORM.email == payload.email),
    ))
    if username_exists or email_exists:
        raise HTTPException(status_code=409, detail="username or email already exists")
    if request_exists:
        raise HTTPException(status_code=409, detail="registration request already pending")
    db.add(RegistrationRequestORM(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    ))
    db.commit()
    return ok({"status": "pending"})


@router.post("/auth/password-reset-request", status_code=202)
def request_password_reset(
    payload: PasswordResetRequestCreate,
    _: None = Depends(enforce_login_rate_limit),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(UserORM).where(func.lower(UserORM.email) == payload.email))
    if user is not None and user.is_active:
        existing = db.scalar(select(PasswordResetRequestORM.id).where(
            PasswordResetRequestORM.email == payload.email,
            PasswordResetRequestORM.status == "pending",
        ))
        if existing is None:
            db.add(PasswordResetRequestORM(email=payload.email))
            db.commit()
    # Do not reveal whether an address belongs to an account.
    return ok({"status": "pending"})


@router.post("/auth/accept-invitation", status_code=201)
def accept_invitation(
    payload: InvitationAccept,
    _: None = Depends(enforce_login_rate_limit),
    db: Session = Depends(get_db),
):
    if not payload.email:
        raise HTTPException(status_code=422, detail="email is required")

    email = payload.email.strip().lower()
    token_hash = sha256(payload.invitation_token.encode("utf-8")).hexdigest()
    invitation = db.scalar(
        select(UserInvitationORM)
        .where(UserInvitationORM.token_hash == token_hash)
        .with_for_update()
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    if invitation is None or invitation.revoked_at is not None or invitation.accepted_at is not None:
        raise HTTPException(status_code=400, detail="invitation is invalid")
    if invitation.expires_at < now:
        raise HTTPException(status_code=400, detail="invitation has expired")
    if invitation.email != email:
        raise HTTPException(status_code=400, detail="invitation email does not match")
    if db.scalar(select(UserORM.id).where(func.lower(UserORM.email) == email)) is not None:
        raise HTTPException(status_code=409, detail="email already exists")

    try:
        user = create_user_service(
            user=UserCreate(username=payload.username, password=payload.password, email=email),
            db=db,
            commit=False,
        )
    except DuplicateUsernameError:
        raise HTTPException(status_code=409, detail="username already exists")

    invitation.accepted_at = now
    write_audit_log(
        actor_user_id=user.id,
        action="client.invitation.accepted",
        target_type="user_invitation",
        target_id=None,
        knowledge_base_id=None,
        details={"invitation_id": invitation.id},
        db=db,
        commit=False,
    )
    db.commit()
    return ok(UserResponse.model_validate(user, from_attributes=True))


@router.post("/auth/reset-password", status_code=204)
def reset_password(
    payload: PasswordResetConfirm,
    _: None = Depends(enforce_login_rate_limit),
    db: Session = Depends(get_db),
):
    token_hash = sha256(payload.reset_token.encode("utf-8")).hexdigest()
    reset = db.scalar(
        select(PasswordResetORM)
        .where(PasswordResetORM.token_hash == token_hash)
        .with_for_update()
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    if reset is None or reset.used_at is not None or reset.revoked_at is not None:
        raise HTTPException(status_code=400, detail="password reset is invalid")
    if reset.expires_at < now:
        raise HTTPException(status_code=400, detail="password reset has expired")
    user = db.get(UserORM, reset.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="password reset is invalid")

    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    reset.used_at = now
    write_audit_log(
        actor_user_id=user.id,
        action="client.password_reset.completed",
        target_type="password_reset",
        target_id=None,
        knowledge_base_id=None,
        details={"password_reset_id": reset.id},
        db=db,
        commit=False,
    )
    db.commit()


@router.post("/auth/login")
def login(payload: Annotated[UserLogin, Body()], request: Request, response: Response, _: None = Depends(enforce_login_rate_limit), db: Session = Depends(get_db)):
    enforce_account_login_rate_limit(payload.username)
    try:
        user = login_user_service(user_login=payload, db=db)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="invalid username or password")
    except UserInactiveError:
        raise HTTPException(status_code=403, detail="user is inactive")
    result, refresh = issue_session(user=user, audience="client-api", request=request, db=db)
    result["refresh_token"] = refresh
    return ok(result)


@router.post("/auth/refresh")
def refresh(payload: Annotated[RefreshTokenRequest, Body()], request: Request, response: Response, db: Session = Depends(get_db)):
    result, refresh_token = rotate_session(request=request, audience="client-api", refresh_token=payload.refresh_token, db=db)
    result["refresh_token"] = refresh_token
    return ok(result)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, user: UserORM = Depends(require_client_access), db: Session = Depends(get_db)):
    from ...security import decode_v1_token
    token = request.headers["authorization"].split(" ", 1)[1]
    session_id = str(decode_v1_token(token, expected_audience="client-api", expected_type="access")["sid"])
    revoke_session(session_id=session_id, user_id=user.id, audience="client-api", db=db)


@router.get("/me")
def me(user: UserORM = Depends(require_client_access)):
    return ok(UserResponse.model_validate(user, from_attributes=True))

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...database import get_db
from ...exceptions import InvalidCredentialsError, UserInactiveError, UserNotFoundError
from ...models.user import UserORM
from ...models.audit_log import AuditLogORM
from ...models.document import DocumentORM
from ...models.knowledge_base import KnowledgeBaseORM
from ...schemas.user import UserLogin, UserResponse, UserRoleUpdate, UserUpdate
from ...services.auth_sessions import clear_refresh_cookie, issue_session, revoke_session, rotate_session, set_refresh_cookie
from ...services.users import login_user_service, update_user_role_service, update_user_service
from ...services.audit_logs import write_audit_log
from ...celery_app import celery_app
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
def login(payload: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
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


@router.patch("/users/{user_id}/role")
def update_role(user_id: int, payload: UserRoleUpdate, db: Session = Depends(get_db), admin: UserORM = Depends(require_admin_user)):
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
    try:
        user = update_user_service(user_id, UserUpdate(is_active=payload.is_active), db)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    write_audit_log(actor_user_id=admin.id, action="admin.user.status_updated", target_type="user", target_id=user.id,
                    knowledge_base_id=None, details={"is_active": user.is_active}, db=db)
    return ok(UserResponse.model_validate(user, from_attributes=True))


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


@router.get("/audit-logs")
def audit_logs(limit: int = 50, db: Session = Depends(get_db), _: UserORM = Depends(require_admin_user)):
    rows = db.scalars(select(AuditLogORM).order_by(AuditLogORM.id.desc()).limit(min(max(limit, 1), 100))).all()
    return ok([{ "id": item.id, "actor_user_id": item.actor_user_id, "action": item.action,
                "target_type": item.target_type, "target_id": item.target_id,
                "details": item.details, "created_at": item.created_at } for item in rows])


@router.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db), _: UserORM = Depends(require_admin_user)):
    return ok({
        "users": db.scalar(select(func.count()).select_from(UserORM)),
        "knowledge_bases": db.scalar(select(func.count()).select_from(KnowledgeBaseORM)),
        "documents": db.scalar(select(func.count()).select_from(DocumentORM)),
        "ready_documents": db.scalar(select(func.count()).select_from(DocumentORM).where(DocumentORM.status == "ready")),
    })

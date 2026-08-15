from datetime import UTC, datetime
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...database import get_db
from ...config import ALLOW_SELF_REGISTRATION
from ...exceptions import DuplicateUsernameError, InvalidCredentialsError, UserInactiveError
from ...models.user import UserORM
from ...models.user_invitation import UserInvitationORM
from ...schemas.user import InvitationAccept, UserCreate, UserLogin, UserResponse
from ...services.audit_logs import write_audit_log
from ...services.auth_sessions import clear_refresh_cookie, issue_session, revoke_session, rotate_session, set_refresh_cookie
from ...services.users import create_user_service, login_user_service
from ...rate_limit import enforce_login_rate_limit
from ..common.response import ok
from ..dependencies import require_client_access

router = APIRouter()


@router.get("/auth/registration-status")
def registration_status():
    return ok({"enabled": ALLOW_SELF_REGISTRATION})


@router.post("/auth/register", status_code=201)
def register(payload: UserCreate, _: None = Depends(enforce_login_rate_limit), db: Session = Depends(get_db)):
    if not ALLOW_SELF_REGISTRATION:
        raise HTTPException(status_code=403, detail="self registration is disabled")
    try:
        user = create_user_service(user=payload, db=db)
    except DuplicateUsernameError:
        raise HTTPException(status_code=409, detail="username already exists")
    return ok(UserResponse.model_validate(user, from_attributes=True))


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


@router.post("/auth/login")
def login(payload: UserLogin, request: Request, response: Response, _: None = Depends(enforce_login_rate_limit), db: Session = Depends(get_db)):
    try:
        user = login_user_service(user_login=payload, db=db)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="invalid username or password")
    except UserInactiveError:
        raise HTTPException(status_code=403, detail="user is inactive")
    result, refresh = issue_session(user=user, audience="client-api", request=request, db=db)
    result["csrf_token"] = set_refresh_cookie(response, refresh, "client-api")
    return ok(result)


@router.post("/auth/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    result, refresh_token = rotate_session(request=request, audience="client-api", db=db)
    result["csrf_token"] = set_refresh_cookie(response, refresh_token, "client-api")
    return ok(result)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, user: UserORM = Depends(require_client_access), db: Session = Depends(get_db)):
    from ...security import decode_v1_token
    token = request.headers["authorization"].split(" ", 1)[1]
    session_id = str(decode_v1_token(token, expected_audience="client-api", expected_type="access")["sid"])
    revoke_session(session_id=session_id, user_id=user.id, audience="client-api", db=db)
    clear_refresh_cookie(response, "client-api")


@router.get("/me")
def me(user: UserORM = Depends(require_client_access)):
    return ok(UserResponse.model_validate(user, from_attributes=True))

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ...database import get_db
from ...config import ALLOW_SELF_REGISTRATION
from ...exceptions import DuplicateUsernameError, InvalidCredentialsError, UserInactiveError
from ...models.user import UserORM
from ...schemas.user import UserCreate, UserLogin, UserResponse
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

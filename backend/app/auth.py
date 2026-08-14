from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models.user import UserORM
from .security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)

def raise_unauthorized(detail: str):
    raise HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise_unauthorized("missing token")

    if credentials.scheme.lower() != "bearer":
        raise_unauthorized("invalid token")

    try:
        user_id, token_version = decode_access_token(
    credentials.credentials
)
    except ValueError:
        raise_unauthorized("invalid or expired token")

    user = db.get(UserORM, user_id)
    if (
    user is None
    or not user.is_active
    or user.token_version != token_version
):
        raise_unauthorized("invalid token")

    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserORM | None:
    if credentials is None:
        return None
    return get_current_user(credentials=credentials, db=db)

def require_admin(
    current_user: UserORM = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="admin permission required",
        )

    return current_user

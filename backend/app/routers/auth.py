from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..exceptions import InvalidCredentialsError, UserInactiveError
from ..schemas.user import UserLogin
from ..services.users import login_user_service
from ..security import create_access_token
from ..schemas.auth import TokenResponse
from ..rate_limit import enforce_login_rate_limit


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    user_login: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_login_rate_limit),
):
    try:
        user = login_user_service(user_login=user_login, db=db)
        return {
            "access_token": create_access_token(
    user_id=user.id,
    token_version=user.token_version,
),
            "token_type": "bearer",
        }
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=401,
            detail="invalid username or password",
        )
    except UserInactiveError:
        raise HTTPException(
            status_code=403,
            detail="user is inactive",
        )

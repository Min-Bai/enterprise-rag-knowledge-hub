from typing import Literal

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import UserORM
from ..services.auth_sessions import get_v1_current_user

bearer_scheme = HTTPBearer(auto_error=False)


def _current_for(audience: Literal["client-api", "admin-api"]):
    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        db: Session = Depends(get_db),
    ) -> UserORM:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="missing access token", headers={"WWW-Authenticate": "Bearer"})
        user, _ = get_v1_current_user(token=credentials.credentials, audience=audience, db=db)
        return user
    return dependency


require_client_access = _current_for("client-api")
require_admin_access = _current_for("admin-api")


def require_admin_user(user: UserORM = Depends(require_admin_access)) -> UserORM:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin permission required")
    return user

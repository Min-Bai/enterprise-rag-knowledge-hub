from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from .config import (
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_SECRET_KEY,
)
import jwt

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)

def create_access_token(user_id: int, token_version: int) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "tv": token_version,
        "exp": expire_at,
    }
    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

def decode_access_token(token: str) -> tuple[int, int]:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.InvalidTokenError:
        raise ValueError("invalid access token")

    user_id_text = payload.get("sub")
    if not isinstance(user_id_text, str) or not user_id_text.isdigit():
        raise ValueError("invalid access token")
    
    token_version = payload.get("tv")
    if not isinstance(token_version, int) or token_version < 0:
        raise ValueError("invalid access token")

    return int(user_id_text), token_version
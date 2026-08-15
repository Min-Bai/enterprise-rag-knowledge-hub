from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4
from .config import (
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_SECRET_KEY,
    ADMIN_ACCESS_EXPIRE_MINUTES,
    ADMIN_REFRESH_EXPIRE_DAYS,
    CLIENT_ACCESS_EXPIRE_MINUTES,
    CLIENT_REFRESH_EXPIRE_DAYS,
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


def hash_token_identifier(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def create_v1_token(
    *, user_id: int, token_version: int, session_id: str, audience: str, token_type: str
) -> tuple[str, int, str]:
    if audience not in {"client-api", "admin-api"}:
        raise ValueError("invalid token audience")
    if token_type not in {"access", "refresh"}:
        raise ValueError("invalid token type")
    minutes = (
        CLIENT_ACCESS_EXPIRE_MINUTES if audience == "client-api" else ADMIN_ACCESS_EXPIRE_MINUTES
    )
    lifetime = timedelta(minutes=minutes) if token_type == "access" else timedelta(
        days=CLIENT_REFRESH_EXPIRE_DAYS if audience == "client-api" else ADMIN_REFRESH_EXPIRE_DAYS
    )
    expires_at = datetime.now(timezone.utc) + lifetime
    jti = token_urlsafe(32)
    token = jwt.encode(
        {
            "sub": str(user_id), "sid": session_id, "typ": token_type,
            "aud": audience, "jti": jti, "tv": token_version,
            "iat": datetime.now(timezone.utc), "exp": expires_at,
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    return token, int(lifetime.total_seconds()), jti


def create_session_identifier() -> str:
    return str(uuid4())


def decode_v1_token(token: str, *, expected_audience: str, expected_type: str) -> dict[str, object]:
    try:
        payload = jwt.decode(
            token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], audience=expected_audience
        )
    except jwt.InvalidTokenError as exc:
        raise ValueError("invalid token") from exc
    required = ("sub", "sid", "jti", "tv", "typ")
    if any(key not in payload for key in required) or payload["typ"] != expected_type:
        raise ValueError("invalid token")
    if not isinstance(payload["sub"], str) or not payload["sub"].isdigit():
        raise ValueError("invalid token")
    if not isinstance(payload["tv"], int) or payload["tv"] < 0:
        raise ValueError("invalid token")
    return payload

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

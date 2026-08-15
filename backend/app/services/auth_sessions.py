from datetime import UTC, datetime, timedelta
from hashlib import sha256

from fastapi import HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import ADMIN_REFRESH_EXPIRE_DAYS, AUTH_COOKIE_SECURE, CLIENT_REFRESH_EXPIRE_DAYS
from ..models.auth_session import AuthSessionORM
from ..models.user import UserORM
from ..security import create_session_identifier, create_v1_token, decode_v1_token, hash_token_identifier
from .audit_logs import write_audit_log


AUDIENCES = {"client-api", "admin-api"}


def _utcnow() -> datetime:
    # Existing MySQL columns are timezone-naive; use an explicit UTC instant
    # without relying on deprecated datetime.utcnow().
    return datetime.now(UTC).replace(tzinfo=None)


def _cookie_name(audience: str) -> str:
    return "rag_client_refresh" if audience == "client-api" else "rag_admin_refresh"


def _cookie_path(audience: str) -> str:
    return "/api/v1/client/auth" if audience == "client-api" else "/api/v1/admin/auth"


def _hash_request_value(value: str | None) -> str | None:
    return sha256(value.encode("utf-8")).hexdigest() if value else None


def _refresh_days(audience: str) -> int:
    return CLIENT_REFRESH_EXPIRE_DAYS if audience == "client-api" else ADMIN_REFRESH_EXPIRE_DAYS


def issue_session(*, user: UserORM, audience: str, request: Request, db: Session) -> tuple[dict[str, object], str]:
    if audience not in AUDIENCES:
        raise ValueError("invalid audience")
    session_id = create_session_identifier()
    refresh, _, refresh_jti = create_v1_token(
        user_id=user.id, token_version=user.token_version, session_id=session_id,
        audience=audience, token_type="refresh",
    )
    session = AuthSessionORM(
        id=session_id, user_id=user.id, audience=audience,
        refresh_jti_hash=hash_token_identifier(refresh_jti),
        expires_at=_utcnow() + timedelta(days=_refresh_days(audience)),
        ip_hash=_hash_request_value(request.client.host if request.client else None),
        user_agent_hash=_hash_request_value(request.headers.get("user-agent")),
    )
    db.add(session)
    write_audit_log(actor_user_id=user.id, action="auth.login", target_type="auth_session", target_id=None,
                    knowledge_base_id=None, details={"audience": audience}, db=db, commit=False)
    db.commit()
    return _access_payload(user, audience, session_id), refresh


def _access_payload(user: UserORM, audience: str, session_id: str) -> dict[str, object]:
    access, seconds, _ = create_v1_token(
        user_id=user.id, token_version=user.token_version, session_id=session_id,
        audience=audience, token_type="access",
    )
    return {"access_token": access, "token_type": "bearer", "expires_in": seconds}


def set_refresh_cookie(response: Response, refresh: str, audience: str) -> str:
    csrf = create_session_identifier()
    response.set_cookie(_cookie_name(audience), refresh, httponly=True, secure=AUTH_COOKIE_SECURE,
                        samesite="lax", path=_cookie_path(audience), max_age=_refresh_days(audience) * 86400)
    response.set_cookie(f"{_cookie_name(audience)}_csrf", csrf, httponly=False, secure=AUTH_COOKIE_SECURE,
                        samesite="lax", path=_cookie_path(audience), max_age=_refresh_days(audience) * 86400)
    return csrf


def clear_refresh_cookie(response: Response, audience: str) -> None:
    response.delete_cookie(_cookie_name(audience), path=_cookie_path(audience))
    response.delete_cookie(f"{_cookie_name(audience)}_csrf", path=_cookie_path(audience))


def rotate_session(*, request: Request, audience: str, db: Session) -> tuple[dict[str, object], str]:
    cookie_name = _cookie_name(audience)
    refresh = request.cookies.get(cookie_name)
    csrf = request.headers.get("X-CSRF-Token")
    if not refresh or not csrf or csrf != request.cookies.get(f"{cookie_name}_csrf"):
        raise HTTPException(status_code=401, detail="csrf validation failed")
    try:
        payload = decode_v1_token(refresh, expected_audience=audience, expected_type="refresh")
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    now = _utcnow()
    session = db.get(AuthSessionORM, str(payload["sid"]))
    token_hash = hash_token_identifier(str(payload["jti"]))
    if session is None or session.audience != audience or session.expires_at < now or session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    if session.previous_refresh_jti_hash == token_hash:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="refresh token reuse detected")
    if session.refresh_jti_hash != token_hash:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    user = db.get(UserORM, int(str(payload["sub"])))
    if user is None or not user.is_active or user.token_version != payload["tv"]:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="invalid refresh token")
    replacement, _, replacement_jti = create_v1_token(user_id=user.id, token_version=user.token_version,
        session_id=session.id, audience=audience, token_type="refresh")
    changed = db.execute(update(AuthSessionORM).where(
        AuthSessionORM.id == session.id, AuthSessionORM.refresh_jti_hash == token_hash,
        AuthSessionORM.revoked_at.is_(None)
    ).values(previous_refresh_jti_hash=token_hash, refresh_jti_hash=hash_token_identifier(replacement_jti),
             replaced_at=now, last_used_at=now)).rowcount
    if changed != 1:
        db.rollback()
        # A concurrent request can have already rotated this exact token.
        # Treat it as refresh-token replay and invalidate the whole session.
        latest = db.get(AuthSessionORM, session.id)
        if latest is not None and latest.previous_refresh_jti_hash == token_hash:
            latest.revoked_at = _utcnow()
            db.commit()
            raise HTTPException(status_code=401, detail="refresh token reuse detected")
        raise HTTPException(status_code=401, detail="invalid refresh token")
    db.commit()
    return _access_payload(user, audience, session.id), replacement


def revoke_session(*, session_id: str, user_id: int, audience: str, db: Session) -> None:
    db.execute(update(AuthSessionORM).where(AuthSessionORM.id == session_id, AuthSessionORM.user_id == user_id,
        AuthSessionORM.audience == audience, AuthSessionORM.revoked_at.is_(None)).values(revoked_at=_utcnow()))
    db.commit()


def get_v1_current_user(*, token: str, audience: str, db: Session) -> tuple[UserORM, str]:
    try:
        payload = decode_v1_token(token, expected_audience=audience, expected_type="access")
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid access token", headers={"WWW-Authenticate": "Bearer"})
    session = db.get(AuthSessionORM, str(payload["sid"]))
    user = db.get(UserORM, int(str(payload["sub"])))
    if session is None or session.user_id != int(str(payload["sub"])) or session.audience != audience or session.revoked_at is not None or session.expires_at < _utcnow() or user is None or not user.is_active or user.token_version != payload["tv"]:
        raise HTTPException(status_code=401, detail="invalid access token", headers={"WWW-Authenticate": "Bearer"})
    return user, session.id

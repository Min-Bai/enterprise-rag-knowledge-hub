import logging

from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError

from .config import (
    AI_RATE_LIMIT,
    AI_RATE_WINDOW_SECONDS,
    DOCUMENT_UPLOAD_RATE_LIMIT,
    DOCUMENT_UPLOAD_RATE_WINDOW_SECONDS,
    LOGIN_RATE_LIMIT,
    LOGIN_IP_RATE_LIMIT,
    LOGIN_RATE_WINDOW_SECONDS,
)
from .redis_client import redis_client


logger = logging.getLogger("enterprise_rag.rate_limit")


class LoginRateLimiter:
    def __init__(
        self,
        client: Redis,
        limit: int,
        window_seconds: int,
        key_prefix: str = "rate_limit:login",
    ):
        self.client = client
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    def is_allowed(self, client_id: str) -> bool:
        key = f"{self.key_prefix}:{client_id}"
        count = self.client.incr(key)

        if count == 1:
            self.client.expire(key, self.window_seconds)

        return count <= self.limit

    def retry_after(self, client_id: str) -> int:
        key = f"{self.key_prefix}:{client_id}"
        ttl = self.client.ttl(key)
        return ttl if ttl > 0 else self.window_seconds


def enforce_login_rate_limit(request: Request) -> None:
    if redis_client is None:
        return

    client_id = request.client.host if request.client else "unknown"
    ip_limiter = LoginRateLimiter(
        client=redis_client,
        limit=LOGIN_IP_RATE_LIMIT,
        window_seconds=LOGIN_RATE_WINDOW_SECONDS,
    )
    try:
        ip_allowed = ip_limiter.is_allowed(client_id)
    except RedisError:
        logger.exception("login rate limit check failed")
        raise HTTPException(
            status_code=503,
            detail="rate limit service unavailable",
        )

    if not ip_allowed:
        raise HTTPException(
            status_code=429,
            detail="too many login attempts",
            headers={"Retry-After": str(ip_limiter.retry_after(client_id))},
        )


def enforce_account_login_rate_limit(username: str) -> None:
    if redis_client is None:
        return
    limiter = LoginRateLimiter(
        client=redis_client,
        limit=LOGIN_RATE_LIMIT,
        window_seconds=LOGIN_RATE_WINDOW_SECONDS,
        key_prefix="rate_limit:login-account",
    )
    account_id = username.strip().lower()
    try:
        allowed = limiter.is_allowed(account_id)
    except RedisError:
        logger.exception("login account rate limit check failed")
        raise HTTPException(status_code=503, detail="rate limit service unavailable")
    if not allowed:
        raise HTTPException(status_code=429, detail="too many login attempts", headers={"Retry-After": str(limiter.retry_after(account_id))})


def enforce_ai_rate_limit(user_id: int) -> None:
    if redis_client is None:
        return

    limiter = LoginRateLimiter(
        client=redis_client,
        limit=AI_RATE_LIMIT,
        window_seconds=AI_RATE_WINDOW_SECONDS,
        key_prefix="rate_limit:ai:rewrite",
    )

    try:
        allowed = limiter.is_allowed(str(user_id))
    except RedisError:
        logger.exception("AI rate limit check failed")
        raise HTTPException(
            status_code=503,
            detail="rate limit service unavailable",
        )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="AI request limit exceeded",
            headers={"Retry-After": str(limiter.retry_after(str(user_id)))},
        )

def enforce_document_upload_rate_limit(user_id: int) -> None:
    if redis_client is None:
        return

    limiter = LoginRateLimiter(
        client=redis_client,
        limit=DOCUMENT_UPLOAD_RATE_LIMIT,
        window_seconds=DOCUMENT_UPLOAD_RATE_WINDOW_SECONDS,
        key_prefix="rate_limit:document-upload",
    )

    try:
        allowed = limiter.is_allowed(str(user_id))
    except RedisError:
        logger.exception("document upload rate limit check failed")
        raise HTTPException(
            status_code=503,
            detail="rate limit service unavailable",
        )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="document upload rate limit exceeded",
            headers={"Retry-After": str(limiter.retry_after(str(user_id)))},
        )

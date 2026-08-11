from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from .redis_client import redis_client
from .services.vector_store import get_qdrant_client

import logging
from time import perf_counter
from uuid import uuid4
from .config import CORS_ORIGINS, LOG_LEVEL
from .database import get_db
from .routers.tasks import router as task_router
from .routers.users import router as user_router
from .routers.auth import router as auth_router
from .routers.ai import router as ai_router
from .routers.documents import router as document_router

app = FastAPI(title="Todo Project Structure API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("todo_api")

@app.get("/")
def read_root():
    return {
        "message": "Todo API is running",
        "docs": "/docs",
    }


def readiness_response(db: Session):
    try:
        db.execute(text("SELECT 1"))

        if redis_client is None:
            raise RuntimeError("Redis is not configured")

        redis_client.ping()
        get_qdrant_client().get_collections()
    except Exception:
        logger.exception("readiness check failed")
        raise HTTPException(
            status_code=503,
            detail="dependencies unavailable",
        )

    return {
        "status": "ok",
        "database": "ok",
        "redis": "ok",
        "qdrant": "ok",
    }


@app.get("/health/live")
def liveness_check():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)):
    return readiness_response(db)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    return readiness_response(db)

app.include_router(task_router)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(document_router)

@app.middleware("http")
async def log_request(request: Request, call_next):
    start_time = perf_counter()
    request_id = uuid4().hex
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (perf_counter() - start_time) * 1000
        logger.exception(
            "request_id=%s %s %s failed after %.1fms",
            request_id,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "internal server error"},
            headers={"X-Request-ID": request_id},
        )
    elapsed_ms = (perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request_id=%s %s %s -> %s in %.1fms",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )

    return response

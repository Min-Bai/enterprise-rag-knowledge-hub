from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
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
from .error_codes import get_error_code
from .routers.users import router as user_router
from .routers.auth import router as auth_router
from .routers.ai import router as ai_router
from .routers.documents import router as document_router
from .routers.knowledge_bases import router as knowledge_base_router
from .request_context import get_request_id, reset_request_id, set_request_id
from .api.client.router import router as client_v1_router
from .api.admin.router import router as admin_v1_router
from .api.common.response import ApiResponse

app = FastAPI(title="Enterprise RAG Knowledge Hub API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-CSRF-Token", "X-Request-ID"],
)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("enterprise_rag")


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": get_error_code(exc.detail, exc.status_code),
        },
        headers=exc.headers,
    )

@app.get("/")
def read_root():
    return {
        "message": "Enterprise RAG Knowledge Hub API is running",
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

app.include_router(user_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(document_router)
app.include_router(knowledge_base_router)


def create_versioned_api(title: str, router) -> FastAPI:
    versioned = FastAPI(title=title, version="1.0.0", docs_url="/docs", openapi_url="/openapi.json")
    # Mounted FastAPI applications otherwise keep a separate override map,
    # making the production dependency graph and the test graph diverge.
    versioned.router.dependency_overrides_provider = app

    @versioned.exception_handler(HTTPException)
    async def v1_http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={
            "code": get_error_code(exc.detail, exc.status_code),
            "message": str(exc.detail), "data": None,
            "request_id": get_request_id(),
        }, headers=exc.headers)

    @versioned.exception_handler(RequestValidationError)
    async def v1_validation_exception_handler(request: Request, exc: RequestValidationError):
        # Log locations and error types only; validation input may contain passwords.
        logging.getLogger("enterprise_rag.validation").warning(
            "v1 request validation failed: %s",
            [{"loc": error.get("loc"), "type": error.get("type")} for error in exc.errors()],
        )
        return JSONResponse(status_code=422, content={
            "code": "VALIDATION_ERROR", "message": "request validation failed", "data": None,
            "request_id": get_request_id(),
        })

    versioned.include_router(router)
    return versioned


client_v1_app = create_versioned_api("Enterprise RAG Client API", client_v1_router)
admin_v1_app = create_versioned_api("Enterprise RAG Admin API", admin_v1_router)
app.mount("/api/v1/client", client_v1_app)
app.mount("/api/v1/admin", admin_v1_app)


@app.get("/openapi/client.json", include_in_schema=False)
def client_openapi():
    return client_v1_app.openapi()


@app.get("/openapi/admin.json", include_in_schema=False)
def admin_openapi():
    return admin_v1_app.openapi()

@app.middleware("http")
async def log_request(request: Request, call_next):
    start_time = perf_counter()
    request_id = uuid4().hex
    request_id_token = set_request_id(request_id)
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
        content = (
            {"code": "INTERNAL_SERVER_ERROR", "message": "internal server error", "data": None, "request_id": request_id}
            if request.url.path.startswith("/api/v1/")
            else {"detail": "internal server error", "code": "INTERNAL_SERVER_ERROR"}
        )
        return JSONResponse(status_code=500, content=content, headers={"X-Request-ID": request_id})
    finally:
        reset_request_id(request_id_token)
    elapsed_ms = (perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")

    logger.info(
        "request_id=%s %s %s -> %s in %.1fms",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )

    return response

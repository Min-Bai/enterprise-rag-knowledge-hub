from fastapi import Depends, FastAPI, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

import logging
from time import perf_counter
from .config import CORS_ORIGINS, LOG_LEVEL
from .database import get_db
from .routers.tasks import router as task_router
from .routers.users import router as user_router
from .routers.auth import router as auth_router
from .routers.ai import router as ai_router

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

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "ok",
    }

app.include_router(task_router)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(ai_router)

@app.middleware("http")
async def log_request(request: Request, call_next):
    start_time = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (perf_counter() - start_time) * 1000
        logger.exception(
        "%s %s failed after %.1fms",
        request.method,
        request.url.path,
        elapsed_ms,
        )
        raise
    elapsed_ms = (perf_counter() - start_time) * 1000

    logger.info(
        "%s %s -> %s in %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )

    return response

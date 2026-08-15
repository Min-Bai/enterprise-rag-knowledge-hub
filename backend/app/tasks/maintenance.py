from datetime import UTC, datetime

from ..celery_app import celery_app
from ..database import SessionLocal
from ..models.auth_session import AuthSessionORM


@celery_app.task(name="enterprise_rag.maintenance.cleanup_auth_sessions", queue="maintenance")
def cleanup_auth_sessions() -> int:
    """Remove expired and revoked sessions; it is safe to run repeatedly."""
    db = SessionLocal()
    try:
        deleted = db.query(AuthSessionORM).filter(
            (AuthSessionORM.expires_at < datetime.now(UTC).replace(tzinfo=None)) | AuthSessionORM.revoked_at.is_not(None)
        ).delete(synchronize_session=False)
        db.commit()
        return deleted
    finally:
        db.close()

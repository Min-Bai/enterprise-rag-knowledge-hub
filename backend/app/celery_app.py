from celery import Celery
from celery.signals import worker_ready

from .config import REDIS_URL


# Kept for the existing requeue/check scripts during the publish transition.
DOCUMENT_QUEUE_NAME = "document-processing"
DOCUMENT_DEFAULT_QUEUE = "document.default"

if not REDIS_URL:
    raise RuntimeError("REDIS_URL is required for Celery document processing")


celery_app = Celery(
    "enterprise_rag",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.app.tasks.document_processing", "backend.app.tasks.maintenance"],
)
celery_app.conf.update(
    task_default_queue=DOCUMENT_QUEUE_NAME,
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=20 * 60,
    task_soft_time_limit=18 * 60,
    worker_prefetch_multiplier=1,
    task_routes={
        "enterprise_rag.document_processing": {"queue": "document.default"},
        "enterprise_rag.document_retry": {"queue": "document.high"},
        "enterprise_rag.maintenance.*": {"queue": "maintenance"},
        "enterprise_rag.evaluation.*": {"queue": "evaluation"},
    },
    beat_schedule={
        "cleanup-expired-auth-sessions": {
            "task": "enterprise_rag.maintenance.cleanup_auth_sessions",
            "schedule": 3600.0,
        },
    },
)


@worker_ready.connect
def recover_interrupted_documents(**_kwargs) -> None:
    from .services.document_processor import mark_interrupted_documents_failed

    recovered = mark_interrupted_documents_failed()
    if recovered:
        print(f"Marked {recovered} interrupted document(s) as failed")

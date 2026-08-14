from celery import Celery
from celery.signals import worker_ready

from .config import REDIS_URL


DOCUMENT_QUEUE_NAME = "document-processing"

if not REDIS_URL:
    raise RuntimeError("REDIS_URL is required for Celery document processing")


celery_app = Celery(
    "enterprise_rag",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.app.tasks.document_processing"],
)
celery_app.conf.update(
    task_default_queue=DOCUMENT_QUEUE_NAME,
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=20 * 60,
    task_soft_time_limit=18 * 60,
    worker_prefetch_multiplier=1,
)


@worker_ready.connect
def recover_interrupted_documents(**_kwargs) -> None:
    from .services.document_processor import mark_interrupted_documents_failed

    recovered = mark_interrupted_documents_failed()
    if recovered:
        print(f"Marked {recovered} interrupted document(s) as failed")

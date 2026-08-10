from rq import Queue

from ..redis_client import redis_client
from .document_processor import process_document


DOCUMENT_QUEUE_NAME = "document-processing"


def get_document_queue() -> Queue:
    if redis_client is None:
        raise RuntimeError("REDIS_URL is required for document processing")

    return Queue(DOCUMENT_QUEUE_NAME, connection=redis_client)


def enqueue_document_processing(document_id: int) -> None:
    get_document_queue().enqueue(
        process_document,
        document_id,
        job_timeout="20m",
        result_ttl=0,
        failure_ttl=7 * 24 * 60 * 60,
    )
from functools import lru_cache

from redis import Redis
from rq import Queue

from ..config import REDIS_URL
from .document_processor import process_document


DOCUMENT_QUEUE_NAME = "document-processing"


@lru_cache
def get_document_redis() -> Redis:
    if not REDIS_URL:
        raise RuntimeError("REDIS_URL is required for document processing")

    return Redis.from_url(REDIS_URL, decode_responses=False)


def get_document_queue() -> Queue:
    return Queue(
        DOCUMENT_QUEUE_NAME,
        connection=get_document_redis(),
    )


def enqueue_document_processing(document_id: int) -> None:
    get_document_queue().enqueue(
        process_document,
        document_id,
        job_timeout="20m",
        result_ttl=0,
        failure_ttl=7 * 24 * 60 * 60,
    )
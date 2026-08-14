from ..celery_app import DOCUMENT_QUEUE_NAME
from ..tasks.document_processing import process_document_task


def enqueue_document_processing(document_id: int) -> None:
    process_document_task.apply_async(
        args=[document_id],
        queue=DOCUMENT_QUEUE_NAME,
    )

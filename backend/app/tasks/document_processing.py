from ..celery_app import DOCUMENT_QUEUE_NAME, celery_app
from ..services.document_processor import process_document


@celery_app.task(
    name="enterprise_rag.document_processing",
    queue=DOCUMENT_QUEUE_NAME,
)
def process_document_task(document_id: int) -> None:
    process_document(document_id)

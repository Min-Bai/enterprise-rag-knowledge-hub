from ..celery_app import DOCUMENT_DEFAULT_QUEUE, celery_app
from ..services.document_processor import process_document


@celery_app.task(
    name="enterprise_rag.document_processing",
    queue=DOCUMENT_DEFAULT_QUEUE,
)
def process_document_task(document_id: int) -> None:
    process_document(document_id)

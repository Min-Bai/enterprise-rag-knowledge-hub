from datetime import UTC, datetime
from pathlib import Path

from ..database import SessionLocal
from ..models.document import DocumentORM
from .document_parser import split_document_into_chunks, split_pdf_into_chunks
from .document_vectors import index_document_chunks
from sqlalchemy import update


INTERRUPTED_PROCESSING_MESSAGE = "processing interrupted; retry document"


def mark_interrupted_documents_failed() -> int:
    db = SessionLocal()

    try:
        result = db.execute(
            update(DocumentORM)
            .where(DocumentORM.status == "processing")
            .values(
                status="failed",
                error_message=INTERRUPTED_PROCESSING_MESSAGE,
            )
        )
        db.commit()
        return int(result.rowcount or 0)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def process_document(document_id: int) -> None:
    db = SessionLocal()

    try:
        document = db.get(DocumentORM, document_id)
        if document is None:
            return

        document.status = "processing"
        document.error_message = None
        document.chunk_count = 0
        document.processed_at = None
        db.commit()

        chunks = (
            split_pdf_into_chunks(document.storage_path)
            if Path(document.storage_path).suffix.lower() == ".pdf"
            else split_document_into_chunks(document.storage_path)
        )

        index_document_chunks(
            document_id=document.id,
            user_id=document.user_id,
            knowledge_base_id=document.knowledge_base_id,
            tags=document.tags,
            chunks=chunks,
        )

        document.status = "ready"
        document.chunk_count = len(chunks)
        document.processed_at = datetime.now(UTC)
        db.commit()

    except Exception as error:
        db.rollback()

        document = db.get(DocumentORM, document_id)
        if document is not None:
            document.status = "failed"
            document.error_message = str(error)[:50]
            document.chunk_count = 0
            document.processed_at = None
            db.commit()

    finally:
        db.close()

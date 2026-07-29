from ..database import SessionLocal
from ..models.document import DocumentORM
from .document_parser import extract_pdf_text, split_text_into_chunks
from .document_vectors import index_document_chunks


def process_document(document_id: int) -> None:
    db = SessionLocal()

    try:
        document = db.get(DocumentORM, document_id)
        if document is None:
            return

        document.status = "processing"
        document.error_message = None
        db.commit()

        text = extract_pdf_text(document.storage_path)
        chunks = split_text_into_chunks(text)

        index_document_chunks(
            document_id=document.id,
            user_id=document.user_id,
            chunks=chunks,
        )

        document.status = "ready"
        db.commit()

    except Exception as error:
        db.rollback()

        document = db.get(DocumentORM, document_id)
        if document is not None:
            document.status = "failed"
            document.error_message = str(error)[:50]
            db.commit()

    finally:
        db.close()
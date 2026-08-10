from pathlib import Path

from ..exceptions import (
    DocumentNotFoundError,
    DocumentRetryNotAllowedError,
)
from .document_vectors import delete_document_vectors

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.document import DocumentORM


def create_document_service(
    db: Session,
    user_id: int,
    filename: str,
    storage_path: str,
) -> DocumentORM:
    document = DocumentORM(
        user_id=user_id,
        filename=filename,
        storage_path=storage_path,
    )

    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_documents_service(db: Session, user_id: int) -> list[DocumentORM]:
    statement = (
        select(DocumentORM)
        .where(DocumentORM.user_id == user_id)
        .order_by(DocumentORM.created_at.desc())
    )
    return list(db.scalars(statement).all())

def get_ready_documents_service(
    db: Session,
    user_id: int,
) -> list[DocumentORM]:
    statement = (
        select(DocumentORM)
        .where(
            DocumentORM.user_id == user_id,
            DocumentORM.status == "ready",
        )
        .order_by(DocumentORM.created_at.desc())
    )
    return list(db.scalars(statement).all())

def retry_document_service(
    document_id: int,
    user_id: int,
    db: Session,
) -> DocumentORM:
    statement = select(DocumentORM).where(
        DocumentORM.id == document_id,
        DocumentORM.user_id == user_id,
    )
    document = db.scalar(statement)

    if document is None:
        raise DocumentNotFoundError

    if document.status != "failed":
        raise DocumentRetryNotAllowedError

    delete_document_vectors(
        document_id=document.id,
        user_id=user_id,
    )

    document.status = "uploaded"
    document.error_message = None
    db.commit()
    db.refresh(document)
    return document

def delete_document_service(
    document_id: int,
    user_id: int,
    db: Session,
) -> None:
    statement = select(DocumentORM).where(
        DocumentORM.id == document_id,
        DocumentORM.user_id == user_id,
    )
    document = db.scalar(statement)

    if document is None:
        raise DocumentNotFoundError

    delete_document_vectors(
        document_id=document.id,
        user_id=user_id,
    )

    Path(document.storage_path).unlink(missing_ok=True)

    db.delete(document)
    db.commit()
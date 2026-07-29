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

from pathlib import Path

from ..exceptions import (
    DocumentNotFoundError,
    DocumentReindexNotAllowedError,
    DuplicateDocumentError,
    DocumentRetryNotAllowedError,
)
from .document_vectors import delete_document_vectors

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.document import DocumentORM
from .knowledge_bases import (
    KnowledgeBaseNotFoundError,
    get_default_knowledge_base_service,
    get_knowledge_base_service,
)
from .knowledge_base_members import require_knowledge_base_role
from .document_tags import normalize_document_tags


def create_document_service(
    db: Session,
    user_id: int,
    filename: str,
    storage_path: str,
    content_sha256: str | None = None,
    knowledge_base_id: int | None = None,
    tags: list[str] | None = None,
) -> DocumentORM:
    if knowledge_base_id is None:
        knowledge_base = get_default_knowledge_base_service(db, user_id)
    else:
        knowledge_base = get_knowledge_base_service(
            db,
            knowledge_base_id,
            user_id,
        )
    require_knowledge_base_role(
        knowledge_base=knowledge_base,
        user_id=user_id,
        db=db,
        allowed_roles={"owner", "editor"},
    )
    if content_sha256 is not None and db.scalar(select(DocumentORM.id).where(
        DocumentORM.knowledge_base_id == knowledge_base.id,
        DocumentORM.content_sha256 == content_sha256,
    )) is not None:
        raise DuplicateDocumentError

    document = DocumentORM(
        user_id=user_id,
        knowledge_base_id=knowledge_base.id,
        filename=filename,
        storage_path=storage_path,
        content_sha256=content_sha256,
        tags=normalize_document_tags(tags),
    )

    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_documents_service(
    db: Session,
    user_id: int,
    knowledge_base_id: int | None = None,
) -> list[DocumentORM]:
    if knowledge_base_id is not None:
        knowledge_base = get_knowledge_base_service(db, knowledge_base_id, user_id)
        require_knowledge_base_role(knowledge_base=knowledge_base, user_id=user_id, db=db, allowed_roles={"owner", "editor", "viewer"})
        statement = select(DocumentORM).where(DocumentORM.knowledge_base_id == knowledge_base_id)
    else:
        statement = select(DocumentORM).where(DocumentORM.user_id == user_id)
    statement = statement.order_by(DocumentORM.created_at.desc())
    return list(db.scalars(statement).all())


def get_document_service(
    document_id: int,
    user_id: int,
    db: Session,
) -> DocumentORM:
    document = db.scalar(select(DocumentORM).where(DocumentORM.id == document_id))
    if document is None:
        raise DocumentNotFoundError
    try:
        knowledge_base = get_knowledge_base_service(db, document.knowledge_base_id, user_id)
    except KnowledgeBaseNotFoundError as error:
        raise DocumentNotFoundError from error
    require_knowledge_base_role(knowledge_base=knowledge_base, user_id=user_id, db=db, allowed_roles={"owner", "editor", "viewer"})
    return document

def get_ready_documents_service(
    db: Session,
    user_id: int,
    knowledge_base_id: int | None = None,
) -> list[DocumentORM]:
    if knowledge_base_id is not None:
        knowledge_base = get_knowledge_base_service(db, knowledge_base_id, user_id)
        require_knowledge_base_role(knowledge_base=knowledge_base, user_id=user_id, db=db, allowed_roles={"owner", "editor", "viewer"})
        statement = select(DocumentORM).where(DocumentORM.knowledge_base_id == knowledge_base_id)
    else:
        statement = select(DocumentORM).where(DocumentORM.user_id == user_id)
    statement = statement.where(DocumentORM.status == "ready").order_by(DocumentORM.created_at.desc())
    return list(db.scalars(statement).all())

def retry_document_service(
    document_id: int,
    user_id: int,
    db: Session,
) -> DocumentORM:
    document = get_document_service(document_id=document_id, user_id=user_id, db=db)
    knowledge_base = get_knowledge_base_service(db, document.knowledge_base_id, user_id)
    require_knowledge_base_role(knowledge_base=knowledge_base, user_id=user_id, db=db, allowed_roles={"owner", "editor"})

    if document.status != "failed":
        raise DocumentRetryNotAllowedError

    delete_document_vectors(
        document_id=document.id,
        user_id=document.user_id,
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
) -> DocumentORM:
    document = get_document_service(document_id=document_id, user_id=user_id, db=db)
    knowledge_base = get_knowledge_base_service(db, document.knowledge_base_id, user_id)
    require_knowledge_base_role(knowledge_base=knowledge_base, user_id=user_id, db=db, allowed_roles={"owner", "editor"})

    delete_document_vectors(
        document_id=document.id,
        user_id=document.user_id,
    )

    Path(document.storage_path).unlink(missing_ok=True)

    db.delete(document)
    db.commit()
    return document


def reindex_document_service(
    document_id: int,
    user_id: int,
    db: Session,
) -> DocumentORM:
    document = get_document_service(document_id=document_id, user_id=user_id, db=db)
    knowledge_base = get_knowledge_base_service(db, document.knowledge_base_id, user_id)
    require_knowledge_base_role(knowledge_base=knowledge_base, user_id=user_id, db=db, allowed_roles={"owner", "editor"})
    if document.status != "ready":
        raise DocumentReindexNotAllowedError
    delete_document_vectors(document_id=document.id, user_id=document.user_id)
    document.status = "uploaded"
    document.error_message = None
    db.commit()
    db.refresh(document)
    return document

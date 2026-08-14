from sqlalchemy import and_, distinct, or_, select
from sqlalchemy.orm import Session

from ..models.knowledge_base import KnowledgeBaseORM
from ..models.document import DocumentORM
from ..models.knowledge_base_member import KnowledgeBaseMemberORM
from ..schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


class KnowledgeBaseNotFoundError(Exception):
    pass


class KnowledgeBaseNotEmptyError(Exception):
    pass


DEFAULT_KNOWLEDGE_BASE_NAME = "Default knowledge base"


def get_default_knowledge_base_service(
    db: Session,
    owner_user_id: int,
) -> KnowledgeBaseORM:
    statement = select(KnowledgeBaseORM).where(
        KnowledgeBaseORM.owner_user_id == owner_user_id,
        KnowledgeBaseORM.name == DEFAULT_KNOWLEDGE_BASE_NAME,
    )
    knowledge_base = db.scalar(statement)
    if knowledge_base is not None:
        return knowledge_base

    knowledge_base = KnowledgeBaseORM(
        owner_user_id=owner_user_id,
        name=DEFAULT_KNOWLEDGE_BASE_NAME,
    )
    db.add(knowledge_base)
    db.flush()
    return knowledge_base


def create_knowledge_base_service(
    db: Session,
    owner_user_id: int,
    payload: KnowledgeBaseCreate,
) -> KnowledgeBaseORM:
    knowledge_base = KnowledgeBaseORM(
        owner_user_id=owner_user_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base


def get_knowledge_bases_service(
    db: Session,
    owner_user_id: int,
) -> list[dict[str, object]]:
    statement = (
        select(KnowledgeBaseORM, KnowledgeBaseMemberORM.role).distinct()
        .outerjoin(
            KnowledgeBaseMemberORM,
            and_(
                KnowledgeBaseMemberORM.knowledge_base_id == KnowledgeBaseORM.id,
                KnowledgeBaseMemberORM.user_id == owner_user_id,
            ),
        )
        .where(or_(KnowledgeBaseORM.owner_user_id == owner_user_id, KnowledgeBaseMemberORM.user_id == owner_user_id))
        .order_by(KnowledgeBaseORM.created_at.desc())
    )
    return [
        {
            "id": knowledge_base.id,
            "name": knowledge_base.name,
            "description": knowledge_base.description,
            "created_at": knowledge_base.created_at,
            "role": "owner" if knowledge_base.owner_user_id == owner_user_id else role,
        }
        for knowledge_base, role in db.execute(statement).all()
    ]


def get_knowledge_base_service(
    db: Session,
    knowledge_base_id: int,
    owner_user_id: int,
) -> KnowledgeBaseORM:
    statement = select(KnowledgeBaseORM).where(
        KnowledgeBaseORM.id == knowledge_base_id,
        or_(
            KnowledgeBaseORM.owner_user_id == owner_user_id,
            KnowledgeBaseORM.members.any(KnowledgeBaseMemberORM.user_id == owner_user_id),
        ),
    )
    knowledge_base = db.scalar(statement)
    if knowledge_base is None:
        raise KnowledgeBaseNotFoundError
    return knowledge_base


def update_knowledge_base_service(
    db: Session,
    knowledge_base_id: int,
    owner_user_id: int,
    payload: KnowledgeBaseUpdate,
) -> KnowledgeBaseORM:
    knowledge_base = get_knowledge_base_service(
        db,
        knowledge_base_id,
        owner_user_id,
    )
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(knowledge_base, field_name, value)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base


def delete_knowledge_base_service(
    db: Session,
    knowledge_base_id: int,
    owner_user_id: int,
) -> None:
    knowledge_base = get_knowledge_base_service(
        db,
        knowledge_base_id,
        owner_user_id,
    )
    document_exists = db.scalar(
        select(DocumentORM.id)
        .where(DocumentORM.knowledge_base_id == knowledge_base.id)
        .limit(1)
    )
    if document_exists is not None:
        raise KnowledgeBaseNotEmptyError
    db.delete(knowledge_base)
    db.commit()

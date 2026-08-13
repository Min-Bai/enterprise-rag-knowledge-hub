from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.knowledge_base import KnowledgeBaseORM
from ..models.knowledge_base_member import KnowledgeBaseMemberORM
from ..models.user import UserORM


class KnowledgeBaseAccessDeniedError(Exception):
    pass


class KnowledgeBaseMemberNotFoundError(Exception):
    pass


def get_knowledge_base_role(*, knowledge_base: KnowledgeBaseORM, user_id: int, db: Session) -> str | None:
    if knowledge_base.owner_user_id == user_id:
        return "owner"
    return db.scalar(select(KnowledgeBaseMemberORM.role).where(
        KnowledgeBaseMemberORM.knowledge_base_id == knowledge_base.id,
        KnowledgeBaseMemberORM.user_id == user_id,
    ))


def require_knowledge_base_role(*, knowledge_base: KnowledgeBaseORM, user_id: int, db: Session, allowed_roles: set[str]) -> str:
    role = get_knowledge_base_role(knowledge_base=knowledge_base, user_id=user_id, db=db)
    if role not in allowed_roles:
        raise KnowledgeBaseAccessDeniedError
    return role


def list_knowledge_base_members(*, knowledge_base: KnowledgeBaseORM, db: Session) -> list[dict[str, object]]:
    members = db.execute(
        select(KnowledgeBaseMemberORM, UserORM.username)
        .join(UserORM, UserORM.id == KnowledgeBaseMemberORM.user_id)
        .where(KnowledgeBaseMemberORM.knowledge_base_id == knowledge_base.id)
        .order_by(UserORM.username)
    ).all()
    return [{"user_id": knowledge_base.owner_user_id, "username": knowledge_base.owner.username, "role": "owner"}] + [
        {"user_id": member.user_id, "username": username, "role": member.role}
        for member, username in members
    ]


def add_knowledge_base_member(*, knowledge_base: KnowledgeBaseORM, username: str, role: str, db: Session) -> KnowledgeBaseMemberORM:
    user = db.scalar(select(UserORM).where(UserORM.username == username))
    if user is None:
        raise KnowledgeBaseMemberNotFoundError
    if user.id == knowledge_base.owner_user_id:
        raise KnowledgeBaseAccessDeniedError
    membership = db.scalar(select(KnowledgeBaseMemberORM).where(
        KnowledgeBaseMemberORM.knowledge_base_id == knowledge_base.id,
        KnowledgeBaseMemberORM.user_id == user.id,
    ))
    if membership is None:
        membership = KnowledgeBaseMemberORM(knowledge_base_id=knowledge_base.id, user_id=user.id, role=role)
        db.add(membership)
    else:
        membership.role = role
    db.commit()
    db.refresh(membership)
    return membership


def remove_knowledge_base_member(*, knowledge_base: KnowledgeBaseORM, member_user_id: int, db: Session) -> None:
    membership = db.scalar(select(KnowledgeBaseMemberORM).where(
        KnowledgeBaseMemberORM.knowledge_base_id == knowledge_base.id,
        KnowledgeBaseMemberORM.user_id == member_user_id,
    ))
    if membership is None:
        raise KnowledgeBaseMemberNotFoundError
    db.delete(membership)
    db.commit()

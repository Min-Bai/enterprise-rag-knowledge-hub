from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.audit_log import AuditLogORM
from ..models.user import UserORM


def write_audit_log(
    *, actor_user_id: int, action: str, target_type: str, target_id: int | None,
    knowledge_base_id: int | None, details: dict[str, object] | None, db: Session,
    commit: bool = True,
) -> None:
    db.add(AuditLogORM(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        knowledge_base_id=knowledge_base_id,
        details=details,
    ))
    if commit:
        db.commit()


def get_knowledge_base_audit_logs(
    *, knowledge_base_id: int, db: Session, limit: int = 100, offset: int = 0
) -> list[dict[str, object]]:
    rows = db.execute(
        select(AuditLogORM, UserORM.username)
        .join(UserORM, UserORM.id == AuditLogORM.actor_user_id)
        .where(AuditLogORM.knowledge_base_id == knowledge_base_id)
        .order_by(AuditLogORM.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        {
            "id": event.id,
            "actor_user_id": event.actor_user_id,
            "actor_username": username,
            "action": event.action,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "details": event.details,
            "created_at": event.created_at,
        }
        for event, username in rows
    ]

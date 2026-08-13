from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.audit_log import AuditLogORM


def write_audit_log(
    *, actor_user_id: int, action: str, target_type: str, target_id: int | None,
    knowledge_base_id: int | None, details: dict[str, object] | None, db: Session,
) -> None:
    db.add(AuditLogORM(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        knowledge_base_id=knowledge_base_id,
        details=details,
    ))
    db.commit()


def get_knowledge_base_audit_logs(*, knowledge_base_id: int, db: Session, limit: int = 100) -> list[AuditLogORM]:
    return list(db.scalars(
        select(AuditLogORM)
        .where(AuditLogORM.knowledge_base_id == knowledge_base_id)
        .order_by(AuditLogORM.id.desc())
        .limit(limit)
    ).all())

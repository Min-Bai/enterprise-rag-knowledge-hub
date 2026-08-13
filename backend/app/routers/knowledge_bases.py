from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models.user import UserORM
from ..schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    KnowledgeBaseMemberCreate,
    KnowledgeBaseMemberResponse,
    AuditLogResponse,
    FeedbackSummaryResponse,
)
from ..services.knowledge_bases import (
    KnowledgeBaseNotFoundError,
    KnowledgeBaseNotEmptyError,
    create_knowledge_base_service,
    delete_knowledge_base_service,
    get_knowledge_bases_service,
    get_knowledge_base_service,
    update_knowledge_base_service,
)
from ..services.audit_logs import get_knowledge_base_audit_logs, write_audit_log
from ..services.feedback_analytics import get_knowledge_base_feedback_summary
from ..services.knowledge_base_members import (
    KnowledgeBaseAccessDeniedError,
    KnowledgeBaseMemberNotFoundError,
    add_knowledge_base_member,
    list_knowledge_base_members,
    remove_knowledge_base_member,
    require_knowledge_base_role,
)


router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.get("", response_model=list[KnowledgeBaseResponse])
def get_knowledge_bases(
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_knowledge_bases_service(db, current_user.id)


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    knowledge_base = create_knowledge_base_service(db, current_user.id, payload)
    write_audit_log(actor_user_id=current_user.id, action="knowledge_base.created", target_type="knowledge_base", target_id=knowledge_base.id, knowledge_base_id=knowledge_base.id, details={"name": knowledge_base.name}, db=db)
    return knowledge_base


@router.patch("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
def update_knowledge_base(
    knowledge_base_id: int,
    payload: KnowledgeBaseUpdate,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        knowledge_base = get_knowledge_base_service(db, knowledge_base_id, current_user.id)
        require_knowledge_base_role(knowledge_base=knowledge_base, user_id=current_user.id, db=db, allowed_roles={"owner"})
        updated = update_knowledge_base_service(
            db,
            knowledge_base_id,
            current_user.id,
            payload,
        )
        write_audit_log(actor_user_id=current_user.id, action="knowledge_base.updated", target_type="knowledge_base", target_id=updated.id, knowledge_base_id=updated.id, details=payload.model_dump(exclude_unset=True), db=db)
        return updated
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base owner access required")


@router.delete("/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_base(
    knowledge_base_id: int,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        knowledge_base = get_knowledge_base_service(db, knowledge_base_id, current_user.id)
        require_knowledge_base_role(knowledge_base=knowledge_base, user_id=current_user.id, db=db, allowed_roles={"owner"})
        delete_knowledge_base_service(db, knowledge_base_id, current_user.id)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseNotEmptyError:
        raise HTTPException(
            status_code=409,
            detail="delete all documents before deleting this knowledge base",
        )
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base owner access required")


@router.get("/{knowledge_base_id}/members", response_model=list[KnowledgeBaseMemberResponse])
def get_knowledge_base_members(knowledge_base_id: int, current_user: UserORM = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        knowledge_base = get_knowledge_base_service(db, knowledge_base_id, current_user.id)
        require_knowledge_base_role(knowledge_base=knowledge_base, user_id=current_user.id, db=db, allowed_roles={"owner"})
        return list_knowledge_base_members(knowledge_base=knowledge_base, db=db)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base owner access required")


@router.put("/{knowledge_base_id}/members", response_model=KnowledgeBaseMemberResponse)
def add_member(knowledge_base_id: int, payload: KnowledgeBaseMemberCreate, current_user: UserORM = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        knowledge_base = get_knowledge_base_service(db, knowledge_base_id, current_user.id)
        require_knowledge_base_role(knowledge_base=knowledge_base, user_id=current_user.id, db=db, allowed_roles={"owner"})
        membership = add_knowledge_base_member(knowledge_base=knowledge_base, username=payload.username, role=payload.role, db=db)
        write_audit_log(actor_user_id=current_user.id, action="knowledge_base.member_upserted", target_type="user", target_id=membership.user_id, knowledge_base_id=knowledge_base.id, details={"role": membership.role}, db=db)
        return {"user_id": membership.user_id, "username": payload.username, "role": membership.role}
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseMemberNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base owner access required")


@router.delete("/{knowledge_base_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(knowledge_base_id: int, user_id: int, current_user: UserORM = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        knowledge_base = get_knowledge_base_service(db, knowledge_base_id, current_user.id)
        require_knowledge_base_role(knowledge_base=knowledge_base, user_id=current_user.id, db=db, allowed_roles={"owner"})
        remove_knowledge_base_member(knowledge_base=knowledge_base, member_user_id=user_id, db=db)
        write_audit_log(actor_user_id=current_user.id, action="knowledge_base.member_removed", target_type="user", target_id=user_id, knowledge_base_id=knowledge_base.id, details=None, db=db)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseMemberNotFoundError:
        raise HTTPException(status_code=404, detail="member not found")
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base owner access required")


@router.get("/{knowledge_base_id}/audit-logs", response_model=list[AuditLogResponse])
def get_audit_logs(knowledge_base_id: int, current_user: UserORM = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        knowledge_base = get_knowledge_base_service(db, knowledge_base_id, current_user.id)
        require_knowledge_base_role(knowledge_base=knowledge_base, user_id=current_user.id, db=db, allowed_roles={"owner"})
        return get_knowledge_base_audit_logs(knowledge_base_id=knowledge_base.id, db=db)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base owner access required")


@router.get("/{knowledge_base_id}/feedback-summary", response_model=FeedbackSummaryResponse)
def get_feedback_summary(knowledge_base_id: int, current_user: UserORM = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        knowledge_base = get_knowledge_base_service(db, knowledge_base_id, current_user.id)
        require_knowledge_base_role(knowledge_base=knowledge_base, user_id=current_user.id, db=db, allowed_roles={"owner"})
        return get_knowledge_base_feedback_summary(knowledge_base_id=knowledge_base.id, db=db)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base owner access required")

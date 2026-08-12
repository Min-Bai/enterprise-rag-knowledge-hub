from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models.user import UserORM
from ..schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from ..services.knowledge_bases import (
    KnowledgeBaseNotFoundError,
    KnowledgeBaseNotEmptyError,
    create_knowledge_base_service,
    delete_knowledge_base_service,
    get_knowledge_bases_service,
    update_knowledge_base_service,
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
    return create_knowledge_base_service(db, current_user.id, payload)


@router.patch("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
def update_knowledge_base(
    knowledge_base_id: int,
    payload: KnowledgeBaseUpdate,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return update_knowledge_base_service(
            db,
            knowledge_base_id,
            current_user.id,
            payload,
        )
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")


@router.delete("/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_base(
    knowledge_base_id: int,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        delete_knowledge_base_service(db, knowledge_base_id, current_user.id)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseNotEmptyError:
        raise HTTPException(
            status_code=409,
            detail="delete all documents before deleting this knowledge base",
        )

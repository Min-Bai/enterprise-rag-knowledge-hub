from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models.user import UserORM
from ..rate_limit import enforce_ai_rate_limit
from ..schemas.ai import (
    ConversationResponse,
    DocumentAnswerRequest,
    DocumentAnswerResponse,
)
from ..services.ai import (
    AiNotConfiguredError,
    AiProviderError,
    DocumentNotReadyError,
    answer_document_service,
)
from ..services.conversations import (
    ConversationNotFoundError,
    get_document_conversations_service,
)
from ..services.documents import get_document_service
from ..exceptions import DocumentNotFoundError

router = APIRouter(prefix='/ai', tags=['ai'])


@router.post('/document-answer', response_model=DocumentAnswerResponse)
def answer_document(
    request: DocumentAnswerRequest,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    enforce_ai_rate_limit(current_user.id)
    try:
        return answer_document_service(request=request, current_user=current_user, db=db)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail='document not found')
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail='conversation not found')
    except DocumentNotReadyError:
        raise HTTPException(status_code=409, detail='document is not ready')
    except AiNotConfiguredError:
        raise HTTPException(status_code=503, detail='AI service is not configured')
    except AiProviderError:
        raise HTTPException(status_code=502, detail='AI provider request failed')


@router.get('/documents/{document_id}/conversations', response_model=list[ConversationResponse])
def get_document_conversations(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    try:
        get_document_service(
            document_id=document_id,
            user_id=current_user.id,
            db=db,
        )
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail='document not found')

    return get_document_conversations_service(
        user_id=current_user.id,
        document_id=document_id,
        db=db,
    )

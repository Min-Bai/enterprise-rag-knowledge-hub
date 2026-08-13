from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models.user import UserORM
from ..rate_limit import enforce_ai_rate_limit
from ..schemas.ai import (
    ConversationResponse,
    DocumentAnswerRequest,
    DocumentAnswerResponse,
    KnowledgeBaseAnswerRequest,
)
from ..services.ai import (
    AiNotConfiguredError,
    AiProviderError,
    DocumentNotReadyError,
    answer_document_service,
    prepare_document_answer,
    prepare_knowledge_base_answer,
    stream_document_answer_service,
)
from ..services.conversations import (
    ConversationNotFoundError,
    get_document_conversations_service,
    get_knowledge_base_conversations_service,
)
from ..services.documents import get_document_service
from ..exceptions import DocumentNotFoundError
from ..services.knowledge_bases import KnowledgeBaseNotFoundError

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


@router.post('/document-answer/stream')
def stream_document_answer(
    request: DocumentAnswerRequest,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    enforce_ai_rate_limit(current_user.id)
    try:
        prepared = prepare_document_answer(
            request=request,
            current_user=current_user,
            db=db,
        )
        stream = stream_document_answer_service(request=request, prepared=prepared, db=db)
        return StreamingResponse(stream, media_type='text/event-stream')
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail='document not found')
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail='conversation not found')
    except DocumentNotReadyError:
        raise HTTPException(status_code=409, detail='document is not ready')
    except AiNotConfiguredError:
        raise HTTPException(status_code=503, detail='AI service is not configured')


@router.post('/knowledge-base-answer/stream')
def stream_knowledge_base_answer(
    request: KnowledgeBaseAnswerRequest,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    enforce_ai_rate_limit(current_user.id)
    try:
        prepared = prepare_knowledge_base_answer(request=request, current_user=current_user, db=db)
        return StreamingResponse(
            stream_document_answer_service(request=request, prepared=prepared, db=db),
            media_type='text/event-stream',
        )
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail='knowledge base not found')
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail='conversation not found')
    except AiNotConfiguredError:
        raise HTTPException(status_code=503, detail='AI service is not configured')


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


@router.get('/knowledge-bases/{knowledge_base_id}/conversations', response_model=list[ConversationResponse])
def get_knowledge_base_conversations(
    knowledge_base_id: int,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    try:
        from ..services.knowledge_bases import get_knowledge_base_service

        get_knowledge_base_service(db, knowledge_base_id, current_user.id)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail='knowledge base not found')
    return get_knowledge_base_conversations_service(
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        db=db,
    )

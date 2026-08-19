from fastapi import APIRouter, Depends, HTTPException, Query
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
    AnswerFeedbackRequest,
    ConversationMessageResponse,
    TableQuestionRequest, KnowledgeBaseToolResponse,
)
from ..services.answer_feedback import AnswerFeedbackNotFoundError, save_answer_feedback
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
    delete_conversation_service,
    get_document_conversations_service,
    get_knowledge_base_conversations_service,
)
from ..services.documents import get_document_service
from ..exceptions import DocumentNotFoundError
from ..services.knowledge_bases import KnowledgeBaseNotFoundError
from ..services.ai_tools import answer_table_question, extract_information, summarize_knowledge_base

router = APIRouter(prefix='/ai', tags=['ai'])


@router.post('/knowledge-bases/{knowledge_base_id}/summarize', response_model=KnowledgeBaseToolResponse)
def summarize_knowledge_base_route(knowledge_base_id: int, db: Session = Depends(get_db), current_user: UserORM = Depends(get_current_user)):
    enforce_ai_rate_limit(current_user.id)
    try:
        result, sources = summarize_knowledge_base(knowledge_base_id=knowledge_base_id, user=current_user, db=db)
        return {"result": result, "sources": sources}
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail='knowledge base not found')
    except AiNotConfiguredError:
        raise HTTPException(status_code=503, detail='AI service is not configured')
    except AiProviderError:
        raise HTTPException(status_code=502, detail='AI provider request failed')


@router.post('/knowledge-bases/{knowledge_base_id}/extract', response_model=KnowledgeBaseToolResponse)
def extract_knowledge_base_route(knowledge_base_id: int, db: Session = Depends(get_db), current_user: UserORM = Depends(get_current_user)):
    enforce_ai_rate_limit(current_user.id)
    try:
        result, sources = extract_information(knowledge_base_id=knowledge_base_id, user=current_user, db=db)
        return {"result": result, "sources": sources}
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail='knowledge base not found')
    except AiNotConfiguredError:
        raise HTTPException(status_code=503, detail='AI service is not configured')
    except AiProviderError:
        raise HTTPException(status_code=502, detail='AI provider request failed')


@router.post('/knowledge-bases/{knowledge_base_id}/table-query', response_model=KnowledgeBaseToolResponse)
def table_query_route(knowledge_base_id: int, payload: TableQuestionRequest, db: Session = Depends(get_db), current_user: UserORM = Depends(get_current_user)):
    if payload.knowledge_base_id != knowledge_base_id:
        raise HTTPException(status_code=400, detail='knowledge base id does not match')
    enforce_ai_rate_limit(current_user.id)
    try:
        result, sources = answer_table_question(knowledge_base_id=knowledge_base_id, question=payload.question, user=current_user, db=db)
        return {"result": result, "sources": sources}
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail='knowledge base not found')
    except AiNotConfiguredError:
        raise HTTPException(status_code=503, detail='AI service is not configured')
    except AiProviderError:
        raise HTTPException(status_code=502, detail='AI provider request failed')


@router.delete('/conversations/{conversation_id}', status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    try:
        delete_conversation_service(
            conversation_id=conversation_id,
            user_id=current_user.id,
            db=db,
        )
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail='conversation not found')


@router.put('/answer-messages/{message_id}/feedback', response_model=ConversationMessageResponse)
def submit_answer_feedback(
    message_id: int,
    payload: AnswerFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    try:
        return save_answer_feedback(
            message_id=message_id,
            user_id=current_user.id,
            feedback=payload.feedback,
            comment=payload.comment,
            db=db,
        )
    except AnswerFeedbackNotFoundError:
        raise HTTPException(status_code=404, detail='answer message not found')


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
        return StreamingResponse(stream, media_type='text/event-stream', headers={'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})
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
            headers={'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'},
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
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
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
        limit=limit,
        offset=offset,
        db=db,
    )


@router.get('/knowledge-bases/{knowledge_base_id}/conversations', response_model=list[ConversationResponse])
def get_knowledge_base_conversations(
    knowledge_base_id: int,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
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
        limit=limit,
        offset=offset,
        db=db,
    )

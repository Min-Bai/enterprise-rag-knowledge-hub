import logging

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, RAG_MIN_SCORE
from ..exceptions import DocumentNotFoundError
from ..models.document import DocumentORM
from ..models.user import UserORM
from ..schemas.ai import DocumentAnswerRequest, DocumentAnswerResponse, SourceItem
from .document_vectors import search_document_chunks
from .rag_prompt import build_document_answer_messages
from .conversations import (
    ConversationNotFoundError,
    get_conversation_history,
    get_or_create_conversation_service,
    save_conversation_turn,
)

logger = logging.getLogger(__name__)


class AiNotConfiguredError(Exception):
    pass


class AiProviderError(Exception):
    pass


class DocumentNotReadyError(Exception):
    pass


def get_model_message(response: requests.Response) -> dict[str, object]:
    data = response.json()
    if not isinstance(data, dict):
        raise AiProviderError('model response is not an object')
    choices = data.get('choices')
    if not isinstance(choices, list) or not choices:
        raise AiProviderError('model response has no choices')
    choice = choices[0]
    if not isinstance(choice, dict) or choice.get('finish_reason') == 'length':
        raise AiProviderError('model response is invalid or truncated')
    message = choice.get('message')
    if not isinstance(message, dict):
        raise AiProviderError('model response has no message')
    return message


def answer_document_service(*, request: DocumentAnswerRequest, current_user: UserORM, db: Session) -> DocumentAnswerResponse:
    document = db.scalar(select(DocumentORM).where(DocumentORM.id == request.document_id, DocumentORM.user_id == current_user.id))
    if document is None:
        raise DocumentNotFoundError
    if document.status != 'ready':
        raise DocumentNotReadyError
    conversation = get_or_create_conversation_service(
        conversation_id=request.conversation_id,
        user_id=current_user.id,
        document_id=document.id,
        db=db,
    )
    hits = [hit for hit in search_document_chunks(question=request.question, user_id=current_user.id, document_ids=[document.id], limit=3) if float(hit['score']) >= RAG_MIN_SCORE]
    if not hits:
        answer = 'No sufficiently relevant document content was found.'
        save_conversation_turn(
            conversation=conversation,
            question=request.question,
            answer=answer,
            sources=[],
            db=db,
        )
        return DocumentAnswerResponse(
            answer=answer,
            sources=[],
            conversation_id=conversation.id,
        )
    if not DEEPSEEK_API_KEY:
        raise AiNotConfiguredError
    context = '\n\n'.join(str(hit['text']) for hit in hits)
    try:
        response = requests.post(
            f'{DEEPSEEK_BASE_URL}/chat/completions',
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'},
            json={
                'model': DEEPSEEK_MODEL,
                'messages': build_document_answer_messages(
                    context=context,
                    question=request.question,
                    history=get_conversation_history(
                        conversation_id=conversation.id,
                        db=db,
                    ),
                ),
                'stream': False, 'max_tokens': 500, 'temperature': 0.1,
            }, timeout=30,
        )
        response.raise_for_status()
        answer = str(get_model_message(response).get('content', '')).strip()
    except (KeyError, IndexError, ValueError, requests.RequestException) as error:
        logger.exception('document answer request failed')
        raise AiProviderError from error
    if not answer:
        raise AiProviderError
    sources = [
        SourceItem(
            document_id=document.id,
            filename=document.filename,
            page=hit.get('page'),
            chunk_index=int(hit['chunk_index']),
        )
        for hit in hits
    ]
    save_conversation_turn(
        conversation=conversation,
        question=request.question,
        answer=answer,
        sources=[source.model_dump() for source in sources],
        db=db,
    )
    return DocumentAnswerResponse(
        answer=answer,
        sources=sources,
        conversation_id=conversation.id,
    )

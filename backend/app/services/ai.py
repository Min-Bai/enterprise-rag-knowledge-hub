import logging
import json
from collections.abc import Iterator
from dataclasses import dataclass

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, RAG_MIN_SCORE
from ..exceptions import DocumentNotFoundError
from ..models.document import DocumentORM
from ..models.user import UserORM
from ..schemas.ai import DocumentAnswerRequest, DocumentAnswerResponse, KnowledgeBaseAnswerRequest, SourceItem
from .document_vectors import search_document_chunks
from .rag_prompt import build_document_answer_messages
from .conversations import (
    ConversationNotFoundError,
    get_conversation_history,
    get_or_create_conversation_service,
    get_or_create_knowledge_base_conversation_service,
    save_conversation_turn,
)
from .documents import get_document_service, get_ready_documents_service
from .knowledge_bases import get_knowledge_base_service

logger = logging.getLogger(__name__)


class AiNotConfiguredError(Exception):
    pass


class AiProviderError(Exception):
    pass


class DocumentNotReadyError(Exception):
    pass


@dataclass
class PreparedDocumentAnswer:
    conversation: object
    hits: list[dict[str, object]]
    sources: list[SourceItem]


def sse_event(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


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


def prepare_document_answer(
    *,
    request: DocumentAnswerRequest,
    current_user: UserORM,
    db: Session,
) -> PreparedDocumentAnswer:
    document = get_document_service(document_id=request.document_id, user_id=current_user.id, db=db)
    if document.status != 'ready':
        raise DocumentNotReadyError
    conversation = get_or_create_conversation_service(
        conversation_id=request.conversation_id,
        user_id=current_user.id,
        document_id=document.id,
        db=db,
    )
    hits = [hit for hit in search_document_chunks(question=request.question, user_id=document.user_id, document_ids=[document.id], limit=3) if float(hit['score']) >= RAG_MIN_SCORE]
    if not hits:
        return PreparedDocumentAnswer(conversation=conversation, hits=[], sources=[])
    if not DEEPSEEK_API_KEY:
        raise AiNotConfiguredError
    sources = [
        SourceItem(
            document_id=document.id,
            filename=document.filename,
            page=hit.get('page'),
            chunk_index=int(hit['chunk_index']),
        )
        for hit in hits
    ]
    return PreparedDocumentAnswer(
        conversation=conversation,
        hits=hits,
        sources=sources,
    )


def prepare_knowledge_base_answer(
    *, request: KnowledgeBaseAnswerRequest, current_user: UserORM, db: Session
) -> PreparedDocumentAnswer:
    get_knowledge_base_service(db, request.knowledge_base_id, current_user.id)
    documents = get_ready_documents_service(
        db=db,
        user_id=current_user.id,
        knowledge_base_id=request.knowledge_base_id,
    )
    conversation = get_or_create_knowledge_base_conversation_service(
        conversation_id=request.conversation_id,
        user_id=current_user.id,
        knowledge_base_id=request.knowledge_base_id,
        db=db,
    )
    filenames = {document.id: document.filename for document in documents}
    hits = [
        hit
        for hit in search_document_chunks(
            question=request.question,
            user_id=None,
            document_ids=list(filenames),
            limit=5,
            knowledge_base_id=request.knowledge_base_id,
            tags=request.tags,
        )
        if float(hit["score"]) >= RAG_MIN_SCORE
    ]
    if not hits:
        return PreparedDocumentAnswer(conversation=conversation, hits=[], sources=[])
    if not DEEPSEEK_API_KEY:
        raise AiNotConfiguredError
    return PreparedDocumentAnswer(
        conversation=conversation,
        hits=hits,
        sources=[
            SourceItem(
                document_id=int(hit["document_id"]),
                filename=filenames[int(hit["document_id"])],
                page=hit.get("page"),
                chunk_index=int(hit["chunk_index"]),
            )
            for hit in hits
        ],
    )


def create_model_request(
    *,
    request: DocumentAnswerRequest,
    conversation_id: int,
    hits: list[dict[str, object]],
    db: Session,
    stream: bool,
) -> dict[str, object]:
    context = '\n\n'.join(str(hit['text']) for hit in hits)
    return {
        'model': DEEPSEEK_MODEL,
        'messages': build_document_answer_messages(
            context=context,
            question=request.question,
            history=get_conversation_history(
                conversation_id=conversation_id,
                db=db,
            ),
        ),
        'stream': stream,
        'max_tokens': 500,
        'temperature': 0.1,
    }


def answer_document_service(*, request: DocumentAnswerRequest, current_user: UserORM, db: Session) -> DocumentAnswerResponse:
    prepared = prepare_document_answer(
        request=request,
        current_user=current_user,
        db=db,
    )
    if not prepared.hits:
        answer = 'No sufficiently relevant document content was found.'
        save_conversation_turn(
            conversation=prepared.conversation,
            question=request.question,
            answer=answer,
            sources=[],
            db=db,
        )
        return DocumentAnswerResponse(
            answer=answer,
            sources=[],
            conversation_id=prepared.conversation.id,
        )
    try:
        response = requests.post(
            f'{DEEPSEEK_BASE_URL}/chat/completions',
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'},
            json=create_model_request(
                request=request,
                conversation_id=prepared.conversation.id,
                hits=prepared.hits,
                db=db,
                stream=False,
            ),
            timeout=30,
        )
        response.raise_for_status()
        answer = str(get_model_message(response).get('content', '')).strip()
    except (KeyError, IndexError, ValueError, requests.RequestException) as error:
        logger.exception('document answer request failed')
        raise AiProviderError from error
    if not answer:
        raise AiProviderError
    save_conversation_turn(
        conversation=prepared.conversation,
        question=request.question,
        answer=answer,
        sources=[source.model_dump() for source in prepared.sources],
        db=db,
    )
    return DocumentAnswerResponse(
        answer=answer,
        sources=prepared.sources,
        conversation_id=prepared.conversation.id,
    )


def stream_document_answer_service(
    *,
    request: DocumentAnswerRequest,
    prepared: PreparedDocumentAnswer,
    db: Session,
) -> Iterator[str]:
    yield sse_event(
        'metadata',
        {
            'conversation_id': prepared.conversation.id,
            'sources': [source.model_dump() for source in prepared.sources],
        },
    )
    if not prepared.hits:
        answer = 'No sufficiently relevant document content was found.'
        save_conversation_turn(
            conversation=prepared.conversation,
            question=request.question,
            answer=answer,
            sources=[],
            db=db,
        )
        yield sse_event('token', {'text': answer})
        yield sse_event('done', {})
        return

    answer_parts: list[str] = []
    try:
        with requests.post(
            f'{DEEPSEEK_BASE_URL}/chat/completions',
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'},
            json=create_model_request(
                request=request,
                conversation_id=prepared.conversation.id,
                hits=prepared.hits,
                db=db,
                stream=True,
            ),
            timeout=30,
            stream=True,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith('data: '):
                    continue
                payload = line.removeprefix('data: ')
                if payload == '[DONE]':
                    break
                data = json.loads(payload)
                choices = data.get('choices', [])
                if not choices:
                    continue
                delta = choices[0].get('delta', {})
                text = delta.get('content')
                if text:
                    answer_parts.append(text)
                    yield sse_event('token', {'text': text})
    except (KeyError, ValueError, requests.RequestException) as error:
        logger.exception('document answer stream failed')
        yield sse_event('error', {'detail': 'AI provider request failed'})
        return

    answer = ''.join(answer_parts).strip()
    if not answer:
        yield sse_event('error', {'detail': 'AI provider returned an empty response'})
        return
    save_conversation_turn(
        conversation=prepared.conversation,
        question=request.question,
        answer=answer,
        sources=[source.model_dump() for source in prepared.sources],
        db=db,
    )
    yield sse_event('done', {})

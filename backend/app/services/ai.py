import logging
import json
from collections.abc import Iterator
from dataclasses import dataclass
from time import perf_counter

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    RAG_MIN_SCORE,
    RAG_QUERY_REWRITE_ENABLED,
)
from ..exceptions import DocumentNotFoundError
from ..models.document import DocumentORM
from ..models.user import UserORM
from ..request_context import get_request_id
from ..schemas.ai import DocumentAnswerRequest, DocumentAnswerResponse, KnowledgeBaseAnswerRequest, SourceItem
from .document_vectors import search_document_chunks
from .rag_prompt import build_document_answer_messages, build_query_rewrite_messages
from .audit_logs import write_audit_log
from .conversations import (
    ConversationNotFoundError,
    get_conversation_history,
    get_or_create_conversation_service,
    get_or_create_knowledge_base_conversation_service,
    save_conversation_turn,
)
from .documents import get_document_service, get_ready_documents_service
from .knowledge_bases import get_knowledge_base_service
from .model_providers import RuntimeModelProvider, get_runtime_model_provider
from .model_usage import record_model_usage

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
    user_id: int
    knowledge_base_id: int
    operation: str


def get_active_provider(db: Session) -> RuntimeModelProvider:
    provider = get_runtime_model_provider(db)
    # Preserve the existing environment configuration and test extension point
    # until an administrator has explicitly enabled a database provider.
    if provider.slug == "deepseek" and not provider.configured:
        return RuntimeModelProvider(
            "deepseek",
            DEEPSEEK_BASE_URL.rstrip("/"),
            DEEPSEEK_MODEL,
            DEEPSEEK_API_KEY or None,
        )
    return provider


def sse_event(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def get_model_message_from_payload(data: object) -> dict[str, object]:
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


def get_model_message(response: requests.Response) -> dict[str, object]:
    return get_model_message_from_payload(response.json())


def rewrite_retrieval_question(
    question: str, *, db: Session, user_id: int, knowledge_base_id: int,
) -> str:
    provider = RuntimeModelProvider("deepseek", DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_API_KEY or None)
    if not RAG_QUERY_REWRITE_ENABLED or not provider.api_key:
        return question

    started_at = perf_counter()
    try:
        response = requests.post(
            f"{provider.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {provider.api_key}"},
            json={
                "model": provider.model_name,
                "messages": build_query_rewrite_messages(question=question),
                "stream": False,
                "max_tokens": 120,
                "temperature": 0,
            },
            timeout=10,
        )
        response.raise_for_status()
        response_payload = response.json()
        rewritten = str(get_model_message_from_payload(response_payload).get("content", "")).strip()
    except (AiProviderError, KeyError, IndexError, ValueError, requests.RequestException):
        record_model_usage(db=db, provider=provider, operation="query_rewrite", latency_ms=(perf_counter() - started_at) * 1000, success=False, user_id=user_id, knowledge_base_id=knowledge_base_id)
        db.commit()
        logger.warning(
            "event=rag_query_rewrite_failed request_id=%s provider=deepseek",
            get_request_id(),
        )
        return question

    record_model_usage(db=db, provider=provider, operation="query_rewrite", latency_ms=(perf_counter() - started_at) * 1000, success=True, response_payload=response_payload, user_id=user_id, knowledge_base_id=knowledge_base_id)

    if not rewritten or len(rewritten) > 500:
        db.commit()
        logger.warning(
            "event=rag_query_rewrite_rejected request_id=%s provider=deepseek",
            get_request_id(),
        )
        return question

    logger.info(
        "event=rag_query_rewrite_completed request_id=%s provider=deepseek changed=%s duration_ms=%.1f",
        get_request_id(),
        rewritten != question,
        (perf_counter() - started_at) * 1000,
    )
    return rewritten


def log_retrieval_outcome(*, scope: str, scope_id: int, hits: list[dict[str, object]]) -> None:
    highest_score = max((float(hit["score"]) for hit in hits), default=0.0)
    logger.info(
        "event=rag_retrieval_completed request_id=%s scope=%s scope_id=%s hit_count=%s highest_score=%.4f abstained=%s",
        get_request_id(),
        scope,
        scope_id,
        len(hits),
        highest_score,
        not hits,
    )


def write_retrieval_audit_log(
    *,
    actor_user_id: int,
    knowledge_base_id: int,
    target_type: str,
    target_id: int,
    hits: list[dict[str, object]],
    db: Session,
) -> None:
    highest_score = max((float(hit["score"]) for hit in hits), default=0.0)
    write_audit_log(
        actor_user_id=actor_user_id,
        action="rag.retrieval_completed",
        target_type=target_type,
        target_id=target_id,
        knowledge_base_id=knowledge_base_id,
        details={
            "hit_count": len(hits),
            "highest_score": round(highest_score, 4),
            "abstained": not hits,
        },
        db=db,
        commit=False,
    )


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
    retrieval_question = rewrite_retrieval_question(request.question, db=db, user_id=current_user.id, knowledge_base_id=document.knowledge_base_id)
    hits = [hit for hit in search_document_chunks(question=retrieval_question, user_id=document.user_id, document_ids=[document.id], limit=3) if float(hit['score']) >= RAG_MIN_SCORE]
    log_retrieval_outcome(scope="document", scope_id=document.id, hits=hits)
    write_retrieval_audit_log(
        actor_user_id=current_user.id,
        knowledge_base_id=document.knowledge_base_id,
        target_type="document",
        target_id=document.id,
        hits=hits,
        db=db,
    )
    if not hits:
        return PreparedDocumentAnswer(conversation=conversation, hits=[], sources=[], user_id=current_user.id, knowledge_base_id=document.knowledge_base_id, operation="document_answer")
    if not get_active_provider(db).api_key:
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
        user_id=current_user.id,
        knowledge_base_id=document.knowledge_base_id,
        operation="document_answer",
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
    retrieval_question = rewrite_retrieval_question(request.question, db=db, user_id=current_user.id, knowledge_base_id=request.knowledge_base_id)
    hits = [
        hit
        for hit in search_document_chunks(
            question=retrieval_question,
            user_id=None,
            document_ids=list(filenames),
            limit=5,
            knowledge_base_id=request.knowledge_base_id,
            tags=request.tags,
        )
        if float(hit["score"]) >= RAG_MIN_SCORE
    ]
    log_retrieval_outcome(
        scope="knowledge_base",
        scope_id=request.knowledge_base_id,
        hits=hits,
    )
    write_retrieval_audit_log(
        actor_user_id=current_user.id,
        knowledge_base_id=request.knowledge_base_id,
        target_type="knowledge_base",
        target_id=request.knowledge_base_id,
        hits=hits,
        db=db,
    )
    if not hits:
        return PreparedDocumentAnswer(conversation=conversation, hits=[], sources=[], user_id=current_user.id, knowledge_base_id=request.knowledge_base_id, operation="knowledge_base_answer")
    if not get_active_provider(db).api_key:
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
        user_id=current_user.id,
        knowledge_base_id=request.knowledge_base_id,
        operation="knowledge_base_answer",
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
    provider = get_active_provider(db)
    payload: dict[str, object] = {
        'model': provider.model_name,
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
    if stream:
        payload["stream_options"] = {"include_usage": True}
    return payload


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
        provider_started_at = perf_counter()
        provider = get_active_provider(db)
        response = requests.post(
            f'{provider.base_url}/chat/completions',
            headers={'Authorization': f'Bearer {provider.api_key}'},
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
        response_payload = response.json()
        message = get_model_message_from_payload(response_payload)
        answer = str(message.get('content', '')).strip()
    except (KeyError, IndexError, ValueError, requests.RequestException) as error:
        if 'provider' in locals() and 'provider_started_at' in locals():
            record_model_usage(db=db, provider=provider, operation=prepared.operation, latency_ms=(perf_counter() - provider_started_at) * 1000, success=False, user_id=prepared.user_id, knowledge_base_id=prepared.knowledge_base_id)
            db.commit()
        logger.exception(
            "event=rag_provider_failed request_id=%s provider=deepseek stream=false",
            get_request_id(),
        )
        raise AiProviderError from error
    logger.info(
        "event=rag_provider_completed request_id=%s provider=deepseek stream=false duration_ms=%.1f",
        get_request_id(),
        (perf_counter() - provider_started_at) * 1000,
    )
    if not answer:
        record_model_usage(db=db, provider=provider, operation=prepared.operation, latency_ms=(perf_counter() - provider_started_at) * 1000, success=False, user_id=prepared.user_id, knowledge_base_id=prepared.knowledge_base_id)
        db.commit()
        raise AiProviderError
    record_model_usage(db=db, provider=provider, operation=prepared.operation, latency_ms=(perf_counter() - provider_started_at) * 1000, success=True, response_payload=response_payload, user_id=prepared.user_id, knowledge_base_id=prepared.knowledge_base_id)
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
    response_payload: dict[str, object] | None = None
    try:
        provider_started_at = perf_counter()
        provider = get_active_provider(db)
        with requests.post(
            f'{provider.base_url}/chat/completions',
            headers={'Authorization': f'Bearer {provider.api_key}'},
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
                if isinstance(data, dict) and isinstance(data.get("usage"), dict):
                    response_payload = data
                choices = data.get('choices', [])
                if not choices:
                    continue
                delta = choices[0].get('delta', {})
                text = delta.get('content')
                if text:
                    answer_parts.append(text)
                    yield sse_event('token', {'text': text})
    except (KeyError, ValueError, requests.RequestException) as error:
        if 'provider' in locals() and 'provider_started_at' in locals():
            record_model_usage(db=db, provider=provider, operation=prepared.operation, latency_ms=(perf_counter() - provider_started_at) * 1000, success=False, user_id=prepared.user_id, knowledge_base_id=prepared.knowledge_base_id)
            db.commit()
        logger.exception(
            "event=rag_provider_failed request_id=%s provider=deepseek stream=true",
            get_request_id(),
        )
        yield sse_event('error', {'detail': 'AI provider request failed'})
        return

    logger.info(
        "event=rag_provider_completed request_id=%s provider=deepseek stream=true duration_ms=%.1f",
        get_request_id(),
        (perf_counter() - provider_started_at) * 1000,
    )

    answer = ''.join(answer_parts).strip()
    if not answer:
        record_model_usage(db=db, provider=provider, operation=prepared.operation, latency_ms=(perf_counter() - provider_started_at) * 1000, success=False, user_id=prepared.user_id, knowledge_base_id=prepared.knowledge_base_id)
        db.commit()
        yield sse_event('error', {'detail': 'AI provider returned an empty response'})
        return
    record_model_usage(db=db, provider=provider, operation=prepared.operation, latency_ms=(perf_counter() - provider_started_at) * 1000, success=True, response_payload=response_payload, user_id=prepared.user_id, knowledge_base_id=prepared.knowledge_base_id)
    save_conversation_turn(
        conversation=prepared.conversation,
        question=request.question,
        answer=answer,
        sources=[source.model_dump() for source in prepared.sources],
        db=db,
    )
    yield sse_event('done', {})

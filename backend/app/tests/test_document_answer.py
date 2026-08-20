from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from backend.app.schemas.ai import DocumentAnswerRequest
from backend.app.schemas.ai import KnowledgeBaseAnswerRequest
from backend.app.services.ai import (
    AiNotConfiguredError,
    AiProviderError,
    DocumentNotFoundError,
    DocumentNotReadyError,
    answer_document_service,
    prepare_document_answer,
    prepare_knowledge_base_answer,
    stream_document_answer_service,
)


def make_dependencies():
    request = DocumentAnswerRequest(
        document_id=8,
        question="What is this document about?",
    )
    current_user = SimpleNamespace(id=1)
    document = SimpleNamespace(
        id=8,
        user_id=1,
        knowledge_base_id=3,
        filename="test.pdf",
        status="ready",
    )
    db = Mock()
    db.scalar.return_value = document
    return request, current_user, db


@pytest.fixture(autouse=True)
def mock_conversations(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.ai.get_or_create_conversation_service",
        Mock(return_value=SimpleNamespace(id=4)),
    )
    monkeypatch.setattr(
        "backend.app.services.ai.get_conversation_history",
        Mock(return_value=[]),
    )
    monkeypatch.setattr(
        "backend.app.services.ai.save_conversation_turn",
        Mock(),
    )
    monkeypatch.setattr(
        "backend.app.services.ai.get_document_service",
        lambda **kwargs: kwargs["db"].scalar.return_value
        if kwargs["db"].scalar.return_value is not None
        else (_ for _ in ()).throw(DocumentNotFoundError),
    )


def test_no_relevant_chunks_does_not_call_deepseek(monkeypatch):
    request, current_user, db = make_dependencies()
    search_mock = Mock(return_value=[])
    deepseek_mock = Mock()

    monkeypatch.setattr(
        "backend.app.services.ai.search_document_chunks",
        search_mock,
    )
    monkeypatch.setattr(
        "backend.app.services.ai.requests.post",
        deepseek_mock,
    )

    result = answer_document_service(
        request=request,
        current_user=current_user,
        db=db,
    )

    assert result.sources == []
    assert result.conversation_id == 4
    assert result.answer == "No sufficiently relevant document content was found."
    search_mock.assert_called_once()
    deepseek_mock.assert_not_called()


def test_document_answer_uses_the_rewritten_query_for_retrieval(monkeypatch):
    request, current_user, db = make_dependencies()
    search = Mock(return_value=[])
    monkeypatch.setattr(
        "backend.app.services.ai.rewrite_retrieval_question",
        lambda _question, **_kwargs: "annual leave policy",
    )
    monkeypatch.setattr("backend.app.services.ai.search_document_chunks", search)

    prepare_document_answer(request=request, current_user=current_user, db=db)

    assert search.call_args.kwargs["question"] == "annual leave policy"


def test_document_answer_logs_retrieval_without_question_or_document_content(monkeypatch, caplog):
    request, current_user, db = make_dependencies()
    caplog.set_level("INFO")
    monkeypatch.setattr(
        "backend.app.services.ai.search_document_chunks",
        Mock(return_value=[]),
    )

    answer_document_service(request=request, current_user=current_user, db=db)

    log = next(
        record.message
        for record in caplog.records
        if "event=rag_retrieval_completed" in record.message
    )
    assert "scope=document" in log
    assert "scope_id=8" in log
    assert "hit_count=0" in log
    assert "abstained=True" in log
    assert "request_id=-" in log
    assert request.question not in log


def test_document_answer_audits_retrieval_metadata_without_question_or_content(monkeypatch):
    request, current_user, db = make_dependencies()
    document = db.scalar.return_value
    document.knowledge_base_id = 3
    write_audit_log = Mock()
    monkeypatch.setattr(
        "backend.app.services.ai.search_document_chunks",
        Mock(return_value=[]),
    )
    monkeypatch.setattr("backend.app.services.ai.write_audit_log", write_audit_log)

    answer_document_service(request=request, current_user=current_user, db=db)

    assert write_audit_log.call_args.kwargs == {
        "actor_user_id": 1,
        "action": "rag.retrieval_completed",
        "target_type": "document",
        "target_id": 8,
        "knowledge_base_id": 3,
        "details": {
            "hit_count": 0,
            "highest_score": 0.0,
            "abstained": True,
        },
        "db": db,
        "commit": False,
    }


def test_success_returns_answer_and_sources(monkeypatch):
    request, current_user, db = make_dependencies()
    model_response = Mock()
    model_response.json.return_value = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": "This document explains testing."},
            }
        ]
    }
    model_response.raise_for_status.return_value = None

    monkeypatch.setattr(
        "backend.app.services.ai.search_document_chunks",
        Mock(
            return_value=[
                {
                    "document_id": 8,
                    "chunk_index": 2,
                    "page": 3,
                    "text": "Testing content",
                    "score": 0.91,
                }
            ]
        ),
    )
    deepseek_mock = Mock(return_value=model_response)
    monkeypatch.setattr(
        "backend.app.services.ai.requests.post",
        deepseek_mock,
    )
    monkeypatch.setattr("backend.app.services.ai.DEEPSEEK_API_KEY", "test-key")

    result = answer_document_service(
        request=request,
        current_user=current_user,
        db=db,
    )

    assert result.answer == "This document explains testing."
    assert result.conversation_id == 4
    assert result.sources[0].document_id == 8
    assert result.sources[0].filename == "test.pdf"
    assert result.sources[0].page == 3
    assert result.sources[0].chunk_index == 2
    deepseek_mock.assert_called_once()
    request_messages = deepseek_mock.call_args.kwargs["json"]["messages"]
    assert request_messages[0]["role"] == "system"
    assert "untrusted data" in request_messages[0]["content"]
    assert "<reference_material>" in request_messages[1]["content"]


def test_deepseek_error_raises_provider_error(monkeypatch, caplog):
    request, current_user, db = make_dependencies()
    caplog.set_level("ERROR")
    response = Mock()
    response.raise_for_status.side_effect = requests.RequestException

    monkeypatch.setattr(
        "backend.app.services.ai.search_document_chunks",
        Mock(
            return_value=[
                {
                    "document_id": 8,
                    "chunk_index": 2,
                    "text": "Testing content",
                    "score": 0.91,
                }
            ]
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.ai.requests.post",
        Mock(return_value=response),
    )
    monkeypatch.setattr("backend.app.services.ai.DEEPSEEK_API_KEY", "test-key")

    with pytest.raises(AiProviderError):
        answer_document_service(
            request=request,
            current_user=current_user,
            db=db,
        )

    log = next(
        record.message
        for record in caplog.records
        if "event=rag_provider_failed" in record.message
    )
    assert "request_id=-" in log
    assert "provider=deepseek" in log
    assert "stream=false" in log
    assert request.question not in log


def test_other_user_document_is_not_revealed(monkeypatch):
    request = DocumentAnswerRequest(
        document_id=8,
        question="What is this document about?",
    )
    current_user = SimpleNamespace(id=1)
    db = Mock()
    db.scalar.return_value = None
    search_mock = Mock()
    monkeypatch.setattr(
        "backend.app.services.ai.search_document_chunks",
        search_mock,
    )

    with pytest.raises(DocumentNotFoundError):
        answer_document_service(
            request=request,
            current_user=current_user,
            db=db,
        )

    search_mock.assert_not_called()


@pytest.mark.parametrize("status", ["processing", "failed"])
def test_non_ready_document_cannot_be_answered(status, monkeypatch):
    request = DocumentAnswerRequest(
        document_id=8,
        question="What is this document about?",
    )
    current_user = SimpleNamespace(id=1)
    document = SimpleNamespace(
        id=8,
        user_id=1,
        filename="test.pdf",
        status=status,
    )
    db = Mock()
    db.scalar.return_value = document
    search_mock = Mock()
    monkeypatch.setattr(
        "backend.app.services.ai.search_document_chunks",
        search_mock,
    )

    with pytest.raises(DocumentNotReadyError):
        answer_document_service(
            request=request,
            current_user=current_user,
            db=db,
        )

    search_mock.assert_not_called()


def test_missing_deepseek_key_raises_not_configured_error(monkeypatch):
    request, current_user, db = make_dependencies()
    monkeypatch.setattr(
        "backend.app.services.ai.search_document_chunks",
        Mock(
            return_value=[
                {
                    "document_id": 8,
                    "chunk_index": 2,
                    "text": "Testing content",
                    "score": 0.91,
                }
            ]
        ),
    )
    monkeypatch.setattr("backend.app.services.ai.DEEPSEEK_API_KEY", None)

    with pytest.raises(AiNotConfiguredError):
        answer_document_service(
            request=request,
            current_user=current_user,
            db=db,
        )


def test_streamed_answer_emits_tokens_and_saves_completed_turn(monkeypatch):
    request, current_user, db = make_dependencies()
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=None)
    response.raise_for_status.return_value = None
    response.iter_lines.return_value = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{"content":" world"}}]}',
        'data: [DONE]',
    ]
    save_mock = Mock()
    monkeypatch.setattr(
        "backend.app.services.ai.search_document_chunks",
        Mock(return_value=[{"document_id": 8, "chunk_index": 2, "text": "Testing content", "score": 0.91}]),
    )
    monkeypatch.setattr("backend.app.services.ai.requests.post", Mock(return_value=response))
    monkeypatch.setattr("backend.app.services.ai.DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr("backend.app.services.ai.save_conversation_turn", save_mock)

    prepared = prepare_document_answer(request=request, current_user=current_user, db=db)
    events = list(stream_document_answer_service(request=request, prepared=prepared, db=db))

    assert 'event: metadata' in events[0]
    assert '"text": "Hello"' in events[1]
    assert '"text": " world"' in events[2]
    assert 'event: done' in events[3]
    save_mock.assert_called_once()
    assert save_mock.call_args.kwargs["answer"] == "Hello world"


def test_streamed_provider_error_does_not_save_turn(monkeypatch):
    request, current_user, db = make_dependencies()
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=None)
    response.raise_for_status.side_effect = requests.RequestException
    save_mock = Mock()
    monkeypatch.setattr(
        "backend.app.services.ai.search_document_chunks",
        Mock(return_value=[{"document_id": 8, "chunk_index": 2, "text": "Testing content", "score": 0.91}]),
    )
    monkeypatch.setattr("backend.app.services.ai.requests.post", Mock(return_value=response))
    monkeypatch.setattr("backend.app.services.ai.DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr("backend.app.services.ai.save_conversation_turn", save_mock)

    prepared = prepare_document_answer(request=request, current_user=current_user, db=db)
    events = list(stream_document_answer_service(request=request, prepared=prepared, db=db))

    assert len(events) == 2
    assert 'event: error' in events[-1]
    save_mock.assert_not_called()


def test_streamed_no_hit_answer_saves_once(monkeypatch):
    request, current_user, db = make_dependencies()
    save_mock = Mock()
    monkeypatch.setattr("backend.app.services.ai.search_document_chunks", Mock(return_value=[]))
    monkeypatch.setattr("backend.app.services.ai.save_conversation_turn", save_mock)

    prepared = prepare_document_answer(request=request, current_user=current_user, db=db)
    events = list(stream_document_answer_service(request=request, prepared=prepared, db=db))

    assert len(events) == 3
    assert 'event: token' in events[1]
    save_mock.assert_called_once()


def test_knowledge_base_answer_retrieves_only_ready_documents(monkeypatch):
    current_user = SimpleNamespace(id=1)
    db = Mock()
    documents = [
        SimpleNamespace(id=8, user_id=1, filename="handbook.pdf"),
        SimpleNamespace(id=9, user_id=1, filename="benefits.pdf"),
    ]
    search_mock = Mock(return_value=[
        {"document_id": 9, "chunk_index": 3, "page": 2, "text": "Benefits", "score": 0.91},
    ])
    monkeypatch.setattr("backend.app.services.ai.get_knowledge_base_service", Mock())
    monkeypatch.setattr("backend.app.services.ai.get_ready_documents_service", Mock(return_value=documents))
    monkeypatch.setattr("backend.app.services.ai.get_or_create_knowledge_base_conversation_service", Mock(return_value=SimpleNamespace(id=7)))
    monkeypatch.setattr("backend.app.services.ai.search_document_chunks", search_mock)
    monkeypatch.setattr("backend.app.services.ai.DEEPSEEK_API_KEY", "test-key")

    prepared = prepare_knowledge_base_answer(
        request=KnowledgeBaseAnswerRequest(knowledge_base_id=3, question="What benefits are available?"),
        current_user=current_user,
        db=db,
    )

    assert prepared.conversation.id == 7
    assert prepared.sources[0].filename == "benefits.pdf"
    assert search_mock.call_args.kwargs["document_ids"] == [8, 9]


def test_knowledge_base_answer_audits_retrieval_metadata(monkeypatch):
    current_user = SimpleNamespace(id=1)
    db = Mock()
    write_audit_log = Mock()
    monkeypatch.setattr("backend.app.services.ai.get_knowledge_base_service", Mock())
    monkeypatch.setattr("backend.app.services.ai.get_ready_documents_service", Mock(return_value=[]))
    monkeypatch.setattr(
        "backend.app.services.ai.get_or_create_knowledge_base_conversation_service",
        Mock(return_value=SimpleNamespace(id=7)),
    )
    monkeypatch.setattr("backend.app.services.ai.search_document_chunks", Mock(return_value=[]))
    monkeypatch.setattr("backend.app.services.ai.write_audit_log", write_audit_log)

    result = prepare_knowledge_base_answer(
        request=KnowledgeBaseAnswerRequest(knowledge_base_id=3, question="What policies apply?"),
        current_user=current_user,
        db=db,
    )

    assert result.hits == []
    assert write_audit_log.call_args.kwargs["knowledge_base_id"] == 3
    assert write_audit_log.call_args.kwargs["target_type"] == "knowledge_base"
    assert write_audit_log.call_args.kwargs["details"] == {
        "hit_count": 0,
        "highest_score": 0.0,
        "abstained": True,
    }

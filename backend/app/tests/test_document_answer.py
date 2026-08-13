from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from backend.app.schemas.ai import DocumentAnswerRequest
from backend.app.services.ai import (
    AiNotConfiguredError,
    AiProviderError,
    DocumentNotFoundError,
    DocumentNotReadyError,
    answer_document_service,
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
        filename="test.pdf",
        status="ready",
    )
    db = Mock()
    db.scalar.return_value = document
    return request, current_user, db


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
    assert result.answer == "No sufficiently relevant document content was found."
    search_mock.assert_called_once()
    deepseek_mock.assert_not_called()


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
    assert result.sources[0].document_id == 8
    assert result.sources[0].filename == "test.pdf"
    assert result.sources[0].page == 3
    assert result.sources[0].chunk_index == 2
    deepseek_mock.assert_called_once()
    request_messages = deepseek_mock.call_args.kwargs["json"]["messages"]
    assert request_messages[0]["role"] == "system"
    assert "untrusted data" in request_messages[0]["content"]
    assert "<reference_material>" in request_messages[1]["content"]


def test_deepseek_error_raises_provider_error(monkeypatch):
    request, current_user, db = make_dependencies()
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

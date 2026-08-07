from types import SimpleNamespace

from fastapi.testclient import TestClient

from python_practice.day57.auth import get_current_user
from python_practice.day57.main import app
from python_practice.day57.schemas.ai import DocumentAnswerResponse
from python_practice.day57.services.ai import DocumentNotReadyError,AiProviderError,DocumentNotFoundError


client = TestClient(app)


def test_document_answer_route_returns_answer(monkeypatch):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )

    monkeypatch.setattr(
        "python_practice.day57.routers.ai.answer_document_service",
        lambda **kwargs: DocumentAnswerResponse(
            answer="This is the answer.",
            sources=[],
        ),
    )

    try:
        response = client.post(
            "/ai/document-answer",
            json={
                "document_id": 8,
                "question": "What is this document about?",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["answer"] == "This is the answer."

def test_document_answer_rejects_empty_question(monkeypatch):
    service_mock = []

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )

    monkeypatch.setattr(
        "python_practice.day57.routers.ai.answer_document_service",
        lambda **kwargs: service_mock.append(kwargs),
    )

    try:
        response = client.post(
            "/ai/document-answer",
            json={
                "document_id": 8,
                "question": "",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422
    assert service_mock == []

def test_document_answer_returns_409_when_document_is_not_ready(monkeypatch):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )

    monkeypatch.setattr(
        "python_practice.day57.routers.ai.enforce_ai_rate_limit",
        lambda user_id: None,
    )

    def raise_not_ready(**kwargs):
        raise DocumentNotReadyError

    monkeypatch.setattr(
        "python_practice.day57.routers.ai.answer_document_service",
        raise_not_ready,
    )

    try:
        response = client.post(
            "/ai/document-answer",
            json={
                "document_id": 8,
                "question": "What is this document about?",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 409
    assert response.json()["detail"] == "document is not ready"

def test_document_answer_returns_502_when_ai_provider_fails(monkeypatch):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )

    monkeypatch.setattr(
        "python_practice.day57.routers.ai.enforce_ai_rate_limit",
        lambda user_id: None,
    )

    def raise_provider_error(**kwargs):
        raise AiProviderError

    monkeypatch.setattr(
        "python_practice.day57.routers.ai.answer_document_service",
        raise_provider_error,
    )

    try:
        response = client.post(
            "/ai/document-answer",
            json={
                "document_id": 8,
                "question": "What is this document about?",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 502
    assert response.json()["detail"] == "AI provider request failed"

def test_document_answer_returns_404_when_document_is_not_found(monkeypatch):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )

    monkeypatch.setattr(
        "python_practice.day57.routers.ai.enforce_ai_rate_limit",
        lambda user_id: None,
    )

    def raise_not_found(**kwargs):
        raise DocumentNotFoundError

    monkeypatch.setattr(
        "python_practice.day57.routers.ai.answer_document_service",
        raise_not_found,
    )

    try:
        response = client.post(
            "/ai/document-answer",
            json={
                "document_id": 999,
                "question": "What is this document about?",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "document not found"

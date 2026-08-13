from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app.auth import get_current_user
from backend.app.main import app
from backend.app.schemas.ai import DocumentAnswerResponse
from backend.app.services.ai import DocumentNotReadyError,AiProviderError,DocumentNotFoundError


client = TestClient(app)


def test_document_answer_route_returns_answer(monkeypatch):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )

    monkeypatch.setattr(
        "backend.app.routers.ai.answer_document_service",
        lambda **kwargs: DocumentAnswerResponse(
            answer="This is the answer.",
            sources=[],
            conversation_id=4,
        ),
    )
    monkeypatch.setattr(
        "backend.app.routers.ai.enforce_ai_rate_limit",
        lambda user_id: None,
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
    assert response.json()["conversation_id"] == 4


def test_document_conversations_are_scoped_to_current_user(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    document = SimpleNamespace(id=8)
    get_document = []
    get_conversations = []

    monkeypatch.setattr(
        "backend.app.routers.ai.get_document_service",
        lambda **kwargs: get_document.append(kwargs) or document,
    )
    monkeypatch.setattr(
        "backend.app.routers.ai.get_document_conversations_service",
        lambda **kwargs: get_conversations.append(kwargs) or [],
    )

    try:
        response = client.get("/ai/documents/8/conversations")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert get_document[0]["user_id"] == 1
    assert get_conversations[0]["user_id"] == 1
    assert get_conversations[0]["document_id"] == 8
    assert "db" in get_conversations[0]

def test_document_answer_rejects_empty_question(monkeypatch):
    service_mock = []

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )

    monkeypatch.setattr(
        "backend.app.routers.ai.answer_document_service",
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
        "backend.app.routers.ai.enforce_ai_rate_limit",
        lambda user_id: None,
    )

    def raise_not_ready(**kwargs):
        raise DocumentNotReadyError

    monkeypatch.setattr(
        "backend.app.routers.ai.answer_document_service",
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
        "backend.app.routers.ai.enforce_ai_rate_limit",
        lambda user_id: None,
    )

    def raise_provider_error(**kwargs):
        raise AiProviderError

    monkeypatch.setattr(
        "backend.app.routers.ai.answer_document_service",
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
        "backend.app.routers.ai.enforce_ai_rate_limit",
        lambda user_id: None,
    )

    def raise_not_found(**kwargs):
        raise DocumentNotFoundError

    monkeypatch.setattr(
        "backend.app.routers.ai.answer_document_service",
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


def test_stream_route_returns_events(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr("backend.app.routers.ai.enforce_ai_rate_limit", lambda user_id: None)
    monkeypatch.setattr("backend.app.routers.ai.prepare_document_answer", lambda **kwargs: object())
    monkeypatch.setattr(
        "backend.app.routers.ai.stream_document_answer_service",
        lambda **kwargs: iter(["event: done\\ndata: {}\\n\\n"]),
    )

    try:
        response = client.post("/ai/document-answer/stream", json={"document_id": 8, "question": "What is this document about?"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in response.text


def test_stream_route_returns_409_before_response_starts(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr("backend.app.routers.ai.enforce_ai_rate_limit", lambda user_id: None)

    def raise_not_ready(**kwargs):
        raise DocumentNotReadyError

    monkeypatch.setattr("backend.app.routers.ai.prepare_document_answer", raise_not_ready)

    try:
        response = client.post("/ai/document-answer/stream", json={"document_id": 8, "question": "What is this document about?"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 409
    assert response.json()["detail"] == "document is not ready"

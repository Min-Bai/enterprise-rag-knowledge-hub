from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from backend.app.auth import get_current_user
from backend.app.main import app
from backend.app.services.knowledge_bases import KnowledgeBaseNotFoundError
from backend.app.services.knowledge_base_members import KnowledgeBaseAccessDeniedError


client = TestClient(app)


def make_document(document_id: int, filename: str):
    return SimpleNamespace(id=document_id, filename=filename, status="ready")


def test_document_search_returns_ranked_chunks_and_forwards_tags(monkeypatch):
    documents = [make_document(8, "handbook.pdf"), make_document(9, "benefits.pdf")]
    search_mock = Mock(
        return_value=[
            {
                "document_id": 9,
                "chunk_index": 2,
                "page": 4,
                "text": "Employees can claim travel benefits.",
                "score": 0.91,
            }
        ]
    )
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr("backend.app.routers.documents.get_ready_documents_service", Mock(return_value=documents))
    monkeypatch.setattr("backend.app.routers.documents.search_document_chunks", search_mock)

    try:
        response = client.post(
            "/documents/search?knowledge_base_id=3",
            json={"question": "travel benefits", "tags": [" HR ", "HR"]},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "document_id": 9,
                "filename": "benefits.pdf",
                "chunk_index": 2,
                "page": 4,
                "text": "Employees can claim travel benefits.",
                "score": 0.91,
            }
        ]
    }
    assert search_mock.call_args.kwargs["document_ids"] == [8, 9]
    assert search_mock.call_args.kwargs["tags"] == ["HR"]
    assert search_mock.call_args.kwargs["user_id"] is None


def test_document_search_returns_empty_items_when_no_chunks(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr("backend.app.routers.documents.get_ready_documents_service", Mock(return_value=[]))
    monkeypatch.setattr("backend.app.routers.documents.search_document_chunks", Mock(return_value=[]))

    try:
        response = client.post("/documents/search", json={"question": "missing policy"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_document_search_hides_missing_knowledge_base(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)

    def missing_knowledge_base(**_kwargs):
        raise KnowledgeBaseNotFoundError

    monkeypatch.setattr("backend.app.routers.documents.get_ready_documents_service", missing_knowledge_base)

    try:
        response = client.post("/documents/search?knowledge_base_id=999", json={"question": "policy"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "knowledge base not found"


def test_document_search_rejects_inaccessible_knowledge_base(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr(
        "backend.app.routers.documents.get_ready_documents_service",
        Mock(side_effect=KnowledgeBaseAccessDeniedError),
    )

    try:
        response = client.post("/documents/search?knowledge_base_id=3", json={"question": "policy"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["detail"] == "knowledge base access denied"

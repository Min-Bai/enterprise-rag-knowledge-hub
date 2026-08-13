from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app.auth import get_current_user
from backend.app.main import app
from backend.app.services.knowledge_bases import (
    KnowledgeBaseNotEmptyError,
)


client = TestClient(app)


def test_create_list_update_and_delete_knowledge_base():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)

    try:
        create_response = client.post(
            "/knowledge-bases",
            json={
                "name": "Engineering handbook",
                "description": "Team standards and runbooks",
            },
        )
        assert create_response.status_code == 201
        knowledge_base = create_response.json()
        assert knowledge_base["name"] == "Engineering handbook"

        list_response = client.get("/knowledge-bases")
        assert list_response.status_code == 200
        assert any(item["id"] == knowledge_base["id"] for item in list_response.json())

        update_response = client.patch(
            f"/knowledge-bases/{knowledge_base['id']}",
            json={"name": "Engineering knowledge base"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Engineering knowledge base"

        delete_response = client.delete(f"/knowledge-bases/{knowledge_base['id']}")
        assert delete_response.status_code == 204
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_knowledge_base_not_found_returns_404():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)

    try:
        response = client.patch(
            "/knowledge-bases/999999",
            json={"name": "Missing"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "knowledge base not found"


def test_delete_knowledge_base_with_documents_returns_409(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)

    def raise_not_empty(*_args, **_kwargs):
        raise KnowledgeBaseNotEmptyError

    monkeypatch.setattr(
        "backend.app.routers.knowledge_bases.delete_knowledge_base_service",
        raise_not_empty,
    )
    monkeypatch.setattr("backend.app.routers.knowledge_bases.get_knowledge_base_service", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("backend.app.routers.knowledge_bases.require_knowledge_base_role", lambda **_kwargs: "owner")
    try:
        response = client.delete("/knowledge-bases/1")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 409
    assert "delete all documents" in response.json()["detail"]

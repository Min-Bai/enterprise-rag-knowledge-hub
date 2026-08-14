from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app.auth import get_current_user
from backend.app.main import app


client = TestClient(app)


def test_document_list_applies_limit_and_offset(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    documents = [
        SimpleNamespace(
            id=index,
            knowledge_base_id=1,
            filename=f"document-{index}.pdf",
            status="ready",
            content_sha256=None,
            tags=[],
            chunk_count=0,
            processed_at=None,
            error_message=None,
            created_at=datetime.now(UTC),
        )
        for index in range(1, 4)
    ]
    captured = {}

    def get_documents_service(**kwargs):
        captured.update(kwargs)
        return documents[kwargs["offset"] : kwargs["offset"] + kwargs["limit"]]

    monkeypatch.setattr(
        "backend.app.routers.documents.get_documents_service",
        get_documents_service,
    )
    try:
        response = client.get("/documents?limit=1&offset=1")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()[0]["filename"] == "document-2.pdf"
    assert captured["limit"] == 1
    assert captured["offset"] == 1

from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from backend.app.auth import get_current_user
from backend.app.exceptions import DocumentNotFoundError
from backend.app.main import app


client = TestClient(app)


def test_document_download_returns_pdf_and_writes_audit_log(monkeypatch, tmp_path):
    stored_file = tmp_path / "stored.pdf"
    stored_file.write_bytes(b"%PDF-1.4 test")
    document = SimpleNamespace(id=8, knowledge_base_id=3, filename="handbook.pdf", storage_path=str(stored_file))
    audit_log = Mock()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr("backend.app.routers.documents.get_document_service", Mock(return_value=document))
    monkeypatch.setattr("backend.app.routers.documents.get_stored_document_file", Mock(return_value=stored_file))
    monkeypatch.setattr("backend.app.routers.documents.write_audit_log", audit_log)

    try:
        response = client.get("/documents/8/download")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert 'filename="handbook.pdf"' in response.headers["content-disposition"]
    assert response.content == b"%PDF-1.4 test"
    audit_log.assert_called_once()


def test_document_download_returns_404_for_missing_or_invalid_file(monkeypatch):
    document = SimpleNamespace(id=8, knowledge_base_id=3, filename="handbook.pdf", storage_path="/outside/file.pdf")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr("backend.app.routers.documents.get_document_service", Mock(return_value=document))
    monkeypatch.setattr("backend.app.routers.documents.get_stored_document_file", Mock(side_effect=FileNotFoundError))

    try:
        response = client.get("/documents/8/download")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "document not found"


def test_document_download_returns_404_for_inaccessible_document(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr("backend.app.routers.documents.get_document_service", Mock(side_effect=DocumentNotFoundError))

    try:
        response = client.get("/documents/8/download")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404

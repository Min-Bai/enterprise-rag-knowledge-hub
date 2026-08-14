from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.auth import get_current_user
from backend.app.main import app
from backend.app.services.document_storage import DocumentTooLargeError


client = TestClient(app)


def test_upload_document_enqueues_processing_job(monkeypatch):
    async def save_file(_file):
        return "/app/data/documents/queued.pdf", "a" * 64

    enqueue_mock = Mock()

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr(
        "backend.app.routers.documents.save_document_file",
        save_file,
    )
    monkeypatch.setattr(
        "backend.app.routers.documents.enqueue_document_processing",
        enqueue_mock,
    )
    monkeypatch.setattr(
        "backend.app.routers.documents.enforce_document_upload_rate_limit",
        lambda user_id: None,
    )

    try:
        response = client.post(
            "/documents",
            files={"file": ("queued.pdf", b"%PDF-test", "application/pdf")},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201
    document = response.json()
    assert document["status"] == "uploaded"
    enqueue_mock.assert_called_once_with(document["id"])

from unittest.mock import Mock

from backend.app.services import document_queue


def test_enqueue_document_processing_uses_document_queue(monkeypatch):
    queue = Mock()
    monkeypatch.setattr(document_queue, "get_document_queue", lambda: queue)

    document_queue.enqueue_document_processing(42)

    queue.enqueue.assert_called_once_with(
        document_queue.process_document,
        42,
        job_timeout="20m",
        result_ttl=0,
        failure_ttl=7 * 24 * 60 * 60,
    )

def test_upload_document_rejects_rate_limited_user(monkeypatch):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )

    def reject_upload(_user_id):
        raise HTTPException(
            status_code=429,
            detail="document upload rate limit exceeded",
        )

    monkeypatch.setattr(
        "backend.app.routers.documents.enforce_document_upload_rate_limit",
        reject_upload,
    )

    try:
        response = client.post(
            "/documents",
            files={"file": ("queued.pdf", b"%PDF-test", "application/pdf")},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 429
    assert response.json()["detail"] == "document upload rate limit exceeded"


def test_upload_document_returns_413_when_the_file_exceeds_the_size_limit(monkeypatch):
    async def reject_large_file(_file):
        raise DocumentTooLargeError("file size must not exceed 10 MB")

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr(
        "backend.app.routers.documents.save_document_file",
        reject_large_file,
    )
    monkeypatch.setattr(
        "backend.app.routers.documents.enforce_document_upload_rate_limit",
        lambda _user_id: None,
    )

    try:
        response = client.post(
            "/documents",
            files={"file": ("large.pdf", b"%PDF-test", "application/pdf")},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 413
    assert response.json() == {"detail": "file size must not exceed 10 MB"}

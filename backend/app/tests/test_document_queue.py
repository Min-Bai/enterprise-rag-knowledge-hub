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


def test_enqueue_document_processing_sends_celery_task(monkeypatch):
    task = Mock()
    monkeypatch.setattr(document_queue, "process_document_task", task)

    document_queue.enqueue_document_processing(42)

    task.apply_async.assert_called_once_with(
        args=[42],
        queue=document_queue.DOCUMENT_DEFAULT_QUEUE,
    )

def test_upload_document_rejects_rate_limited_user(monkeypatch, tmp_path):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )
    storage_path = tmp_path / "rate-limited.pdf"

    async def save_file(_file):
        storage_path.write_bytes(b"%PDF-test")
        return str(storage_path), "a" * 64

    def reject_upload(_user_id):
        raise HTTPException(
            status_code=429,
            detail="document upload rate limit exceeded",
        )

    monkeypatch.setattr(
        "backend.app.routers.documents.enforce_document_upload_rate_limit",
        reject_upload,
    )
    monkeypatch.setattr(
        "backend.app.routers.documents.save_document_file",
        save_file,
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
    assert response.json()["code"] == "DOCUMENT_UPLOAD_RATE_LIMITED"
    assert not storage_path.exists()


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
    assert response.json() == {
        "detail": "file size must not exceed 10 MB",
        "code": "DOCUMENT_FILE_TOO_LARGE",
    }


def test_invalid_document_does_not_consume_upload_rate_limit(monkeypatch):
    rate_limit = Mock()

    async def reject_large_file(_file):
        raise DocumentTooLargeError("file size must not exceed 10 MB")

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr(
        "backend.app.routers.documents.save_document_file",
        reject_large_file,
    )
    monkeypatch.setattr(
        "backend.app.routers.documents.enforce_document_upload_rate_limit",
        rate_limit,
    )

    try:
        response = client.post(
            "/documents",
            files={"file": ("large.pdf", b"%PDF-test", "application/pdf")},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 413
    rate_limit.assert_not_called()

from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from python_practice.day57.auth import get_current_user
from python_practice.day57.main import app


client = TestClient(app)


def test_upload_document_enqueues_processing_job(monkeypatch):
    async def save_file(_file):
        return "/app/data/documents/queued.pdf"

    enqueue_mock = Mock()

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr(
        "python_practice.day57.routers.documents.save_document_file",
        save_file,
    )
    monkeypatch.setattr(
        "python_practice.day57.routers.documents.enqueue_document_processing",
        enqueue_mock,
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

from python_practice.day57.services import document_queue


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
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.auth import get_current_user
from backend.app.main import app

client = TestClient(app)

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.exceptions import (
    DocumentNotFoundError,
    DocumentRetryNotAllowedError,
    DocumentReindexNotAllowedError,
)
from backend.app.services.documents import reindex_document_service, retry_document_service


def test_retry_failed_document_clears_vectors_and_resets_status(monkeypatch):
    document = SimpleNamespace(
        id=8,
        user_id=1,
        knowledge_base_id=1,
        status="failed",
        error_message="processing interrupted",
        chunk_count=5,
        processed_at=datetime.now(),
    )
    db = Mock()
    db.scalar.return_value = document
    delete_vectors = Mock()

    monkeypatch.setattr(
        "backend.app.services.documents.delete_document_vectors",
        delete_vectors,
    )
    monkeypatch.setattr("backend.app.services.documents.get_document_service", lambda **_kwargs: document)
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("backend.app.services.documents.require_knowledge_base_role", lambda **_kwargs: "owner")

    result = retry_document_service(
        document_id=8,
        user_id=1,
        db=db,
    )

    assert result is document
    assert document.status == "uploaded"
    assert document.error_message is None
    delete_vectors.assert_called_once_with(document_id=8, user_id=1)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(document)


def test_retry_rejects_missing_document():
    db = Mock()
    db.scalar.return_value = None

    with pytest.raises(DocumentNotFoundError):
        retry_document_service(document_id=8, user_id=1, db=db)


def test_retry_rejects_document_that_is_not_failed(monkeypatch):
    document = SimpleNamespace(status="ready", knowledge_base_id=1)
    db = Mock()
    db.scalar.return_value = document
    monkeypatch.setattr("backend.app.services.documents.get_document_service", lambda **_kwargs: document)
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("backend.app.services.documents.require_knowledge_base_role", lambda **_kwargs: "owner")

    with pytest.raises(DocumentRetryNotAllowedError):
        retry_document_service(document_id=8, user_id=1, db=db)


def test_reindex_ready_document_clears_vectors_and_requeues(monkeypatch):
    document = SimpleNamespace(id=8, user_id=1, knowledge_base_id=1, status="ready", error_message="old")
    db = Mock()
    delete_vectors = Mock()
    monkeypatch.setattr("backend.app.services.documents.get_document_service", lambda **_kwargs: document)
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("backend.app.services.documents.require_knowledge_base_role", lambda **_kwargs: "editor")
    monkeypatch.setattr("backend.app.services.documents.delete_document_vectors", delete_vectors)

    result = reindex_document_service(document_id=8, user_id=1, db=db)

    assert result is document
    assert document.status == "uploaded"
    assert document.error_message is None
    assert document.chunk_count == 0
    assert document.processed_at is None
    delete_vectors.assert_called_once_with(document_id=8, user_id=1)


def test_reindex_rejects_non_ready_document(monkeypatch):
    document = SimpleNamespace(knowledge_base_id=1, status="processing")
    monkeypatch.setattr("backend.app.services.documents.get_document_service", lambda **_kwargs: document)
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("backend.app.services.documents.require_knowledge_base_role", lambda **_kwargs: "editor")

    with pytest.raises(DocumentReindexNotAllowedError):
        reindex_document_service(document_id=8, user_id=1, db=Mock())

def test_retry_route_requeues_failed_document(monkeypatch):
    document = SimpleNamespace(
        id=8,
        knowledge_base_id=1,
        filename="test.pdf",
        status="uploaded",
        error_message=None,
        created_at=datetime.now(),
    )
    retry_service = Mock(return_value=document)
    enqueue = Mock()

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )
    monkeypatch.setattr(
        "backend.app.routers.documents.retry_document_service",
        retry_service,
    )
    monkeypatch.setattr(
        "backend.app.routers.documents.enqueue_document_processing",
        enqueue,
    )
    monkeypatch.setattr("backend.app.routers.documents.write_audit_log", Mock())

    try:
        response = client.post("/documents/8/retry")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["status"] == "uploaded"
    enqueue.assert_called_once_with(8)


def test_retry_route_rejects_non_failed_document(monkeypatch):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )

    def reject_retry(**_kwargs):
        raise DocumentRetryNotAllowedError

    monkeypatch.setattr(
        "backend.app.routers.documents.retry_document_service",
        reject_retry,
    )

    try:
        response = client.post("/documents/8/retry")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 409
    assert response.json()["detail"] == "only failed documents can be retried"


def test_reindex_route_requeues_ready_document(monkeypatch):
    document = SimpleNamespace(id=8, knowledge_base_id=1, filename="test.pdf", status="uploaded", error_message=None, created_at=datetime.now())
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr("backend.app.routers.documents.reindex_document_service", Mock(return_value=document))
    enqueue = Mock()
    monkeypatch.setattr("backend.app.routers.documents.enqueue_document_processing", enqueue)
    monkeypatch.setattr("backend.app.routers.documents.write_audit_log", Mock())

    try:
        response = client.post("/documents/8/reindex")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    enqueue.assert_called_once_with(8)


def test_batch_reindex_route_requeues_every_ready_document(monkeypatch):
    documents = [
        SimpleNamespace(id=8, knowledge_base_id=1, filename="first.pdf", status="uploaded", error_message=None, created_at=datetime.now()),
        SimpleNamespace(id=9, knowledge_base_id=1, filename="second.pdf", status="uploaded", error_message=None, created_at=datetime.now()),
    ]
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    monkeypatch.setattr(
        "backend.app.routers.documents.batch_reindex_documents_service",
        Mock(return_value=documents),
    )
    enqueue = Mock()
    monkeypatch.setattr("backend.app.routers.documents.enqueue_document_processing", enqueue)
    monkeypatch.setattr("backend.app.routers.documents.write_audit_log", Mock())

    try:
        response = client.post("/documents/reindex", json={"document_ids": [8, 9]})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [8, 9]
    assert enqueue.call_args_list == [((8,), {}), ((9,), {})]

from datetime import datetime
from fastapi.testclient import TestClient

from python_practice.day57.auth import get_current_user
from python_practice.day57.main import app

client = TestClient(app)

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from python_practice.day57.exceptions import (
    DocumentNotFoundError,
    DocumentRetryNotAllowedError,
)
from python_practice.day57.services.documents import retry_document_service


def test_retry_failed_document_clears_vectors_and_resets_status(monkeypatch):
    document = SimpleNamespace(
        id=8,
        user_id=1,
        status="failed",
        error_message="processing interrupted",
    )
    db = Mock()
    db.scalar.return_value = document
    delete_vectors = Mock()

    monkeypatch.setattr(
        "python_practice.day57.services.documents.delete_document_vectors",
        delete_vectors,
    )

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


def test_retry_rejects_document_that_is_not_failed():
    document = SimpleNamespace(status="ready")
    db = Mock()
    db.scalar.return_value = document

    with pytest.raises(DocumentRetryNotAllowedError):
        retry_document_service(document_id=8, user_id=1, db=db)

def test_retry_route_requeues_failed_document(monkeypatch):
    document = SimpleNamespace(
        id=8,
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
        "python_practice.day57.routers.documents.retry_document_service",
        retry_service,
    )
    monkeypatch.setattr(
        "python_practice.day57.routers.documents.enqueue_document_processing",
        enqueue,
    )

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
        "python_practice.day57.routers.documents.retry_document_service",
        reject_retry,
    )

    try:
        response = client.post("/documents/8/retry")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 409
    assert response.json()["detail"] == "only failed documents can be retried"
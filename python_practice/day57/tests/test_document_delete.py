from fastapi.testclient import TestClient

from python_practice.day57.auth import get_current_user
from python_practice.day57.main import app

client = TestClient(app)

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from python_practice.day57.exceptions import DocumentNotFoundError
from python_practice.day57.services.documents import (
    delete_document_service,
)


def test_delete_document_removes_vectors_file_and_database_record(
    monkeypatch,
    tmp_path,
):
    storage_path = tmp_path / "document.pdf"
    storage_path.write_bytes(b"%PDF-test")

    document = SimpleNamespace(
        id=8,
        user_id=1,
        storage_path=str(storage_path),
    )
    db = Mock()
    db.scalar.return_value = document
    delete_vectors_mock = Mock()

    monkeypatch.setattr(
        "python_practice.day57.services.documents.delete_document_vectors",
        delete_vectors_mock,
    )

    delete_document_service(
        document_id=8,
        user_id=1,
        db=db,
    )

    delete_vectors_mock.assert_called_once_with(
        document_id=8,
        user_id=1,
    )
    assert not storage_path.exists()
    db.delete.assert_called_once_with(document)
    db.commit.assert_called_once()


def test_delete_document_rejects_missing_or_other_users_document(
    monkeypatch,
):
    db = Mock()
    db.scalar.return_value = None
    delete_vectors_mock = Mock()

    monkeypatch.setattr(
        "python_practice.day57.services.documents.delete_document_vectors",
        delete_vectors_mock,
    )

    with pytest.raises(DocumentNotFoundError):
        delete_document_service(
            document_id=999,
            user_id=1,
            db=db,
        )

    delete_vectors_mock.assert_not_called()
    db.delete.assert_not_called()
    db.commit.assert_not_called()

def test_delete_document_route_returns_204(monkeypatch):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )
    delete_service_mock = Mock()

    monkeypatch.setattr(
        "python_practice.day57.routers.documents.delete_document_service",
        delete_service_mock,
    )

    try:
        response = client.delete("/documents/8")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 204

    called_kwargs = delete_service_mock.call_args.kwargs
    assert called_kwargs["document_id"] == 8
    assert called_kwargs["user_id"] == 1
    assert "db" in called_kwargs


def test_delete_document_route_returns_404_when_not_found(monkeypatch):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1)
    )

    def raise_not_found(**kwargs):
        raise DocumentNotFoundError

    monkeypatch.setattr(
        "python_practice.day57.routers.documents.delete_document_service",
        raise_not_found,
    )

    try:
        response = client.delete("/documents/999")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "document not found"
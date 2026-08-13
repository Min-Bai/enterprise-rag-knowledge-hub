from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.exceptions import DuplicateDocumentError
from backend.app.services.documents import create_document_service


def test_create_document_rejects_duplicate_content_in_same_knowledge_base(monkeypatch):
    db = Mock()
    db.scalar.side_effect = [SimpleNamespace(id=3), 8]
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: SimpleNamespace(id=3))
    monkeypatch.setattr("backend.app.services.documents.require_knowledge_base_role", lambda **_kwargs: "editor")

    with pytest.raises(DuplicateDocumentError):
        create_document_service(
            db=db,
            user_id=1,
            knowledge_base_id=3,
            filename="copy.pdf",
            storage_path="/tmp/copy.pdf",
            content_sha256="a" * 64,
        )


def test_create_document_keeps_hash_for_new_content(monkeypatch):
    db = Mock()
    db.scalar.return_value = None
    knowledge_base = SimpleNamespace(id=3)
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr("backend.app.services.documents.require_knowledge_base_role", lambda **_kwargs: "editor")

    create_document_service(
        db=db,
        user_id=1,
        knowledge_base_id=3,
        filename="new.pdf",
        storage_path="/tmp/new.pdf",
        content_sha256="b" * 64,
    )

    document = db.add.call_args.args[0]
    assert document.content_sha256 == "b" * 64

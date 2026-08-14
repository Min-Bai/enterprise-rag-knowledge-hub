from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.schemas.ai import KnowledgeBaseAnswerRequest
from backend.app.schemas.document import DocumentSearchRequest
from backend.app.services.document_tags import normalize_document_tags, parse_document_tags
from backend.app.services.documents import create_document_service
from backend.app.services.documents import update_document_tags_service
from backend.app.exceptions import DocumentTagUpdateNotAllowedError
from backend.app.services.knowledge_base_members import KnowledgeBaseAccessDeniedError


def test_document_tags_are_trimmed_and_deduplicated():
    assert parse_document_tags(" HR, policy, HR ,, ") == ["HR", "policy"]


def test_document_tags_reject_too_many_values():
    with pytest.raises(ValueError, match="at most 10"):
        normalize_document_tags([str(index) for index in range(11)])


def test_answer_and_search_requests_normalize_tags():
    answer = KnowledgeBaseAnswerRequest(knowledge_base_id=3, question="policy", tags=[" HR ", "HR"])
    search = DocumentSearchRequest(question="policy", tags=[" HR ", "HR"])
    assert answer.tags == ["HR"]
    assert search.tags == ["HR"]


def test_create_document_persists_normalized_tags(monkeypatch):
    knowledge_base = SimpleNamespace(id=3)
    db = Mock()
    db.scalar.return_value = None
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr("backend.app.services.documents.require_knowledge_base_role", lambda **_kwargs: "editor")

    document = create_document_service(
        db=db,
        user_id=1,
        filename="policy.pdf",
        storage_path="/tmp/policy.pdf",
        content_sha256="a" * 64,
        knowledge_base_id=3,
        tags=[" HR ", "HR", "policy"],
    )

    assert document.tags == ["HR", "policy"]


def make_tag_document(status="ready"):
    return SimpleNamespace(
        id=8,
        user_id=1,
        knowledge_base_id=3,
        status=status,
        tags=["old"],
        error_message="old error",
    )


def test_update_ready_document_tags_clears_vectors_and_requeues(monkeypatch):
    document = make_tag_document()
    db = Mock()
    delete_vectors = Mock()
    monkeypatch.setattr("backend.app.services.documents.get_document_service", lambda **_kwargs: document)
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("backend.app.services.documents.require_knowledge_base_role", lambda **_kwargs: "editor")
    monkeypatch.setattr("backend.app.services.documents.delete_document_vectors", delete_vectors)

    result = update_document_tags_service(document_id=8, user_id=1, tags=[" HR ", "policy"], db=db)

    assert result is document
    assert document.tags == ["HR", "policy"]
    assert document.status == "uploaded"
    assert document.error_message is None
    delete_vectors.assert_called_once_with(document_id=8, user_id=1)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(document)


def test_update_uploaded_document_tags_keeps_processing_state(monkeypatch):
    document = make_tag_document(status="uploaded")
    db = Mock()
    monkeypatch.setattr("backend.app.services.documents.get_document_service", lambda **_kwargs: document)
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("backend.app.services.documents.require_knowledge_base_role", lambda **_kwargs: "editor")

    update_document_tags_service(document_id=8, user_id=1, tags=["policy"], db=db)

    assert document.tags == ["policy"]
    assert document.status == "uploaded"
    db.commit.assert_called_once()


def test_update_processing_document_tags_is_rejected(monkeypatch):
    document = make_tag_document(status="processing")
    monkeypatch.setattr("backend.app.services.documents.get_document_service", lambda **_kwargs: document)
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("backend.app.services.documents.require_knowledge_base_role", lambda **_kwargs: "editor")

    with pytest.raises(DocumentTagUpdateNotAllowedError):
        update_document_tags_service(document_id=8, user_id=1, tags=["policy"], db=Mock())


def test_update_document_tags_requires_editor_access(monkeypatch):
    document = make_tag_document()
    monkeypatch.setattr("backend.app.services.documents.get_document_service", lambda **_kwargs: document)
    monkeypatch.setattr("backend.app.services.documents.get_knowledge_base_service", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        "backend.app.services.documents.require_knowledge_base_role",
        Mock(side_effect=KnowledgeBaseAccessDeniedError),
    )

    with pytest.raises(KnowledgeBaseAccessDeniedError):
        update_document_tags_service(document_id=8, user_id=1, tags=["policy"], db=Mock())

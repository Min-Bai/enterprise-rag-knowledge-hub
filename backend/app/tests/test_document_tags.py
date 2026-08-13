from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.schemas.ai import KnowledgeBaseAnswerRequest
from backend.app.schemas.document import DocumentSearchRequest
from backend.app.services.document_tags import normalize_document_tags, parse_document_tags
from backend.app.services.documents import create_document_service


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

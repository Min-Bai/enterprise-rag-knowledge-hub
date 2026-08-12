from types import SimpleNamespace
from unittest.mock import Mock

from python_practice.day57.schemas.ai import KnowledgeBaseAnswerRequest
from python_practice.day57.services.ai import answer_knowledge_base_service


def test_knowledge_base_answer_returns_sources_from_multiple_documents(monkeypatch):
    request = KnowledgeBaseAnswerRequest(
        knowledge_base_id=4,
        question="What is the leave policy?",
    )
    current_user = SimpleNamespace(id=1)
    documents = [
        SimpleNamespace(id=8, filename="handbook.pdf"),
        SimpleNamespace(id=9, filename="leave-policy.pdf"),
    ]
    db = Mock()
    db.scalars.return_value.all.return_value = documents
    model_response = Mock()
    model_response.raise_for_status.return_value = None
    model_response.json.return_value = {
        "choices": [{"message": {"content": "Employees receive annual leave."}}],
    }

    monkeypatch.setattr(
        "python_practice.day57.services.ai.get_knowledge_base_service",
        lambda *_args: SimpleNamespace(id=4),
    )
    monkeypatch.setattr(
        "python_practice.day57.services.ai.search_document_chunks",
        Mock(
            return_value=[
                {"document_id": 8, "chunk_index": 0, "text": "Handbook", "score": 0.9},
                {"document_id": 9, "chunk_index": 2, "text": "Leave policy", "score": 0.91},
            ]
        ),
    )
    monkeypatch.setattr("python_practice.day57.services.ai.DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(
        "python_practice.day57.services.ai.requests.post",
        Mock(return_value=model_response),
    )

    result = answer_knowledge_base_service(
        request=request,
        current_user=current_user,
        db=db,
    )

    assert result.answer == "Employees receive annual leave."
    assert [source.filename for source in result.sources] == [
        "handbook.pdf",
        "leave-policy.pdf",
    ]


def test_knowledge_base_answer_returns_no_context_without_ready_documents(monkeypatch):
    request = KnowledgeBaseAnswerRequest(
        knowledge_base_id=4,
        question="What is the leave policy?",
    )
    db = Mock()
    db.scalars.return_value.all.return_value = []
    search_mock = Mock()
    monkeypatch.setattr(
        "python_practice.day57.services.ai.get_knowledge_base_service",
        lambda *_args: SimpleNamespace(id=4),
    )
    monkeypatch.setattr(
        "python_practice.day57.services.ai.search_document_chunks",
        search_mock,
    )

    result = answer_knowledge_base_service(
        request=request,
        current_user=SimpleNamespace(id=1),
        db=db,
    )

    assert result.sources == []
    assert "No sufficiently relevant content" in result.answer
    search_mock.assert_called_once()

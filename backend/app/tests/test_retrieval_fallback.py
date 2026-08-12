from backend.app.services import ai
from backend.app.services.ai import (
    retrieve_project_context_details_with_fallback,
    retrieve_project_context_with_fallback,
)
from backend.app.services import vector_store


def test_retrieve_project_context_uses_keyword_fallback_when_vector_is_unavailable(
    monkeypatch,
    caplog,
):
    def raise_vector_error(question, limit):
        raise RuntimeError("Qdrant is unavailable")

    monkeypatch.setattr(vector_store, "search_knowledge", raise_vector_error)

    chunks, retrieval_mode = retrieve_project_context_with_fallback(
        "How does JWT login work?"
    )

    assert chunks
    assert retrieval_mode == "keyword_fallback"
    assert "vector retrieval failed; using keyword fallback" in caplog.text


def test_project_question_returns_without_ai_for_low_relevance(monkeypatch):
    monkeypatch.setattr(
        ai,
        "retrieve_project_context_details_with_fallback",
        lambda question: ([], "no_relevant_context"),
    )
    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", None)

    response = ai.answer_project_question_service("What is the weather today?")

    assert response.sources == []
    assert response.retrieval_mode == "no_relevant_context"


def test_vector_retrieval_accepts_relevant_results(monkeypatch):
    monkeypatch.setattr(
        vector_store,
        "search_knowledge",
        lambda question, limit: [
            {
                "source": "guide.md",
                "section": "Authentication",
                "text": "JWT login",
                "score": 0.8,
            }
        ],
    )

    chunks, retrieval_mode = retrieve_project_context_with_fallback("login")

    assert chunks == [("guide.md", "JWT login")]
    assert retrieval_mode == "vector"


def test_vector_retrieval_preserves_citation_metadata(monkeypatch):
    monkeypatch.setattr(
        vector_store,
        "search_knowledge",
        lambda question, limit: [
            {
                "source": "guide.md",
                "section": "Authentication",
                "text": "JWT login",
                "score": 0.8,
            }
        ],
    )

    chunks, retrieval_mode = retrieve_project_context_details_with_fallback("login")

    assert retrieval_mode == "vector"
    assert chunks[0].source == "guide.md"
    assert chunks[0].section == "Authentication"
    assert chunks[0].score == 0.8


def test_vector_retrieval_rejects_low_relevance_results(monkeypatch):
    monkeypatch.setattr(
        vector_store,
        "search_knowledge",
        lambda question, limit: [
            {"source": "guide.md", "text": "unrelated", "score": 0.2}
        ],
    )

    chunks, retrieval_mode = retrieve_project_context_with_fallback("weather")

    assert chunks == []
    assert retrieval_mode == "no_relevant_context"


def test_vector_retrieval_rejects_empty_results(monkeypatch):
    monkeypatch.setattr(vector_store, "search_knowledge", lambda question, limit: [])

    chunks, retrieval_mode = retrieve_project_context_with_fallback("weather")

    assert chunks == []
    assert retrieval_mode == "no_relevant_context"

import sys
from types import SimpleNamespace

from backend.app.services import ai
from backend.app.services.ai import retrieve_project_context


def test_retrieve_project_context_returns_authentication_chunk():
    results = retrieve_project_context("How does JWT login work?")

    assert results
    assert results[0][0] == "enterprise_rag_overview.md"
    assert "POST /auth/login" in results[0][1]


def test_retrieve_project_context_returns_task_chunk_for_chinese_question():
    results = retrieve_project_context("当前用户的任务如何查询")

    assert results
    assert any("GET /tasks/me" in chunk for _, chunk in results)


def test_vector_retrieval_excludes_chunks_below_score_threshold(monkeypatch):
    monkeypatch.setattr(ai, "RAG_MIN_SCORE", 0.5)
    monkeypatch.setitem(
        sys.modules,
        "backend.app.services.vector_store",
        SimpleNamespace(
            search_knowledge=lambda question, limit: [
                {
                    "source": "relevant.md",
                    "section": "Relevant",
                    "text": "Relevant context",
                    "score": 0.8,
                },
                {
                    "source": "irrelevant.md",
                    "section": "Irrelevant",
                    "text": "Irrelevant context",
                    "score": 0.2,
                },
            ]
        ),
    )

    chunks, mode = ai.retrieve_project_context_details_with_fallback(
        "test question"
    )

    assert mode == "vector"
    assert [chunk.source for chunk in chunks] == ["relevant.md"]


def test_vector_retrieval_rejects_all_chunks_below_score_threshold(monkeypatch):
    monkeypatch.setattr(ai, "RAG_MIN_SCORE", 0.5)
    monkeypatch.setitem(
        sys.modules,
        "backend.app.services.vector_store",
        SimpleNamespace(
            search_knowledge=lambda question, limit: [
                {
                    "source": "unrelated.md",
                    "section": "Unrelated",
                    "text": "Unrelated context",
                    "score": 0.2,
                }
            ]
        ),
    )

    chunks, mode = ai.retrieve_project_context_details_with_fallback(
        "test question"
    )

    assert chunks == []
    assert mode == "no_relevant_context"

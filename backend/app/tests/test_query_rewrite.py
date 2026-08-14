from unittest.mock import Mock

import requests

from backend.app.services import ai


def make_model_response(content: str) -> Mock:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [{"finish_reason": "stop", "message": {"content": content}}]
    }
    return response


def test_query_rewrite_uses_the_original_question_when_disabled(monkeypatch):
    post = Mock()
    monkeypatch.setattr(ai, "RAG_QUERY_REWRITE_ENABLED", False)
    monkeypatch.setattr(ai.requests, "post", post)

    result = ai.rewrite_retrieval_question("What leave is available?")

    assert result == "What leave is available?"
    post.assert_not_called()


def test_query_rewrite_uses_deepseek_when_enabled(monkeypatch):
    post = Mock(return_value=make_model_response("annual leave policy"))
    monkeypatch.setattr(ai, "RAG_QUERY_REWRITE_ENABLED", True)
    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(ai.requests, "post", post)

    result = ai.rewrite_retrieval_question("How much leave can I take each year?")

    assert result == "annual leave policy"
    assert post.call_args.kwargs["json"]["stream"] is False
    assert post.call_args.kwargs["json"]["max_tokens"] == 120


def test_query_rewrite_falls_back_when_the_provider_request_fails(monkeypatch, caplog):
    question = "How much leave can I take each year?"
    caplog.set_level("WARNING")
    monkeypatch.setattr(ai, "RAG_QUERY_REWRITE_ENABLED", True)
    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(ai.requests, "post", Mock(side_effect=requests.RequestException))

    assert ai.rewrite_retrieval_question(question) == question
    assert any("event=rag_query_rewrite_failed" in record.message for record in caplog.records)
    assert all(question not in record.message for record in caplog.records)

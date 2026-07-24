from python_practice.day57.services.ai import retrieve_project_context_with_fallback


def test_retrieve_project_context_uses_keyword_fallback_when_vector_is_unavailable():
    chunks, retrieval_mode = retrieve_project_context_with_fallback(
        "How does JWT login work?"
    )

    assert chunks
    assert retrieval_mode == "keyword_fallback"

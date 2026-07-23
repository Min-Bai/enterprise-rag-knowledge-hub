from python_practice.day57.services.ai import retrieve_project_context


def test_retrieve_project_context_returns_authentication_chunk():
    results = retrieve_project_context("How does JWT login work?")

    assert results
    assert results[0][0] == "todo_api_overview.md"
    assert "POST /auth/login" in results[0][1]


def test_retrieve_project_context_returns_task_chunk_for_chinese_question():
    results = retrieve_project_context("当前用户的任务如何查询")

    assert results
    assert any("GET /tasks/me" in chunk for _, chunk in results)

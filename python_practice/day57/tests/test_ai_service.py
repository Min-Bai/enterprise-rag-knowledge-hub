import pytest

from python_practice.day57.services import ai


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": "完成 React 状态管理练习",
                    }
                }
            ]
        }


def test_rewrite_task_title_returns_provider_reply(monkeypatch):
    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", "test-key")

    def fake_post(url, headers, json, timeout):
        assert url == "https://api.deepseek.com/v1/chat/completions"
        assert headers["Authorization"] == "Bearer test-key"
        assert json["messages"][-1]["content"] == "学习 React"
        assert timeout == 30
        return FakeResponse()

    monkeypatch.setattr(ai.requests, "post", fake_post)

    reply = ai.rewrite_task_title_service("学习 React")

    assert reply == "完成 React 状态管理练习"


def test_rewrite_task_title_requires_api_key(monkeypatch):
    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", None)

    with pytest.raises(ai.AiNotConfiguredError):
        ai.rewrite_task_title_service("学习 React")

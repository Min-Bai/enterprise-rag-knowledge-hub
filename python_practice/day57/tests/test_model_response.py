import pytest
import requests
from unittest.mock import Mock, patch

from python_practice.day57.services import ai
from python_practice.day57.services.ai import AiProviderError, get_model_message


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


def test_get_model_message_returns_a_complete_message():
    response = FakeResponse(
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "Complete reply"},
                }
            ]
        }
    )

    assert get_model_message(response) == {"content": "Complete reply"}


def test_get_model_message_rejects_a_truncated_response():
    response = FakeResponse(
        {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": "Incomplete"},
                }
            ]
        }
    )

    with pytest.raises(AiProviderError):
        get_model_message(response)


def test_get_model_message_rejects_empty_choices():
    with pytest.raises(AiProviderError, match="no choices"):
        get_model_message(FakeResponse({"choices": []}))


def test_rewrite_task_title_returns_model_content(monkeypatch):
    fake_response = Mock()
    fake_response.json.return_value = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": "Review Redis cache"},
            }
        ]
    }
    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", "test-key")

    with patch(
        "python_practice.day57.services.ai.requests.post",
        return_value=fake_response,
    ) as mock_post:
        result = ai.rewrite_task_title_service("redis")

    assert result == "Review Redis cache"
    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["timeout"] == 30


def test_rewrite_task_title_converts_timeout_to_provider_error(monkeypatch):
    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", "test-key")

    with patch(
        "python_practice.day57.services.ai.requests.post",
        side_effect=requests.Timeout(),
    ):
        with pytest.raises(AiProviderError):
            ai.rewrite_task_title_service("redis")

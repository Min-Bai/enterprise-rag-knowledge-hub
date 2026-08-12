import json

from backend.app.services import ai


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "title": "Learn React state",
                                "description": "Practice useState with one small page.",
                                "tags": ["React", "practice"],
                            }
                        )
                    }
                }
            ]
        }


def test_suggest_task_plan_returns_validated_json(monkeypatch):
    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", "test-key")

    def fake_post(url, headers, json, timeout):
        assert json["response_format"] == {"type": "json_object"}
        return FakeResponse()

    monkeypatch.setattr(ai.requests, "post", fake_post)

    result = ai.suggest_task_plan_service("Learn React")

    assert result.title == "Learn React state"
    assert result.tags == ["React", "practice"]

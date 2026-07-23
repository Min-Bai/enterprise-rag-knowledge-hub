import json

import requests
from pydantic import ValidationError

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from ..schemas.ai import TaskPlanSuggestionResponse


class AiNotConfiguredError(Exception):
    pass


class AiProviderError(Exception):
    pass


def rewrite_task_title_service(title: str) -> str:
    if not DEEPSEEK_API_KEY:
        raise AiNotConfiguredError

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You improve Todo task titles. Return only one concise "
                    "task title with no explanation or markdown."
                ),
            },
            {
                "role": "user",
                "content": title,
            },
        ],
        "stream": False,
    }

    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError, requests.RequestException) as error:
        raise AiProviderError from error

    if not reply:
        raise AiProviderError

    return reply


def suggest_task_plan_service(title: str) -> TaskPlanSuggestionResponse:
    if not DEEPSEEK_API_KEY:
        raise AiNotConfiguredError

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You help plan Todo tasks. Return a JSON object only, with "
                    "title, description, and tags. tags must contain one to three "
                    "short strings. Do not use markdown."
                ),
            },
            {"role": "user", "content": title},
        ],
        "response_format": {"type": "json_object"},
        "stream": False,
    }

    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return TaskPlanSuggestionResponse.model_validate(json.loads(content))
    except (
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        ValidationError,
        requests.RequestException,
    ) as error:
        raise AiProviderError from error

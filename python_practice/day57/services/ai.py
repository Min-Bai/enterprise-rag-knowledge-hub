import json
import re
from pathlib import Path

import requests
from pydantic import ValidationError

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from ..schemas.ai import ProjectQuestionResponse, TaskPlanSuggestionResponse


class AiNotConfiguredError(Exception):
    pass


class AiProviderError(Exception):
    pass


KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"


def _search_terms(text: str) -> set[str]:
    terms = set(re.findall(r"[a-z0-9_]+", text.lower()))
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    terms.update(
        "".join(chinese_chars[index : index + 2])
        for index in range(len(chinese_chars) - 1)
    )
    return terms


def retrieve_project_context(question: str, limit: int = 3) -> list[tuple[str, str]]:
    question_terms = _search_terms(question)
    matches: list[tuple[int, str, str]] = []

    for document in sorted(KNOWLEDGE_DIR.glob("*.md")):
        for chunk in document.read_text(encoding="utf-8").split("\n\n"):
            clean_chunk = chunk.strip()
            if not clean_chunk:
                continue

            score = len(question_terms & _search_terms(clean_chunk))
            if score:
                matches.append((score, document.name, clean_chunk))

    matches.sort(key=lambda match: match[0], reverse=True)
    return [(source, chunk) for _, source, chunk in matches[:limit]]


def retrieve_project_context_with_fallback(
    question: str,
    limit: int = 3,
) -> list[tuple[str, str]]:
    try:
        from .vector_store import search_knowledge

        vector_results = search_knowledge(question, limit=limit)
        if vector_results:
            return [
                (str(result["source"]), str(result["text"]))
                for result in vector_results
            ]
    except Exception:
        # The keyword implementation keeps the AI endpoint available while the
        # vector index is unavailable or still being built.
        pass

    return retrieve_project_context(question, limit=limit)


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


def answer_project_question_service(question: str) -> ProjectQuestionResponse:
    if not DEEPSEEK_API_KEY:
        raise AiNotConfiguredError

    context_chunks = retrieve_project_context_with_fallback(question)
    context = "\n\n".join(
        f"Source: {source}\n{chunk}" for source, chunk in context_chunks
    )
    if not context:
        context = "No relevant project documentation was retrieved."

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Answer questions about this Todo project using only the "
                    "provided context. If the context does not contain the answer, "
                    "say that the project documentation does not provide it."
                ),
            },
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
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
        answer = response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError, requests.RequestException) as error:
        raise AiProviderError from error

    if not answer:
        raise AiProviderError

    return ProjectQuestionResponse(
        answer=answer,
        sources=list(dict.fromkeys(source for source, _ in context_chunks)),
    )

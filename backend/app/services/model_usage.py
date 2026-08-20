from typing import Any

from sqlalchemy.orm import Session

from ..models.model_usage import ModelUsageORM
from .model_providers import RuntimeModelProvider


def response_usage(payload: dict[str, Any] | None) -> tuple[int | None, int | None, int | None]:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if not isinstance(usage, dict):
        return None, None, None
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    total = usage.get("total_tokens")
    return (
        int(prompt) if isinstance(prompt, int) and prompt >= 0 else None,
        int(completion) if isinstance(completion, int) and completion >= 0 else None,
        int(total) if isinstance(total, int) and total >= 0 else None,
    )


def estimate_cost(*, provider: RuntimeModelProvider, prompt_tokens: int | None, completion_tokens: int | None) -> float | None:
    if prompt_tokens is None or completion_tokens is None:
        return None
    if provider.input_price_per_million is None or provider.output_price_per_million is None:
        return None
    return round(
        prompt_tokens * provider.input_price_per_million / 1_000_000
        + completion_tokens * provider.output_price_per_million / 1_000_000,
        8,
    )


def record_model_usage(
    *, db: Session, provider: RuntimeModelProvider, operation: str, latency_ms: float,
    success: bool, response_payload: dict[str, Any] | None = None,
    user_id: int | None = None, knowledge_base_id: int | None = None,
) -> None:
    prompt_tokens, completion_tokens, total_tokens = response_usage(response_payload)
    db.add(ModelUsageORM(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        provider_slug=provider.slug,
        model_name=provider.model_name,
        operation=operation,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimate_cost(provider=provider, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
        latency_ms=max(0, round(latency_ms)),
        success=success,
    ))

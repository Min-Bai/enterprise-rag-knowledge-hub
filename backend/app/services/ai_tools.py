import json
from time import perf_counter
from typing import Any

import requests
from sqlalchemy.orm import Session

from ..config import AI_CONTEXT_MAX_CHARS
from ..models.user import UserORM
from ..schemas.ai import SourceItem
from .ai import AiProviderError, get_active_provider
from .document_vectors import search_document_chunks
from .documents import get_ready_documents_service
from .knowledge_bases import get_knowledge_base_service
from .model_usage import record_model_usage


def _context(hits: list[dict[str, object]]) -> str:
    return "\n\n".join(str(hit["text"]) for hit in hits)[:AI_CONTEXT_MAX_CHARS]


def _sources(hits: list[dict[str, object]], filenames: dict[int, str]) -> list[SourceItem]:
    return [SourceItem(document_id=int(hit["document_id"]), filename=filenames[int(hit["document_id"])], page=hit.get("page"), chunk_index=int(hit["chunk_index"])) for hit in hits]


def retrieve_tool_context(*, knowledge_base_id: int, question: str, user: UserORM, db: Session, limit: int = 8) -> tuple[list[dict[str, object]], list[SourceItem]]:
    get_knowledge_base_service(db, knowledge_base_id, user.id)
    documents = get_ready_documents_service(db=db, user_id=user.id, knowledge_base_id=knowledge_base_id)
    filenames = {item.id: item.filename for item in documents}
    hits = search_document_chunks(question=question, user_id=None, document_ids=list(filenames), knowledge_base_id=knowledge_base_id, limit=limit)
    return hits, _sources(hits, filenames)


def call_model(
    *, db: Session, system: str, user: str, user_id: int, knowledge_base_id: int,
    operation: str, max_tokens: int = 800, json_mode: bool = False,
) -> str:
    provider = get_active_provider(db)
    if not provider.api_key:
        from .ai import AiNotConfiguredError
        raise AiNotConfiguredError
    payload: dict[str, Any] = {"model": provider.model_name, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "stream": False, "temperature": 0.1, "max_tokens": max_tokens}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    started_at = perf_counter()
    try:
        response = requests.post(f"{provider.base_url}/chat/completions", headers={"Authorization": f"Bearer {provider.api_key}"}, json=payload, timeout=90)
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty model response")
        record_model_usage(db=db, provider=provider, operation=operation, latency_ms=(perf_counter() - started_at) * 1000, success=True, response_payload=body, user_id=user_id, knowledge_base_id=knowledge_base_id)
        db.commit()
        return content.strip()
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as error:
        record_model_usage(db=db, provider=provider, operation=operation, latency_ms=(perf_counter() - started_at) * 1000, success=False, user_id=user_id, knowledge_base_id=knowledge_base_id)
        db.commit()
        raise AiProviderError("AI provider request failed") from error


def summarize_knowledge_base(*, knowledge_base_id: int, user: UserORM, db: Session) -> tuple[str, list[SourceItem]]:
    hits, sources = retrieve_tool_context(knowledge_base_id=knowledge_base_id, question="请概括这些文档的核心主题、关键事实和主要结论", user=user, db=db, limit=12)
    if not hits:
        return "当前知识库没有可用于摘要的已完成文档。", []
    answer = call_model(db=db, system="你是企业知识库摘要助手。只能依据提供的文档内容总结；证据不足时明确说明，不得补造事实。使用中文，按主题、关键事实、结论输出。", user=_context(hits), user_id=user.id, knowledge_base_id=knowledge_base_id, operation="summarize")
    return answer, sources


def extract_information(*, knowledge_base_id: int, user: UserORM, db: Session) -> tuple[dict[str, list[str]], list[SourceItem]]:
    hits, sources = retrieve_tool_context(knowledge_base_id=knowledge_base_id, question="请找出文档中的人名、金额和合同条款", user=user, db=db, limit=12)
    if not hits:
        return {"people": [], "amounts": [], "clauses": []}, []
    raw = call_model(db=db, system="你是企业文档信息抽取器。仅依据文档内容，返回严格 JSON：{\"people\": [\"人名\"], \"amounts\": [\"金额及原文单位\"], \"clauses\": [\"条款原文或准确摘要\"]}。不确定的字段返回空数组。", user=_context(hits), user_id=user.id, knowledge_base_id=knowledge_base_id, operation="extract", max_tokens=1000, json_mode=True)
    try:
        data = json.loads(raw)
        return {key: [str(item)[:500] for item in data.get(key, []) if str(item).strip()][:50] for key in ("people", "amounts", "clauses")}, sources
    except (json.JSONDecodeError, AttributeError, TypeError) as error:
        raise AiProviderError("模型返回的信息抽取结果不是有效 JSON") from error


def answer_table_question(*, knowledge_base_id: int, question: str, user: UserORM, db: Session) -> tuple[str, list[SourceItem]]:
    hits, sources = retrieve_tool_context(knowledge_base_id=knowledge_base_id, question=question, user=user, db=db, limit=12)
    if not hits:
        return "知识库中没有足够的表格内容回答这个问题。", []
    answer = call_model(db=db, system="你是企业表格问答助手。根据提供的表格文本回答问题，保留数字单位并展示计算过程；没有证据时明确说无法确定，不得猜测。使用中文。", user=f"问题：{question}\n\n表格内容：\n{_context(hits)}", user_id=user.id, knowledge_base_id=knowledge_base_id, operation="table_query", max_tokens=1000)
    return answer, sources


def test_provider_connection(*, base_url: str, model_name: str, api_key: str | None) -> str:
    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        response = requests.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json={"model": model_name, "messages": [{"role": "user", "content": "请只回复：连接成功"}], "max_tokens": 10, "temperature": 0}, timeout=20)
        response.raise_for_status()
    except requests.RequestException as error:
        raise AiProviderError("模型连接失败，请检查地址、模型名称、密钥和网络") from error
    return "连接成功"

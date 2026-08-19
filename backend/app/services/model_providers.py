from base64 import urlsafe_b64encode
from dataclasses import dataclass
from hashlib import sha256

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, JWT_SECRET_KEY
from ..models.model_provider import ModelProviderORM
from ..schemas.model_provider import ModelProviderUpsert


@dataclass(frozen=True)
class RuntimeModelProvider:
    slug: str
    base_url: str
    model_name: str
    api_key: str | None
    configured: bool = False


def _cipher() -> Fernet:
    key = urlsafe_b64encode(sha256(JWT_SECRET_KEY.encode("utf-8")).digest())
    return Fernet(key)


def _mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    return f"...{api_key[-4:]}" if len(api_key) > 4 else "已配置"


def get_runtime_model_provider(db: Session) -> RuntimeModelProvider:
    provider = db.scalar(select(ModelProviderORM).where(ModelProviderORM.is_active.is_(True)))
    if not isinstance(provider, ModelProviderORM):
        return RuntimeModelProvider("deepseek", DEEPSEEK_BASE_URL.rstrip("/"), DEEPSEEK_MODEL, DEEPSEEK_API_KEY or None)
    api_key = _cipher().decrypt(provider.api_key_encrypted.encode("utf-8")).decode("utf-8") if provider.api_key_encrypted else None
    return RuntimeModelProvider(provider.slug, provider.base_url, provider.model_name, api_key, True)


def list_model_providers(db: Session) -> list[dict[str, object]]:
    items = list(db.scalars(select(ModelProviderORM).order_by(ModelProviderORM.display_name)).all())
    return [
        {
            "slug": item.slug,
            "display_name": item.display_name,
            "base_url": item.base_url,
            "model_name": item.model_name,
            "api_key_configured": bool(item.api_key_encrypted),
            "api_key_masked": _mask_api_key(_cipher().decrypt(item.api_key_encrypted.encode("utf-8")).decode("utf-8")) if item.api_key_encrypted else None,
            "is_active": item.is_active,
        }
        for item in items
    ]


def upsert_model_provider(db: Session, slug: str, payload: ModelProviderUpsert) -> dict[str, object]:
    provider = db.scalar(select(ModelProviderORM).where(ModelProviderORM.slug == slug))
    existing_key = provider.api_key_encrypted if provider is not None else None
    if payload.is_active and slug != "ollama" and not payload.api_key and not existing_key:
        raise ValueError("active model provider requires an API key")
    if provider is None:
        provider = ModelProviderORM(slug=slug, display_name=payload.display_name, base_url=payload.base_url, model_name=payload.model_name)
        db.add(provider)
    provider.display_name = payload.display_name
    provider.base_url = payload.base_url
    provider.model_name = payload.model_name
    if payload.api_key:
        provider.api_key_encrypted = _cipher().encrypt(payload.api_key.encode("utf-8")).decode("utf-8")
    if payload.is_active:
        db.execute(update(ModelProviderORM).values(is_active=False))
    provider.is_active = payload.is_active
    db.commit()
    db.refresh(provider)
    return next(item for item in list_model_providers(db) if item["slug"] == provider.slug)

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.main import app
from backend.app.models.model_provider import ModelProviderORM
from backend.app.models.user import UserORM
from backend.app.schemas.model_provider import ModelProviderUpsert
from backend.app.services.model_providers import get_runtime_model_provider, list_model_providers, upsert_model_provider
from backend.app.tests.conftest import TestingSessionLocal


client = TestClient(app)


def create_user(*, role: str = "user") -> tuple[str, str]:
    username = f"provider_{uuid4().hex[:10]}"
    password = "secret123"
    assert client.post("/users", json={"username": username, "password": password}).status_code == 200
    if role == "admin":
        with TestingSessionLocal() as db:
            db.scalar(select(UserORM).where(UserORM.username == username)).role = "admin"
            db.commit()
    return username, password


def test_model_provider_encrypts_key_and_runtime_provider_can_decrypt_it():
    with TestingSessionLocal() as db:
        saved = upsert_model_provider(
            db,
            f"provider-{uuid4().hex[:8]}",
            ModelProviderUpsert(
                display_name="测试模型",
                base_url="https://api.example.com/v1",
                model_name="example-chat",
                api_key="sk-top-secret-key",
                is_active=True,
            ),
        )
        row = db.scalar(select(ModelProviderORM).where(ModelProviderORM.slug == saved["slug"]))
        assert row is not None
        assert row.api_key_encrypted is not None
        assert "sk-top-secret-key" not in row.api_key_encrypted
        assert saved["api_key_configured"] is True
        assert saved["api_key_masked"] == "...-key"
        assert "api_key" not in saved
        runtime = get_runtime_model_provider(db)
        assert runtime.configured is True
        assert runtime.api_key == "sk-top-secret-key"
        assert runtime.model_name == "example-chat"


def test_model_provider_list_never_exposes_raw_api_key():
    with TestingSessionLocal() as db:
        saved = upsert_model_provider(
            db,
            f"masked-{uuid4().hex[:8]}",
            ModelProviderUpsert(
                display_name="掩码测试",
                base_url="https://api.example.com/v1",
                model_name="example-chat",
                api_key="sk-12345678",
                is_active=False,
            ),
        )
        item = next(item for item in list_model_providers(db) if item["slug"] == saved["slug"])
        assert item["api_key_masked"] == "...5678"
        assert all("sk-12345678" not in str(value) for value in item.values())


def test_model_provider_api_requires_admin_and_returns_masked_key_only():
    username, password = create_user(role="admin")
    login = client.post("/api/v1/admin/auth/login", json={"username": username, "password": password})
    admin_headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    slug = f"api-{uuid4().hex[:8]}"
    payload = {
        "display_name": "接口测试",
        "base_url": "https://api.example.com/v1",
        "model_name": "example-chat",
        "api_key": "sk-api-secret",
        "is_active": False,
    }
    forbidden = client.get("/api/v1/admin/model-providers")
    assert forbidden.status_code == 401
    response = client.put(f"/api/v1/admin/model-providers/{slug}", json=payload, headers=admin_headers)
    assert response.status_code == 200
    item = response.json()["data"]
    assert item["api_key_configured"] is True
    assert item["api_key_masked"] == "...cret"
    assert "api_key" not in item

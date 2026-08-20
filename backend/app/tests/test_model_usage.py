from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.main import app
from backend.app.models.model_usage import ModelUsageORM
from backend.app.models.user import UserORM
from backend.app.services.model_providers import RuntimeModelProvider
from backend.app.services.model_usage import estimate_cost, record_model_usage, response_usage
from backend.app.tests.conftest import TestingSessionLocal


client = TestClient(app)


def create_user(*, role: str = "user") -> tuple[str, str]:
    username = f"usage_{uuid4().hex[:10]}"
    password = "secret123"
    assert client.post("/users", json={"username": username, "password": password}).status_code == 200
    if role == "admin":
        with TestingSessionLocal() as db:
            db.scalar(select(UserORM).where(UserORM.username == username)).role = "admin"
            db.commit()
    return username, password


def test_usage_parser_and_estimate_cost_require_provider_usage_and_prices():
    provider = RuntimeModelProvider("deepseek", "https://example.com/v1", "deepseek-chat", "key", True, 1.0, 2.0)
    assert response_usage({"usage": {"prompt_tokens": 1_000_000, "completion_tokens": 500_000, "total_tokens": 1_500_000}}) == (1_000_000, 500_000, 1_500_000)
    assert estimate_cost(provider=provider, prompt_tokens=1_000_000, completion_tokens=500_000) == 2.0
    assert response_usage({}) == (None, None, None)
    assert estimate_cost(provider=RuntimeModelProvider("local", "http://localhost", "local", None), prompt_tokens=1, completion_tokens=1) is None


def test_admin_model_usage_analytics_excludes_non_admin_and_returns_aggregates():
    username, password = create_user(role="admin")
    with TestingSessionLocal() as db:
        user = db.scalar(select(UserORM).where(UserORM.username == username))
        assert user is not None
        record_model_usage(
            db=db,
            provider=RuntimeModelProvider("deepseek", "https://example.com/v1", "deepseek-chat", "key", True, 1.0, 2.0),
            operation="knowledge_base_answer",
            latency_ms=123.4,
            success=True,
            response_payload={"usage": {"prompt_tokens": 1_000_000, "completion_tokens": 500_000, "total_tokens": 1_500_000}},
            user_id=user.id,
        )
        db.commit()
        assert db.scalar(select(ModelUsageORM).where(ModelUsageORM.user_id == user.id)) is not None

    unauthorized = client.get("/api/v1/admin/analytics/model-usage")
    assert unauthorized.status_code == 401
    login = client.post("/api/v1/admin/auth/login", json={"username": username, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    response = client.get("/api/v1/admin/analytics/model-usage?days=30", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["requests"] >= 1
    assert data["summary"]["estimated_cost"] >= 2.0
    assert any(item["provider_slug"] == "deepseek" for item in data["by_provider"])

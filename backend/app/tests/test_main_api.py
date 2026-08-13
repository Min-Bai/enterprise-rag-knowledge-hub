from fastapi.testclient import TestClient
from unittest.mock import Mock
from backend.app.main import app


client = TestClient(app)

def mock_readiness_dependencies(monkeypatch):
    redis = Mock()
    qdrant = Mock()

    monkeypatch.setattr(
        "backend.app.main.redis_client",
        redis,
    )
    monkeypatch.setattr(
        "backend.app.main.get_qdrant_client",
        lambda: qdrant,
    )

    return redis, qdrant

def test_health_check(monkeypatch):
    redis, qdrant = mock_readiness_dependencies(monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "redis": "ok",
        "qdrant": "ok",
    }
    redis.ping.assert_called_once()
    qdrant.get_collections.assert_called_once()
    assert response.headers["x-request-id"]

def test_liveness_check():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert len(response.headers["x-request-id"]) == 32

def test_readiness_check(monkeypatch):
    redis, qdrant = mock_readiness_dependencies(monkeypatch)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "redis": "ok",
        "qdrant": "ok",
    }
    redis.ping.assert_called_once()
    qdrant.get_collections.assert_called_once()

def test_readiness_check_returns_503_when_qdrant_is_unavailable(
    monkeypatch,
):
    redis, qdrant = mock_readiness_dependencies(monkeypatch)
    qdrant.get_collections.side_effect = RuntimeError("Qdrant unavailable")

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "dependencies unavailable",
    }
    redis.ping.assert_called_once()

def test_readiness_check_returns_503_when_redis_is_unavailable(
    monkeypatch,
):
    redis, qdrant = mock_readiness_dependencies(monkeypatch)
    redis.ping.side_effect = RuntimeError("Redis unavailable")

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "dependencies unavailable",
    }
    qdrant.get_collections.assert_not_called()

def test_cors_allows_configured_origin():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )

def test_cors_rejects_unknown_origin():
    response = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400

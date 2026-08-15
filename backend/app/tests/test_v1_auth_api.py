from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.client import router as client_router


client = TestClient(app)


def create_user() -> tuple[str, str]:
    username = f"v1_user_{uuid4().hex[:8]}"
    password = "secret123"
    response = client.post("/users", json={"username": username, "password": password})
    assert response.status_code == 200
    return username, password


def test_client_auth_uses_envelope_cookie_refresh_and_audience_boundary():
    username, password = create_user()
    login = client.post("/api/v1/client/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    body = login.json()
    assert body["code"] == "OK"
    assert body["data"]["token_type"] == "bearer"
    assert "rag_client_refresh" in login.headers["set-cookie"]
    assert "HttpOnly" in login.headers["set-cookie"]
    csrf_cookie = next(value for value in login.headers.get_list("set-cookie") if "rag_client_refresh_csrf=" in value)
    assert "Path=/" in csrf_cookie

    access = body["data"]["access_token"]
    me = client.get("/api/v1/client/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["data"]["username"] == username

    admin = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {access}"})
    assert admin.status_code == 401
    assert admin.json()["code"] == "AUTH_INVALID_TOKEN"

    refresh = client.post(
        "/api/v1/client/auth/refresh",
        headers={"X-CSRF-Token": body["data"]["csrf_token"]},
    )
    assert refresh.status_code == 200
    assert refresh.json()["data"]["access_token"] != access


def test_v1_invalid_requests_have_the_standard_error_envelope():
    response = client.post("/api/v1/client/auth/login", json={"username": ""})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["data"] is None
    assert response.json()["request_id"]


def test_client_registration_obeys_policy_and_returns_standard_envelope(monkeypatch):
    disabled = client.get("/api/v1/client/auth/registration-status")
    assert disabled.status_code == 200
    assert isinstance(disabled.json()["data"]["enabled"], bool)

    monkeypatch.setattr(client_router, "ALLOW_SELF_REGISTRATION", True)
    username = f"registered_{uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/client/auth/register",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 201
    assert response.json()["code"] == "OK"
    assert response.json()["data"]["username"] == username

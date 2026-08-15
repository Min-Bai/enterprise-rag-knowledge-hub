from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.client import router as client_router
from backend.app.models.user import UserORM
from backend.app.models.user_invitation import UserInvitationORM
from backend.app.tests.conftest import TestingSessionLocal


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


def test_invitation_registration_is_one_time_and_works_when_public_registration_is_disabled():
    admin_username, password = create_user()
    with TestingSessionLocal() as db:
        admin = db.query(UserORM).filter(UserORM.username == admin_username).one()
        admin.role = "admin"
        db.commit()

    login = client.post("/api/v1/admin/auth/login", json={"username": admin_username, "password": password})
    assert login.status_code == 200
    access_token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    email = f"invited_{uuid4().hex[:8]}@example.com"
    invitation_response = client.post(
        "/api/v1/admin/invitations",
        json={"email": email, "expires_in_hours": 24},
        headers=headers,
    )
    assert invitation_response.status_code == 201
    invitation = invitation_response.json()["data"]
    assert invitation["email"] == email

    with TestingSessionLocal() as db:
        stored = db.get(UserInvitationORM, invitation["id"])
        assert stored is not None
        assert stored.token_hash == sha256(invitation["invitation_token"].encode("utf-8")).hexdigest()
        assert stored.token_hash != invitation["invitation_token"]

    accepted = client.post(
        "/api/v1/client/auth/accept-invitation",
        json={"username": f"accepted_{uuid4().hex[:8]}", "email": email, "password": "secret123", "invitation_token": invitation["invitation_token"]},
    )
    assert accepted.status_code == 201
    assert accepted.json()["data"]["role"] == "user"

    reused = client.post(
        "/api/v1/client/auth/accept-invitation",
        json={"username": f"reused_{uuid4().hex[:8]}", "email": email, "password": "secret123", "invitation_token": invitation["invitation_token"]},
    )
    assert reused.status_code == 400
    assert reused.json()["code"] == "INVITATION_INVALID"


def test_revoked_and_expired_invitations_cannot_be_accepted():
    admin_username, password = create_user()
    with TestingSessionLocal() as db:
        admin = db.query(UserORM).filter(UserORM.username == admin_username).one()
        admin.role = "admin"
        db.commit()
    login = client.post("/api/v1/admin/auth/login", json={"username": admin_username, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    def invite(email: str) -> dict:
        response = client.post("/api/v1/admin/invitations", json={"email": email}, headers=headers)
        assert response.status_code == 201
        return response.json()["data"]

    revoked = invite(f"revoked_{uuid4().hex[:8]}@example.com")
    assert client.delete(f"/api/v1/admin/invitations/{revoked['id']}", headers=headers).status_code == 204
    response = client.post("/api/v1/client/auth/accept-invitation", json={"username": f"revoked_{uuid4().hex[:8]}", "email": revoked["email"], "password": "secret123", "invitation_token": revoked["invitation_token"]})
    assert response.status_code == 400

    expired = invite(f"expired_{uuid4().hex[:8]}@example.com")
    with TestingSessionLocal() as db:
        invitation = db.get(UserInvitationORM, expired["id"])
        invitation.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
        db.commit()
    response = client.post("/api/v1/client/auth/accept-invitation", json={"username": f"expired_{uuid4().hex[:8]}", "email": expired["email"], "password": "secret123", "invitation_token": expired["invitation_token"]})
    assert response.status_code == 400
    assert response.json()["code"] == "INVITATION_EXPIRED"

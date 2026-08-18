from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.user import UserORM
from backend.app.models.user_invitation import UserInvitationORM
from backend.app.models.password_reset import PasswordResetORM
from backend.app.models.password_reset_request import PasswordResetRequestORM
from backend.app.models.registration_request import RegistrationRequestORM
from backend.app.services.email_delivery import EmailDeliveryError
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
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["code"] == "OK"
    assert body["data"]["token_type"] == "bearer"
    assert len(body["data"]["refresh_token"]) >= 20

    access = body["data"]["access_token"]
    me = client.get("/api/v1/client/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["data"]["username"] == username

    admin = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {access}"})
    assert admin.status_code == 401
    assert admin.json()["code"] == "AUTH_INVALID_TOKEN"

    refresh = client.post("/api/v1/client/auth/refresh", json={"refresh_token": body["data"]["refresh_token"]})
    assert refresh.status_code == 200
    assert refresh.json()["data"]["access_token"] != access


def test_client_refresh_tokens_are_isolated_between_users():
    first_username, first_password = create_user()
    second_username, second_password = create_user()
    first_client = TestClient(app)
    second_client = TestClient(app)

    first_login = first_client.post("/api/v1/client/auth/login", json={"username": first_username, "password": first_password})
    second_login = second_client.post("/api/v1/client/auth/login", json={"username": second_username, "password": second_password})
    assert first_login.status_code == second_login.status_code == 200, f"first={first_login.text}; second={second_login.text}"

    first_tokens = first_login.json()["data"]
    second_tokens = second_login.json()["data"]
    first_refresh = first_client.post("/api/v1/client/auth/refresh", json={"refresh_token": first_tokens["refresh_token"]})
    second_refresh = second_client.post("/api/v1/client/auth/refresh", json={"refresh_token": second_tokens["refresh_token"]})
    assert first_refresh.status_code == second_refresh.status_code == 200

    first_me = first_client.get("/api/v1/client/me", headers={"Authorization": f"Bearer {first_refresh.json()['data']['access_token']}"})
    second_me = second_client.get("/api/v1/client/me", headers={"Authorization": f"Bearer {second_refresh.json()['data']['access_token']}"})
    assert first_me.json()["data"]["username"] == first_username
    assert second_me.json()["data"]["username"] == second_username


def test_v1_invalid_requests_have_the_standard_error_envelope():
    response = client.post("/api/v1/client/auth/login", json={"username": ""})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["data"] is None
    assert response.json()["request_id"]


def test_client_registration_requires_admin_approval_before_login():
    status = client.get("/api/v1/client/auth/registration-status")
    assert status.status_code == 200
    assert status.json()["data"]["approval_required"] is True
    username = f"registered_{uuid4().hex[:8]}"
    email = f"{username}@example.com"
    response = client.post(
        "/api/v1/client/auth/register",
        json={"username": username, "email": email, "password": "secret123"},
    )
    assert response.status_code == 202
    assert response.json()["code"] == "OK"
    assert response.json()["data"]["status"] == "pending"
    assert client.post("/api/v1/client/auth/login", json={"username": username, "password": "secret123"}).status_code == 401

    admin_username, admin_password = create_user()
    with TestingSessionLocal() as db:
        admin = db.query(UserORM).filter(UserORM.username == admin_username).one()
        request_item = db.query(RegistrationRequestORM).filter(RegistrationRequestORM.username == username).one()
        assert request_item.password_hash != "secret123"
        admin.role = "admin"
        db.commit()
        request_id = request_item.id
    admin_login = client.post("/api/v1/admin/auth/login", json={"username": admin_username, "password": admin_password})
    headers = {"Authorization": f"Bearer {admin_login.json()['data']['access_token']}"}
    approved = client.post(f"/api/v1/admin/registration-requests/{request_id}/approve", headers=headers)
    assert approved.status_code == 201
    assert approved.json()["data"]["username"] == username
    assert client.post("/api/v1/client/auth/login", json={"username": username, "password": "secret123"}).status_code == 200


def test_client_password_reset_request_requires_admin_approval(monkeypatch):
    admin_username, admin_password = create_user()
    user_username, user_password = create_user()
    email = f"{user_username}@example.com"
    with TestingSessionLocal() as db:
        admin = db.query(UserORM).filter(UserORM.username == admin_username).one()
        user = db.query(UserORM).filter(UserORM.username == user_username).one()
        admin.role = "admin"
        user.email = email
        db.commit()
    unknown = client.post("/api/v1/client/auth/password-reset-request", json={"email": "unknown@example.com"})
    requested = client.post("/api/v1/client/auth/password-reset-request", json={"email": email})
    assert unknown.status_code == requested.status_code == 202
    with TestingSessionLocal() as db:
        request_item = db.query(PasswordResetRequestORM).filter(PasswordResetRequestORM.email == email).one()
        request_id = request_item.id
    admin_login = client.post("/api/v1/admin/auth/login", json={"username": admin_username, "password": admin_password})
    headers = {"Authorization": f"Bearer {admin_login.json()['data']['access_token']}"}
    delivered_tokens: list[str] = []

    def capture_reset_email(*, reset_token: str, **_kwargs):
        delivered_tokens.append(reset_token)

    monkeypatch.setattr("backend.app.api.admin.router.send_password_reset_email", capture_reset_email)
    approved = client.post(f"/api/v1/admin/password-reset-requests/{request_id}/approve", json={"expires_in_hours": 1}, headers=headers)
    assert approved.status_code == 201
    assert approved.json()["data"]["delivery"] == "email"
    assert "reset_token" not in approved.json()["data"]
    assert len(delivered_tokens) == 1
    assert client.post("/api/v1/client/auth/reset-password", json={"reset_token": delivered_tokens[0], "new_password": "updated123"}).status_code == 204
    assert client.post("/api/v1/client/auth/login", json={"username": user_username, "password": user_password}).status_code == 401
    assert client.post("/api/v1/client/auth/login", json={"username": user_username, "password": "updated123"}).status_code == 200


def test_password_reset_approval_stays_pending_when_email_delivery_fails(monkeypatch):
    admin_username, admin_password = create_user()
    user_username, _ = create_user()
    email = f"{user_username}@example.com"
    with TestingSessionLocal() as db:
        admin = db.query(UserORM).filter(UserORM.username == admin_username).one()
        user = db.query(UserORM).filter(UserORM.username == user_username).one()
        admin.role = "admin"
        user.email = email
        db.add(PasswordResetRequestORM(email=email))
        db.commit()
        user_id = user.id
        request_id = db.query(PasswordResetRequestORM).filter(PasswordResetRequestORM.email == email).one().id

    def fail_email_delivery(**_kwargs):
        raise EmailDeliveryError("test delivery failure")

    monkeypatch.setattr("backend.app.api.admin.router.send_password_reset_email", fail_email_delivery)
    login = client.post("/api/v1/admin/auth/login", json={"username": admin_username, "password": admin_password})
    response = client.post(
        f"/api/v1/admin/password-reset-requests/{request_id}/approve",
        json={"expires_in_hours": 1},
        headers={"Authorization": f"Bearer {login.json()['data']['access_token']}"},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "PASSWORD_RESET_EMAIL_DELIVERY_FAILED"
    with TestingSessionLocal() as db:
        request_item = db.get(PasswordResetRequestORM, request_id)
        assert request_item is not None
        assert request_item.status == "pending"
        assert db.query(PasswordResetORM).filter(PasswordResetORM.user_id == user_id).count() == 0


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


def test_admin_password_reset_is_one_time_and_invalidates_existing_sessions():
    admin_username, admin_password = create_user()
    target_username, target_password = create_user()
    with TestingSessionLocal() as db:
        admin = db.query(UserORM).filter(UserORM.username == admin_username).one()
        admin.role = "admin"
        db.commit()

    admin_login = client.post("/api/v1/admin/auth/login", json={"username": admin_username, "password": admin_password})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['data']['access_token']}"}
    target_login = client.post("/api/v1/client/auth/login", json={"username": target_username, "password": target_password})
    old_access_token = target_login.json()["data"]["access_token"]

    with TestingSessionLocal() as db:
        target = db.query(UserORM).filter(UserORM.username == target_username).one()
        target_id = target.id

    first_link = client.post(f"/api/v1/admin/users/{target_id}/password-reset", json={"expires_in_hours": 1}, headers=admin_headers)
    assert first_link.status_code == 201
    first_token = first_link.json()["data"]["reset_token"]
    second_link = client.post(f"/api/v1/admin/users/{target_id}/password-reset", json={"expires_in_hours": 1}, headers=admin_headers)
    assert second_link.status_code == 201
    second_token = second_link.json()["data"]["reset_token"]
    assert first_token != second_token

    with TestingSessionLocal() as db:
        reset = db.query(PasswordResetORM).filter(PasswordResetORM.token_hash == sha256(second_token.encode("utf-8")).hexdigest()).one()
        assert reset.token_hash != second_token
        assert db.query(PasswordResetORM).filter(PasswordResetORM.token_hash == sha256(first_token.encode("utf-8")).hexdigest()).one().revoked_at is not None

    old_link = client.post("/api/v1/client/auth/reset-password", json={"reset_token": first_token, "new_password": "updated123"})
    assert old_link.status_code == 400
    reset = client.post("/api/v1/client/auth/reset-password", json={"reset_token": second_token, "new_password": "updated123"})
    assert reset.status_code == 204

    old_session = client.get("/api/v1/client/me", headers={"Authorization": f"Bearer {old_access_token}"})
    assert old_session.status_code == 401
    assert client.post("/api/v1/client/auth/login", json={"username": target_username, "password": target_password}).status_code == 401
    assert client.post("/api/v1/client/auth/login", json={"username": target_username, "password": "updated123"}).status_code == 200
    assert client.post("/api/v1/client/auth/reset-password", json={"reset_token": second_token, "new_password": "another123"}).status_code == 400

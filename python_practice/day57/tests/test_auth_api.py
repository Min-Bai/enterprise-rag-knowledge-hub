from uuid import uuid4

from fastapi.testclient import TestClient

from python_practice.day57.main import app
from python_practice.day57.security import create_access_token


client = TestClient(app)


def test_login_returns_access_token():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post(
        "/users",
        json={
            "username": username,
            "password": "secret123",
        },
    )
    assert create_response.status_code == 200

    response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": "secret123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["access_token"], str)
    assert data["token_type"] == "bearer"

def test_login_rejects_wrong_password():
    username = f"user_{uuid4().hex[:8]}"

    client.post(
        "/users",
        json={
            "username": username,
            "password": "secret123",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid username or password"

def test_login_rejects_inactive_user():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post(
        "/users",
        json={
            "username": username,
            "password": "secret123",
        },
    )
    user_id = create_response.json()["id"]

    deactivate_response = client.patch(
        f"/users/{user_id}/deactivate",
        headers={"Authorization": f"Bearer {create_access_token(1, 0)}"},
    )
    assert deactivate_response.status_code == 200

    response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": "secret123",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "user is inactive"

def test_change_my_password():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post(
        "/users",
        json={
            "username": username,
            "password": "old-password",
        },
    )
    user_id = create_response.json()["id"]
    token = create_access_token(user_id, 0)

    response = client.patch(
        "/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "old-password",
            "new_password": "new-password",
        },
    )

    assert response.status_code == 204

    old_login_response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": "old-password",
        },
    )
    assert old_login_response.status_code == 401

    new_login_response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": "new-password",
        },
    )
    assert new_login_response.status_code == 200

def test_change_my_password_rejects_wrong_old_password():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post(
        "/users",
        json={
            "username": username,
            "password": "correct-password",
        },
    )
    user_id = create_response.json()["id"]
    token = create_access_token(user_id, 0)

    response = client.patch(
        "/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "wrong-password",
            "new_password": "new-password",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "old password is incorrect"

    login_response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": "correct-password",
        },
    )

    assert login_response.status_code == 200

def test_change_password_invalidates_existing_token():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post(
        "/users",
        json={
            "username": username,
            "password": "old-password",
        },
    )
    user_id = create_response.json()["id"]
    old_token = create_access_token(user_id, 0)

    change_response = client.patch(
        "/users/me/password",
        headers={"Authorization": f"Bearer {old_token}"},
        json={
            "old_password": "old-password",
            "new_password": "new-password",
        },
    )
    assert change_response.status_code == 204

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {old_token}"},
    )

    assert response.status_code == 401

    login_response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": "new-password",
        },
    )
    assert login_response.status_code == 200

    new_token = login_response.json()["access_token"]

    me_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {new_token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["id"] == user_id

def test_logout_invalidates_existing_token():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post(
        "/users",
        json={
            "username": username,
            "password": "secret123",
        },
    )
    user_id = create_response.json()["id"]
    token = create_access_token(user_id, 0)

    logout_response = client.post(
        "/users/me/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert logout_response.status_code == 204

    me_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 401

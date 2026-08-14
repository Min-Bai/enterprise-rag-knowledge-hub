from fastapi.testclient import TestClient
from uuid import uuid4

from backend.app.main import app
from backend.app.security import create_access_token


client = TestClient(app)


def auth_headers(user_id: int):
    return {"Authorization": f"Bearer {create_access_token(user_id, 0)}"}


def test_users_ping():
    response = client.get("/users/ping")

    assert response.status_code == 200
    assert response.json() == {"message": "users router ok"}


def test_get_me_requires_token():
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing token"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_get_me_rejects_invalid_token():
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid or expired token"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_get_me_returns_current_user_with_valid_token():
    username = f"user_{uuid4().hex[:8]}"
    email = f"{username}@example.com"
    create_response = client.post(
        "/users",
        json={"username": username, "email": email, "password": "secret123"},
    )
    assert create_response.status_code == 200
    created_user = create_response.json()

    response = client.get(
        "/users/me",
        headers={
            "Authorization": (
                f"Bearer {create_access_token(created_user['id'], 0)}"
            )
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == created_user["id"]
    assert data["username"] == username
    assert data["email"] == email
    assert data["is_active"] is True


def test_get_me_rejects_missing_user_token():
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {create_access_token(999999, 0)}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid token"
    assert response.headers["WWW-Authenticate"] == "Bearer"

def test_get_me_rejects_inactive_user():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert create_response.status_code == 200
    user = create_response.json()

    deactivate_response = client.patch(
        f"/users/{user['id']}/deactivate",
        headers=auth_headers(1),
    )
    assert deactivate_response.status_code == 200

    response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {create_access_token(user['id'], 0)}"
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid token"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_create_user():
    username = f"user_{uuid4().hex[:8]}"

    response = client.post(
        "/users",
        json={
            "username": username,
            "password": "secret123",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["username"] == username
    assert data["is_active"] is True
    assert isinstance(data["id"], int)
    assert "password" not in data
    assert "password_hash" not in data

def test_create_duplicate_user_returns_400():
    username = f"user_{uuid4().hex[:8]}"

    first_response = client.post(
        "/users",
        json={"username": username, "password": "secret123"},
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/users",
        json={"username": username, "password": "secret123"},
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "username already exists"

def test_get_users():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post(
        "/users",
        json={"username": username, "password": "secret123"},
    )
    assert create_response.status_code == 200

    response = client.get("/users", headers=auth_headers(1))

    assert response.status_code == 200

    data = response.json()
    created_user = next(user for user in data if user["username"] == username)
    assert created_user["is_active"] is True

def test_get_user_by_id():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert create_response.status_code == 200
    created_user = create_response.json()

    response = client.get(f"/users/{created_user['id']}", headers=auth_headers(1))

    assert response.status_code == 200
    assert response.json()["id"] == created_user["id"]
    assert response.json()["username"] == username
    assert response.json()["is_active"] is True


def test_get_missing_user_returns_404():
    response = client.get("/users/999999", headers=auth_headers(1))

    assert response.status_code == 404
    assert response.json()["detail"] == "user not found"

def test_create_user_blank_username_returns_422():
    response = client.post(
        "/users",
        json={"username": "   ", "password": "secret123"},
    )

    assert response.status_code == 422

def test_deactivate_user():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert create_response.status_code == 200
    created_user = create_response.json()

    response = client.patch(
        f"/users/{created_user['id']}/deactivate",
        headers=auth_headers(1),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_user["id"]
    assert response.json()["is_active"] is False


def test_deactivate_missing_user_returns_404():
    response = client.patch(
        "/users/999999/deactivate",
        headers=auth_headers(1),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "user not found"


def test_delete_user():
    username = f"user_{uuid4().hex[:8]}"

    user_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert user_response.status_code == 200
    user = user_response.json()

    delete_response = client.delete(
        f"/users/{user['id']}",
        headers=auth_headers(1),
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "delete success"

def test_delete_missing_user_returns_404():
    response = client.delete("/users/999999", headers=auth_headers(1))

    assert response.status_code == 404
    assert response.json()["detail"] == "user not found"

def test_update_user_username():
    username = f"user_{uuid4().hex[:8]}"
    new_username = f"user_{uuid4().hex[:8]}"

    create_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert create_response.status_code == 200
    created_user = create_response.json()

    response = client.patch(
        f"/users/{created_user['id']}",
        json={"username": new_username},
        headers=auth_headers(1),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_user["id"]
    assert response.json()["username"] == new_username
    assert response.json()["is_active"] is True


def test_update_user_is_active():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert create_response.status_code == 200
    created_user = create_response.json()

    response = client.patch(
        f"/users/{created_user['id']}",
        json={"is_active": False},
        headers=auth_headers(1),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_user["id"]
    assert response.json()["username"] == username
    assert response.json()["is_active"] is False

def test_update_user_empty_body_returns_400():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert create_response.status_code == 200
    created_user = create_response.json()

    response = client.patch(
        f"/users/{created_user['id']}",
        json={},
        headers=auth_headers(1),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "provide at least one field to update"


def test_update_missing_user_returns_404():
    response = client.patch(
        "/users/999999",
        json={"username": f"user_{uuid4().hex[:8]}"},
        headers=auth_headers(1),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "user not found"


def test_update_user_duplicate_username_returns_400():
    first_username = f"user_{uuid4().hex[:8]}"
    second_username = f"user_{uuid4().hex[:8]}"

    first_response = client.post("/users", json={"username": first_username, "password": "secret123"})
    assert first_response.status_code == 200

    second_response = client.post("/users", json={"username": second_username, "password": "secret123"})
    assert second_response.status_code == 200
    second_user = second_response.json()

    response = client.patch(
        f"/users/{second_user['id']}",
        json={"username": first_username},
        headers=auth_headers(1),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "username already exists"

def test_get_users_filter_by_is_active_false():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert create_response.status_code == 200
    created_user = create_response.json()

    update_response = client.patch(
        f"/users/{created_user['id']}",
        json={"is_active": False},
        headers=auth_headers(1),
    )
    assert update_response.status_code == 200

    response = client.get("/users", params={"is_active": "false"}, headers=auth_headers(1))

    assert response.status_code == 200

    data = response.json()
    usernames = [user["username"] for user in data]
    assert username in usernames
    assert all(user["is_active"] is False for user in data)

def test_get_users_filter_by_is_active_true():
    username = f"user_{uuid4().hex[:8]}"

    create_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert create_response.status_code == 200

    response = client.get("/users", params={"is_active": "true"}, headers=auth_headers(1))

    assert response.status_code == 200

    data = response.json()
    usernames = [user["username"] for user in data]
    assert username in usernames
    assert all(user["is_active"] is True for user in data)

def test_get_user_detail():
    user_response = client.post(
        "/users",
        json={"username": f"user_{uuid4().hex[:8]}", "password": "secret123"},
    )
    assert user_response.status_code == 200
    user = user_response.json()

    response = client.get(f"/users/{user['id']}/detail", headers=auth_headers(1))

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == user["id"]
    assert data["username"] == user["username"]

def test_get_missing_user_detail_returns_404():
    response = client.get("/users/999999/detail", headers=auth_headers(1))

    assert response.status_code == 404
    assert response.json()["detail"] == "user not found"


def test_user_directory_requires_an_admin_account():
    anonymous_response = client.get("/users")
    assert anonymous_response.status_code == 401

    user_response = client.post(
        "/users",
        json={"username": f"user_{uuid4().hex[:8]}", "password": "secret123"},
    )
    user = user_response.json()

    response = client.get("/users", headers=auth_headers(user["id"]))
    assert response.status_code == 403
    assert response.json()["detail"] == "admin permission required"


def test_user_detail_requires_an_admin_account():
    response = client.get("/users/1")
    assert response.status_code == 401

def test_duplicate_user_returns_400_without_duplicate_side_effects():
    username = f"user_{uuid4().hex[:8]}"

    first_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert first_response.status_code == 200
    second_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert second_response.status_code == 400

def test_create_user_requires_password():
    response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
        },
    )

    assert response.status_code == 422

def test_admin_can_update_user_role():
    user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    user = user_response.json()

    response = client.patch(
        f"/users/{user['id']}/role",
        json={"role": "admin"},
        headers=auth_headers(1),
    )

    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert response.json()["role"] == "admin"

def test_regular_user_cannot_update_user_role():
    target_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    actor_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    target_user = target_response.json()
    actor_user = actor_response.json()

    response = client.patch(
        f"/users/{target_user['id']}/role",
        json={"role": "admin"},
        headers=auth_headers(actor_user["id"]),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "admin permission required"

def test_role_change_invalidates_old_token():
    user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    user = user_response.json()
    old_token = create_access_token(user["id"], 0)

    update_response = client.patch(
        f"/users/{user['id']}/role",
        json={"role": "admin"},
        headers=auth_headers(1),
    )
    assert update_response.status_code == 200

    me_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {old_token}"},
    )

    assert me_response.status_code == 401
    
    login_response = client.post(
        "/auth/login",
        json={
            "username": user["username"],
            "password": "secret123",
        },
    )
    assert login_response.status_code == 200

    new_token = login_response.json()["access_token"]

    admin_response = client.get(
        "/users/admin/ping",
        headers={"Authorization": f"Bearer {new_token}"},
    )

    assert admin_response.status_code == 200
    assert admin_response.json()["username"] == user["username"]

def test_regular_user_cannot_delete_user():
    target_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    actor_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    target_user = target_response.json()
    actor_user = actor_response.json()

    response = client.delete(
        f"/users/{target_user['id']}",
        headers=auth_headers(actor_user["id"]),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "admin permission required"

def test_user_can_update_own_profile():
    username = f"user_{uuid4().hex[:8]}"
    new_username = f"user_{uuid4().hex[:8]}"

    create_response = client.post(
        "/users",
        json={
            "username": username,
            "password": "secret123",
        },
    )
    user = create_response.json()

    response = client.patch(
        "/users/me",
        json={
            "username": new_username,
            "email": "me@example.com",
        },
        headers=auth_headers(user["id"]),
    )

    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert response.json()["username"] == new_username
    assert response.json()["email"] == "me@example.com"
    assert response.json()["role"] == "user"

def test_user_cannot_change_own_role_or_active_status():
    response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    user = response.json()

    update_response = client.patch(
        "/users/me",
        json={
            "role": "admin",
            "is_active": False,
        },
        headers=auth_headers(user["id"]),
    )

    assert update_response.status_code == 422

def test_create_user_rejects_client_role():
    response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
            "role": "admin",
        },
    )

    assert response.status_code == 422

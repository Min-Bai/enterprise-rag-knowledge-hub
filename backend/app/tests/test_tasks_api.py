from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.security import create_access_token


client = TestClient(app)
client.headers.update(
    {"Authorization": f"Bearer {create_access_token(1, 0)}"}
)


def auth_headers(user_id: int):
    return {"Authorization": f"Bearer {create_access_token(user_id, 0)}"}


def test_create_task():
    title = f"test task {uuid4()}"

    response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["title"] == title
    assert data["done"] is False
    assert isinstance(data["id"], int)


def test_create_task_with_due_date():
    title = f"due task {uuid4().hex[:8]}"

    response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
            "due_date": "2026-08-01",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["title"] == title
    assert data["due_date"] == "2026-08-01"


def test_get_task_by_id():
    title = f"test task {uuid4()}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
    )
    created_task = create_response.json()

    response = client.get(f"/tasks/{created_task['id']}")

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == created_task["id"]
    assert data["title"] == title
    assert data["done"] is False


def test_patch_task_done_false():
    title = f"test task {uuid4()}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": True,
        },
    )
    created_task = create_response.json()

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"done": False},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == created_task["id"]
    assert data["title"] == title
    assert data["done"] is False
    assert data["updated_at"] >= created_task["updated_at"]


def test_patch_task_updates_updated_at():
    title = f"updated at {uuid4().hex[:8]}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
    )
    assert create_response.status_code == 200
    created_task = create_response.json()

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"done": True},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["done"] is True
    assert data["updated_at"] >= created_task["updated_at"]


def test_patch_task_due_date():
    title = f"due update {uuid4().hex[:8]}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
    )
    assert create_response.status_code == 200
    created_task = create_response.json()

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"due_date": "2026-09-01"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == created_task["id"]
    assert data["due_date"] == "2026-09-01"


def test_archive_task():
    title = f"archive {uuid4().hex[:8]}"

    create_response = client.post("/tasks", json={"title": title})
    assert create_response.status_code == 200
    task = create_response.json()
    assert task["archived"] is False

    response = client.patch(f"/tasks/{task['id']}/archive")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task["id"]
    assert data["archived"] is True
    assert data["updated_at"] >= task["updated_at"]


def test_unarchive_task():
    title = f"unarchive {uuid4().hex[:8]}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "archived": True,
        },
    )
    assert create_response.status_code == 200
    task = create_response.json()
    assert task["archived"] is True

    response = client.patch(f"/tasks/{task['id']}/unarchive")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task["id"]
    assert data["archived"] is False


def test_archive_missing_task_returns_404():
    response = client.patch("/tasks/999999/archive")

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


def test_list_tasks_default_hides_archived_tasks():
    keyword = f"archive-filter-{uuid4().hex[:8]}"
    visible_title = f"{keyword} visible"
    archived_title = f"{keyword} archived"

    visible_response = client.post(
        "/tasks",
        json={"title": visible_title},
    )
    archived_response = client.post(
        "/tasks",
        json={"title": archived_title},
    )
    assert visible_response.status_code == 200
    assert archived_response.status_code == 200
    archived_task = archived_response.json()

    archive_response = client.patch(f"/tasks/{archived_task['id']}/archive")
    assert archive_response.status_code == 200

    response = client.get("/tasks", params={"keyword": keyword})
    assert response.status_code == 200

    data = response.json()
    titles = [task["title"] for task in data["items"]]
    assert visible_title in titles
    assert archived_title not in titles


def test_list_tasks_can_filter_archived_true():
    title = f"archived filter {uuid4().hex[:8]}"

    create_response = client.post("/tasks", json={"title": title})
    assert create_response.status_code == 200
    task = create_response.json()

    archive_response = client.patch(f"/tasks/{task['id']}/archive")
    assert archive_response.status_code == 200

    response = client.get("/tasks", params={"archived": "true"})
    assert response.status_code == 200

    data = response.json()
    titles = [task["title"] for task in data["items"]]
    assert title in titles
    assert all(task["archived"] is True for task in data["items"])


def test_patch_task_due_date_null_clears_due_date():
    title = f"due clear {uuid4().hex[:8]}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "due_date": "2026-09-01",
        },
    )
    assert create_response.status_code == 200
    created_task = create_response.json()

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"due_date": None},
    )

    assert response.status_code == 200
    assert response.json()["due_date"] is None


def test_patch_task_empty_body_returns_400():
    title = f"test task {uuid4()}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
    )
    created_task = create_response.json()

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "provide at least one field to update"


def test_get_my_tasks_requires_token():
    response = TestClient(app).get("/tasks/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing token"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_get_my_tasks_returns_current_user_tasks():
    first_username = f"user_{uuid4().hex[:8]}"
    second_username = f"user_{uuid4().hex[:8]}"

    first_user_response = client.post("/users", json={"username": first_username, "password": "secret123"})
    second_user_response = client.post("/users", json={"username": second_username, "password": "secret123"})
    assert first_user_response.status_code == 200
    assert second_user_response.status_code == 200
    first_user = first_user_response.json()
    second_user = second_user_response.json()

    first_title = f"my task {uuid4().hex[:8]}"
    second_title = f"other task {uuid4().hex[:8]}"

    first_task_response = client.post(
        "/tasks",
        json={"title": first_title},
        headers=auth_headers(first_user["id"]),
    )
    second_task_response = client.post(
        "/tasks",
        json={"title": second_title},
        headers=auth_headers(second_user["id"]),
    )
    assert first_task_response.status_code == 200
    assert second_task_response.status_code == 200

    response = client.get(
        "/tasks/me",
        headers={
            "Authorization": f"Bearer {create_access_token(first_user['id'], 0)}"
        },
    )

    assert response.status_code == 200

    data = response.json()
    titles = [task["title"] for task in data["items"]]
    assert first_title in titles
    assert second_title not in titles
    assert all(task["user_id"] == first_user["id"] for task in data["items"])


def test_get_my_tasks_supports_filters_and_sort():
    first_username = f"user_{uuid4().hex[:8]}"
    second_username = f"user_{uuid4().hex[:8]}"

    first_user_response = client.post("/users", json={"username": first_username, "password": "secret123"})
    second_user_response = client.post("/users", json={"username": second_username, "password": "secret123"})
    assert first_user_response.status_code == 200
    assert second_user_response.status_code == 200
    first_user = first_user_response.json()
    second_user = second_user_response.json()

    keyword = f"mine-{uuid4().hex[:8]}"
    high_title = f"{keyword} high"
    low_title = f"{keyword} low"
    done_title = f"{keyword} done"
    other_title = f"{keyword} other"

    high_response = client.post(
        "/tasks",
        json={
            "title": high_title,
            "done": False,
            "priority": 5,
        },
        headers=auth_headers(first_user["id"]),
    )
    low_response = client.post(
        "/tasks",
        json={
            "title": low_title,
            "done": False,
            "priority": 1,
        },
        headers=auth_headers(first_user["id"]),
    )
    done_response = client.post(
        "/tasks",
        json={
            "title": done_title,
            "done": True,
            "priority": 4,
        },
        headers=auth_headers(first_user["id"]),
    )
    other_response = client.post(
        "/tasks",
        json={
            "title": other_title,
            "done": False,
            "priority": 4,
        },
        headers=auth_headers(second_user["id"]),
    )
    assert high_response.status_code == 200
    assert low_response.status_code == 200
    assert done_response.status_code == 200
    assert other_response.status_code == 200

    response = client.get(
        "/tasks/me",
        params={
            "keyword": keyword,
            "done": "false",
            "sort": "priority_desc",
        },
        headers={
            "Authorization": f"Bearer {create_access_token(first_user['id'], 0)}"
        },
    )

    assert response.status_code == 200

    data = response.json()
    titles = [task["title"] for task in data["items"]]
    assert titles == [high_title, low_title]
    assert all(task["user_id"] == first_user["id"] for task in data["items"])
    assert all(task["done"] is False for task in data["items"])


def test_list_tasks_filter_by_keyword_and_done_false():
    keyword = f"filter-{uuid4()}"
    undone_title = f"{keyword} undone"
    done_title = f"{keyword} done"

    client.post(
        "/tasks",
        json={
            "title": undone_title,
            "done": False,
        },
    )
    client.post(
        "/tasks",
        json={
            "title": done_title,
            "done": True,
        },
    )

    response = client.get(
        "/tasks",
        params={
            "keyword": keyword,
            "done": "false",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["count"] == 1
    assert data["items"][0]["title"] == undone_title
    assert data["items"][0]["done"] is False


def test_list_tasks_sort_id_desc():
    keyword = f"sort-{uuid4()}"

    first_response = client.post(
        "/tasks",
        json={
            "title": f"{keyword} first",
            "done": False,
        },
    )
    second_response = client.post(
        "/tasks",
        json={
            "title": f"{keyword} second",
            "done": False,
        },
    )
    first_task = first_response.json()
    second_task = second_response.json()

    response = client.get(
        "/tasks",
        params={
            "keyword": keyword,
            "sort": "id_desc",
        },
    )

    assert response.status_code == 200

    data = response.json()
    ids = [task["id"] for task in data["items"]]
    assert ids == [second_task["id"], first_task["id"]]


def test_list_tasks_sort_priority_desc():
    keyword = f"priority-{uuid4().hex[:8]}"

    low_response = client.post(
        "/tasks",
        json={
            "title": f"{keyword} low",
            "priority": 1,
        },
    )
    high_response = client.post(
        "/tasks",
        json={
            "title": f"{keyword} high",
            "priority": 5,
        },
    )
    middle_response = client.post(
        "/tasks",
        json={
            "title": f"{keyword} middle",
            "priority": 3,
        },
    )
    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert middle_response.status_code == 200

    low_task = low_response.json()
    high_task = high_response.json()
    middle_task = middle_response.json()

    response = client.get(
        "/tasks",
        params={
            "keyword": keyword,
            "sort": "priority_desc",
        },
    )

    assert response.status_code == 200

    data = response.json()
    ids = [task["id"] for task in data["items"]]
    assert ids == [high_task["id"], middle_task["id"], low_task["id"]]


def test_list_tasks_limit_offset():
    keyword = f"page-{uuid4()}"
    created_tasks = []

    for index in range(4):
        response = client.post(
            "/tasks",
            json={
                "title": f"{keyword} task {index}",
                "done": False,
            },
        )
        assert response.status_code == 200
        created_tasks.append(response.json())

    response = client.get(
        "/tasks",
        params={
            "keyword": keyword,
            "sort": "id_asc",
            "limit": 2,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    data = response.json()
    ids = [task["id"] for task in data["items"]]

    assert ids == [created_tasks[1]["id"], created_tasks[2]["id"]]
    assert data["total"] == 4
    assert data["count"] == 2
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert data["has_more"] is True
    assert data["next_offset"] == 3


def test_list_tasks_page_page_size():
    keyword = f"ps-{uuid4().hex[:8]}"
    created_tasks = []

    for index in range(5):
        response = client.post(
            "/tasks",
            json={
                "title": f"{keyword} task {index}",
                "done": False,
            },
        )
        assert response.status_code == 200
        created_tasks.append(response.json())

    response = client.get(
        "/tasks",
        params={
            "keyword": keyword,
            "sort": "id_asc",
            "page": 2,
            "page_size": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()
    ids = [task["id"] for task in data["items"]]

    assert ids == [created_tasks[2]["id"], created_tasks[3]["id"]]
    assert data["total"] == 5
    assert data["count"] == 2
    assert data["limit"] == 2
    assert data["offset"] == 2
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert data["total_pages"] == 3
    assert data["next_page"] == 3


def test_get_task_id_zero_returns_422():
    response = client.get("/tasks/0")

    assert response.status_code == 422


def test_get_missing_task_returns_404():
    response = client.get("/tasks/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


def test_create_duplicate_title_returns_400():
    title = f"duplicate {uuid4()}"

    first_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
    )
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "title already exists"


def test_delete_task():
    title = f"delete {uuid4()}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
    )
    assert create_response.status_code == 200
    created_task = create_response.json()

    delete_response = client.delete(f"/tasks/{created_task['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "delete success"

    get_response = client.get(f"/tasks/{created_task['id']}")

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "task not found"

def test_get_task_count():
    title = f"count {uuid4()}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
    )
    assert create_response.status_code == 200

    response = client.get("/tasks/count")

    assert response.status_code == 200

    data = response.json()
    assert data["count"] >= 1

def test_get_done_task_count():
    title = f"done count {uuid4()}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": True,
        },
    )
    assert create_response.status_code == 200

    response = client.get("/tasks/count", params={"done": "true"})

    assert response.status_code == 200

    data = response.json()
    assert data["count"] >= 1

def test_get_undone_task_count():
    title = f"undone count {uuid4()}"

    create_response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
    )
    assert create_response.status_code == 200

    response = client.get("/tasks/count", params={"done": "false"})

    assert response.status_code == 200

    data = response.json()
    assert data["count"] >= 1


def test_task_count_default_excludes_archived_tasks():
    visible_title = f"count visible {uuid4().hex[:8]}"
    archived_title = f"count archived {uuid4().hex[:8]}"

    visible_response = client.post("/tasks", json={"title": visible_title})
    archived_response = client.post("/tasks", json={"title": archived_title})
    assert visible_response.status_code == 200
    assert archived_response.status_code == 200

    archived_task = archived_response.json()
    archive_response = client.patch(f"/tasks/{archived_task['id']}/archive")
    assert archive_response.status_code == 200

    list_response = client.get("/tasks")
    count_response = client.get("/tasks/count")
    assert list_response.status_code == 200
    assert count_response.status_code == 200

    assert count_response.json()["count"] == list_response.json()["total"]


def test_task_count_can_filter_archived_true():
    title = f"count archived true {uuid4().hex[:8]}"

    create_response = client.post("/tasks", json={"title": title})
    assert create_response.status_code == 200
    task = create_response.json()

    archive_response = client.patch(f"/tasks/{task['id']}/archive")
    assert archive_response.status_code == 200

    response = client.get("/tasks/count", params={"archived": "true"})

    assert response.status_code == 200
    assert response.json()["count"] >= 1

def test_create_task_assigns_current_user():
    username = f"user_{uuid4().hex[:8]}"

    user_response = client.post("/users", json={"username": username, "password": "secret123"})
    assert user_response.status_code == 200
    user = user_response.json()

    title = f"task user {uuid4().hex[:8]}"

    response = client.post(
        "/tasks",
        json={
            "title": title,
            "done": False,
        },
        headers=auth_headers(user["id"]),
    )

    assert response.status_code == 200

    data = response.json()
    assert data["title"] == title
    assert data["done"] is False
    assert data["user_id"] == user["id"]

def test_create_task_requires_token():
    response = TestClient(app).post(
        "/tasks",
        json={"title": f"task {uuid4().hex[:8]}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "missing token"

def test_list_tasks_filter_by_user_id():
    first_user_response = client.post(
        "/users",
        json={"username": f"user_{uuid4().hex[:8]}", "password": "secret123"},
    )
    assert first_user_response.status_code == 200
    first_user = first_user_response.json()

    second_user_response = client.post(
        "/users",
        json={"username": f"user_{uuid4().hex[:8]}", "password": "secret123"},
    )
    assert second_user_response.status_code == 200
    second_user = second_user_response.json()

    first_title = f"user task {uuid4().hex[:8]}"
    second_title = f"user task {uuid4().hex[:8]}"

    first_task_response = client.post(
        "/tasks",
        json={
            "title": first_title,
            "done": False,
        },
        headers=auth_headers(first_user["id"]),
    )
    assert first_task_response.status_code == 200

    second_task_response = client.post(
        "/tasks",
        json={
            "title": second_title,
            "done": False,
        },
        headers=auth_headers(second_user["id"]),
    )
    assert second_task_response.status_code == 200

    response = client.get("/tasks", params={"user_id": first_user["id"]})

    assert response.status_code == 200

    data = response.json()
    titles = [task["title"] for task in data["items"]]

    assert first_title in titles
    assert second_title not in titles
    assert all(task["user_id"] == first_user["id"] for task in data["items"])

def test_list_tasks_filter_by_user_id_and_done_false():
    user_response = client.post(
        "/users",
        json={"username": f"user_{uuid4().hex[:8]}", "password": "secret123"},
    )
    assert user_response.status_code == 200
    user = user_response.json()

    undone_title = f"user undone {uuid4().hex[:8]}"
    done_title = f"user done {uuid4().hex[:8]}"

    undone_response = client.post(
        "/tasks",
        json={
            "title": undone_title,
            "done": False,
        },
        headers=auth_headers(user["id"]),
    )
    assert undone_response.status_code == 200

    done_response = client.post(
        "/tasks",
        json={
            "title": done_title,
            "done": True,
        },
        headers=auth_headers(user["id"]),
    )
    assert done_response.status_code == 200

    response = client.get(
        "/tasks",
        params={
            "user_id": user["id"],
            "done": "false",
        },
    )

    assert response.status_code == 200

    data = response.json()
    titles = [task["title"] for task in data["items"]]

    assert undone_title in titles
    assert done_title not in titles
    assert all(task["user_id"] == user["id"] for task in data["items"])
    assert all(task["done"] is False for task in data["items"])

def test_patch_task_title_null_returns_422():
    title = f"null title {uuid4().hex[:8]}"

    create_response = client.post("/tasks", json={"title": title})
    assert create_response.status_code == 200
    task = create_response.json()

    response = client.patch(
        f"/tasks/{task['id']}",
        json={"title": None},
    )

    assert response.status_code == 422


def test_patch_task_done_null_returns_422():
    title = f"null done {uuid4().hex[:8]}"

    create_response = client.post("/tasks", json={"title": title})
    assert create_response.status_code == 200
    task = create_response.json()

    response = client.patch(
        f"/tasks/{task['id']}",
        json={"done": None},
    )

    assert response.status_code == 422


def test_patch_task_priority_null_returns_422():
    title = f"null priority {uuid4().hex[:8]}"

    create_response = client.post("/tasks", json={"title": title})
    assert create_response.status_code == 200
    task = create_response.json()

    response = client.patch(
        f"/tasks/{task['id']}",
        json={"priority": None},
    )

    assert response.status_code == 422

def test_regular_user_cannot_update_another_users_task():
    first_user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    second_user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    first_user = first_user_response.json()
    second_user = second_user_response.json()

    original_title = f"owned task {uuid4().hex[:8]}"
    task_response = client.post(
        "/tasks",
        json={"title": original_title},
        headers=auth_headers(first_user["id"]),
    )
    task_id = task_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"title": "hacked title"},
        headers=auth_headers(second_user["id"]),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "task permission denied"

    task_response = client.get(f"/tasks/{task_id}")

    assert task_response.status_code == 200
    assert task_response.json()["title"] == original_title

def test_admin_can_update_another_users_task():
    user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    user = user_response.json()

    task_response = client.post(
        "/tasks",
        json={"title": f"user task {uuid4().hex[:8]}"},
        headers=auth_headers(user["id"]),
    )
    task_id = task_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"title": "updated by admin"},
        headers=auth_headers(1),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "updated by admin"

def test_regular_user_cannot_list_another_users_tasks():
    first_user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    second_user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    first_user = first_user_response.json()
    second_user = second_user_response.json()

    first_title = f"first task {uuid4().hex[:8]}"
    second_title = f"second task {uuid4().hex[:8]}"

    client.post(
        "/tasks",
        json={"title": first_title},
        headers=auth_headers(first_user["id"]),
    )
    client.post(
        "/tasks",
        json={"title": second_title},
        headers=auth_headers(second_user["id"]),
    )

    response = client.get(
        "/tasks",
        params={"user_id": second_user["id"]},
        headers=auth_headers(first_user["id"]),
    )

    assert response.status_code == 200
    titles = [task["title"] for task in response.json()["items"]]
    assert first_title in titles
    assert second_title not in titles

def test_regular_user_cannot_get_another_users_task():
    first_user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    second_user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    first_user = first_user_response.json()
    second_user = second_user_response.json()

    task_response = client.post(
        "/tasks",
        json={"title": f"private task {uuid4().hex[:8]}"},
        headers=auth_headers(first_user["id"]),
    )
    task_id = task_response.json()["id"]

    response = client.get(
        f"/tasks/{task_id}",
        headers=auth_headers(second_user["id"]),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "task permission denied"

def test_regular_user_task_count_only_counts_own_tasks():
    first_user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    second_user_response = client.post(
        "/users",
        json={
            "username": f"user_{uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    first_user = first_user_response.json()
    second_user = second_user_response.json()

    client.post(
        "/tasks",
        json={"title": f"first task {uuid4().hex[:8]}"},
        headers=auth_headers(first_user["id"]),
    )
    client.post(
        "/tasks",
        json={"title": f"second task {uuid4().hex[:8]}"},
        headers=auth_headers(second_user["id"]),
    )

    response = client.get(
        "/tasks/count",
        headers=auth_headers(first_user["id"]),
    )

    assert response.status_code == 200
    assert response.json()["count"] == 2

def test_create_task_rejects_client_user_id():
    response = client.post(
        "/tasks",
        json={
            "title": f"task {uuid4().hex[:8]}",
            "user_id": 999,
        },
    )

    assert response.status_code == 422

def test_update_task_rejects_client_user_id():
    create_response = client.post(
        "/tasks",
        json={"title": f"task {uuid4().hex[:8]}"},
    )
    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"user_id": 999},
    )

    assert response.status_code == 422
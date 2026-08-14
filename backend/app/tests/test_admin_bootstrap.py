from unittest.mock import Mock

from backend.app.schemas.user import UserCreate
from backend.app.services.users import create_admin_user_service


def test_create_admin_user_assigns_the_admin_role_and_a_default_knowledge_base(monkeypatch):
    db = Mock()
    monkeypatch.setattr(
        "backend.app.services.users.get_default_knowledge_base_service",
        Mock(),
    )

    admin = create_admin_user_service(
        UserCreate(username="first_admin", password="secret123"),
        db,
    )

    assert admin.role == "admin"
    assert admin.username == "first_admin"
    db.add.assert_called_once_with(admin)
    db.flush.assert_called_once()
    db.commit.assert_called_once()

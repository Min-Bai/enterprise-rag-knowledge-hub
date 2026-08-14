from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.services.knowledge_base_members import (
    KnowledgeBaseAccessDeniedError,
    get_knowledge_base_role,
    require_knowledge_base_role,
)
from backend.app.services.knowledge_bases import get_knowledge_bases_service


def test_owner_has_owner_role_without_membership_lookup():
    knowledge_base = SimpleNamespace(id=3, owner_user_id=1)
    db = Mock()

    assert get_knowledge_base_role(knowledge_base=knowledge_base, user_id=1, db=db) == "owner"
    db.scalar.assert_not_called()


def test_member_role_is_read_from_membership():
    knowledge_base = SimpleNamespace(id=3, owner_user_id=1)
    db = Mock()
    db.scalar.return_value = "viewer"

    assert get_knowledge_base_role(knowledge_base=knowledge_base, user_id=2, db=db) == "viewer"


def test_viewer_cannot_write_documents():
    knowledge_base = SimpleNamespace(id=3, owner_user_id=1)
    db = Mock()
    db.scalar.return_value = "viewer"

    with pytest.raises(KnowledgeBaseAccessDeniedError):
        require_knowledge_base_role(
            knowledge_base=knowledge_base,
            user_id=2,
            db=db,
            allowed_roles={"owner", "editor"},
        )


def test_knowledge_base_list_includes_the_shared_member_role():
    knowledge_base = SimpleNamespace(
        id=3,
        name="Engineering",
        description=None,
        created_at="2026-08-14T00:00:00Z",
        owner_user_id=1,
    )
    db = Mock()
    db.execute.return_value.all.return_value = [(knowledge_base, "viewer")]

    result = get_knowledge_bases_service(db=db, owner_user_id=2)

    assert result == [
        {
            "id": 3,
            "name": "Engineering",
            "description": None,
            "created_at": "2026-08-14T00:00:00Z",
            "role": "viewer",
        }
    ]

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.services.knowledge_base_members import (
    KnowledgeBaseAccessDeniedError,
    get_knowledge_base_role,
    require_knowledge_base_role,
)


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

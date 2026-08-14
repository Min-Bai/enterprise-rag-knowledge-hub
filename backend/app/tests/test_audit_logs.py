from types import SimpleNamespace
from unittest.mock import Mock

from backend.app.services.audit_logs import write_audit_log
from backend.app.services.audit_logs import get_knowledge_base_audit_logs


def test_write_audit_log_persists_structured_event():
    db = Mock()

    write_audit_log(
        actor_user_id=1,
        action="document.uploaded",
        target_type="document",
        target_id=8,
        knowledge_base_id=3,
        details={"filename": "handbook.pdf"},
        db=db,
    )

    event = db.add.call_args.args[0]
    assert event.actor_user_id == 1
    assert event.action == "document.uploaded"
    assert event.details == {"filename": "handbook.pdf"}
    db.commit.assert_called_once()


def test_write_audit_log_can_join_an_existing_transaction():
    db = Mock()

    write_audit_log(
        actor_user_id=1,
        action="rag.retrieval_completed",
        target_type="document",
        target_id=8,
        knowledge_base_id=3,
        details={"hit_count": 0},
        db=db,
        commit=False,
    )

    db.add.assert_called_once()
    db.commit.assert_not_called()


def test_get_audit_logs_includes_actor_username():
    event = SimpleNamespace(
        id=4,
        actor_user_id=1,
        action="document.uploaded",
        target_type="document",
        target_id=8,
        details={"filename": "handbook.pdf"},
        created_at="2026-08-13T10:00:00Z",
    )
    db = Mock()
    db.execute.return_value.all.return_value = [(event, "alice")]

    result = get_knowledge_base_audit_logs(knowledge_base_id=3, db=db)

    assert result == [{
        "id": 4,
        "actor_user_id": 1,
        "actor_username": "alice",
        "action": "document.uploaded",
        "target_type": "document",
        "target_id": 8,
        "details": {"filename": "handbook.pdf"},
        "created_at": "2026-08-13T10:00:00Z",
    }]

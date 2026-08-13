from types import SimpleNamespace
from unittest.mock import Mock

from backend.app.services.audit_logs import write_audit_log


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

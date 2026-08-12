from unittest.mock import Mock

import pytest

from backend.app.services import document_processor


def test_mark_interrupted_documents_failed_updates_and_commits(monkeypatch):
    db = Mock()
    result = Mock()
    result.rowcount = 2
    db.execute.return_value = result

    monkeypatch.setattr(document_processor, "SessionLocal", lambda: db)

    recovered = document_processor.mark_interrupted_documents_failed()

    assert recovered == 2
    db.execute.assert_called_once()
    db.commit.assert_called_once()
    db.rollback.assert_not_called()
    db.close.assert_called_once()


def test_mark_interrupted_documents_failed_rolls_back_on_error(monkeypatch):
    db = Mock()
    db.execute.side_effect = RuntimeError("database error")

    monkeypatch.setattr(document_processor, "SessionLocal", lambda: db)

    with pytest.raises(RuntimeError, match="database error"):
        document_processor.mark_interrupted_documents_failed()

    db.rollback.assert_called_once()
    db.close.assert_called_once()

def test_process_document_skips_deleted_document(monkeypatch):
    db = Mock()
    db.get.return_value = None

    monkeypatch.setattr(document_processor, "SessionLocal", lambda: db)

    document_processor.process_document(123)

    db.get.assert_called_once()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
    db.close.assert_called_once()
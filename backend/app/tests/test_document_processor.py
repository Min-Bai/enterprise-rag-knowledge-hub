from types import SimpleNamespace
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


def test_process_document_records_chunk_count_and_completion_time(monkeypatch):
    document = SimpleNamespace(
        id=8,
        user_id=1,
        knowledge_base_id=3,
        tags=["HR"],
        status="uploaded",
        error_message="old",
        chunk_count=0,
        processed_at=None,
        storage_path="/tmp/handbook.pdf",
    )
    db = Mock()
    db.get.return_value = document
    chunks = [object(), object(), object()]
    index_chunks = Mock()
    monkeypatch.setattr(document_processor, "SessionLocal", lambda: db)
    monkeypatch.setattr(document_processor, "split_pdf_into_chunks", Mock(return_value=chunks))
    monkeypatch.setattr(document_processor, "index_document_chunks", index_chunks)

    document_processor.process_document(8)

    assert document.status == "ready"
    assert document.error_message is None
    assert document.chunk_count == 3
    assert document.processed_at is not None
    index_chunks.assert_called_once_with(document_id=8, user_id=1, knowledge_base_id=3, tags=["HR"], chunks=chunks)
    assert db.commit.call_count == 2

from pathlib import Path
from unittest.mock import Mock

from scripts import requeue_uploaded_documents


def test_get_uploaded_document_ids_returns_uploaded_documents(monkeypatch):
    db = Mock()
    db.scalars.return_value.all.return_value = [3, 8]
    monkeypatch.setattr(requeue_uploaded_documents, "SessionLocal", lambda: db)

    assert requeue_uploaded_documents.get_uploaded_document_ids() == [3, 8]
    db.close.assert_called_once()


def test_requeue_script_requires_execute_flag(monkeypatch, capsys):
    monkeypatch.setattr(requeue_uploaded_documents, "get_uploaded_document_ids", lambda: [3, 8])
    monkeypatch.setattr(requeue_uploaded_documents, "enqueue_document_processing", Mock())
    monkeypatch.setattr("sys.argv", [str(Path(__file__).resolve())])

    requeue_uploaded_documents.main()

    requeue_uploaded_documents.enqueue_document_processing.assert_not_called()
    assert "当前仅预览" in capsys.readouterr().out


def test_requeue_script_enqueues_uploaded_documents(monkeypatch):
    enqueue = Mock()
    monkeypatch.setattr(requeue_uploaded_documents, "get_uploaded_document_ids", lambda: [3, 8])
    monkeypatch.setattr(requeue_uploaded_documents, "enqueue_document_processing", enqueue)
    monkeypatch.setattr("sys.argv", ["requeue_uploaded_documents.py", "--execute"])

    requeue_uploaded_documents.main()

    assert enqueue.call_args_list == [((3,), {}), ((8,), {})]

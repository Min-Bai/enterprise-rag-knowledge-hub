from unittest.mock import Mock

from python_practice.day57 import worker


def test_worker_marks_interrupted_documents_before_listening(monkeypatch, capsys):
    queue = Mock()
    worker_instance = Mock()
    worker_factory = Mock(return_value=worker_instance)
    recover = Mock(return_value=2)

    monkeypatch.setattr(worker, "mark_interrupted_documents_failed", recover)
    monkeypatch.setattr(worker, "get_document_queue", lambda: queue)
    monkeypatch.setattr(worker, "Worker", worker_factory)

    worker.main()

    recover.assert_called_once()
    worker_factory.assert_called_once_with(
        [queue],
        connection=queue.connection,
    )
    worker_instance.work.assert_called_once()
    assert "Marked 2 interrupted document(s) as failed" in capsys.readouterr().out
from unittest.mock import Mock

from backend.app import celery_app
from backend.app.tasks import document_processing


def test_document_processing_task_runs_document_processor(monkeypatch):
    process_document = Mock()
    monkeypatch.setattr(document_processing, "process_document", process_document)

    document_processing.process_document_task.run(42)

    process_document.assert_called_once_with(42)


def test_celery_document_processing_configuration():
    assert celery_app.DOCUMENT_QUEUE_NAME == "document-processing"
    assert celery_app.celery_app.conf.task_acks_late is True
    assert celery_app.celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.celery_app.conf.task_time_limit == 20 * 60
    assert celery_app.celery_app.conf.worker_prefetch_multiplier == 1


def test_celery_worker_recovery_marks_interrupted_documents(monkeypatch):
    recover = Mock(return_value=2)
    monkeypatch.setattr(
        "backend.app.services.document_processor.mark_interrupted_documents_failed",
        recover,
    )

    celery_app.recover_interrupted_documents()

    recover.assert_called_once()

from rq import Worker

from .services.document_queue import get_document_queue
from .services.document_processor import mark_interrupted_documents_failed


def main() -> None:
    recovered = mark_interrupted_documents_failed()

    if recovered:
        print(f"Marked {recovered} interrupted document(s) as failed")

    queue = get_document_queue()
    worker = Worker([queue], connection=queue.connection)
    worker.work()
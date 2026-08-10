from rq import Worker

from .services.document_queue import get_document_queue


def main() -> None:
    queue = get_document_queue()
    worker = Worker([queue], connection=queue.connection)
    worker.work()


if __name__ == "__main__":
    main()
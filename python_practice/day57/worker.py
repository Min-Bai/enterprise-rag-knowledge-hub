from rq import Worker

from .redis_client import redis_client
from .services.document_queue import DOCUMENT_QUEUE_NAME


def main() -> None:
    if redis_client is None:
        raise RuntimeError("REDIS_URL is required for document worker")

    worker = Worker([DOCUMENT_QUEUE_NAME], connection=redis_client)
    worker.work()


if __name__ == "__main__":
    main()
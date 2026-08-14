"""一次性将旧 RQ 队列遗留文档重新投递到 Celery。"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.models.document import DocumentORM
from backend.app.services.document_queue import enqueue_document_processing


def get_uploaded_document_ids() -> list[int]:
    db = SessionLocal()
    try:
        return list(
            db.scalars(
                select(DocumentORM.id)
                .where(DocumentORM.status == "uploaded")
                .order_by(DocumentORM.id),
            ).all(),
        )
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将旧 RQ 队列遗留的待处理文档重新投递到 Celery。",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际投递列出的文档；默认只预览",
    )
    args = parser.parse_args()

    document_ids = get_uploaded_document_ids()
    print(f"待处理文档数量：{len(document_ids)}")

    if not document_ids:
        return

    print("文档 ID：", ", ".join(map(str, document_ids)))
    if not args.execute:
        print("当前仅预览。停止旧 RQ Worker 后，请使用 --execute 实际投递。")
        return

    for document_id in document_ids:
        enqueue_document_processing(document_id)

    print(f"已向 Celery 投递 {len(document_ids)} 份文档")


if __name__ == "__main__":
    main()

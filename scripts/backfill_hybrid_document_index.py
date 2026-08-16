"""Safely requeue ready documents so they receive the lexical retrieval index."""

from __future__ import annotations

import argparse

from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.models.document import DocumentORM
from backend.app.services.document_queue import enqueue_document_processing


def get_ready_document_ids() -> list[int]:
    db = SessionLocal()
    try:
        return list(
            db.scalars(
                select(DocumentORM.id)
                .where(DocumentORM.status == "ready")
                .order_by(DocumentORM.id),
            ).all(),
        )
    finally:
        db.close()


def mark_documents_uploaded(document_ids: list[int]) -> None:
    if not document_ids:
        return
    db = SessionLocal()
    try:
        documents = list(db.scalars(select(DocumentORM).where(DocumentORM.id.in_(document_ids))).all())
        for document in documents:
            document.status = "uploaded"
            document.error_message = None
            document.chunk_count = 0
            document.processed_at = None
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将已就绪文档重新投递到 Celery，以建立混合检索的稀疏词项索引。",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际修改状态并投递任务；默认仅预览。",
    )
    args = parser.parse_args()
    document_ids = get_ready_document_ids()
    print(f"需要回填词项索引的文档数量：{len(document_ids)}")
    if not document_ids:
        return
    print("文档 ID：", ", ".join(map(str, document_ids)))
    if not args.execute:
        print("当前仅预览。确认 Worker 正常后，使用 --execute 开始回填。")
        return
    mark_documents_uploaded(document_ids)
    for document_id in document_ids:
        enqueue_document_processing(document_id)
    print(f"已将 {len(document_ids)} 份文档加入回填队列")


if __name__ == "__main__":
    main()

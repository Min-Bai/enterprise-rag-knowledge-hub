from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, func, select

from scripts import import_sqlite_to_mysql as importer
from python_practice.day57.database import Base


def test_import_sqlite_data_copies_records_once(monkeypatch, tmp_path):
    source_engine = create_engine(f"sqlite:///{tmp_path / 'source.db'}")
    target_engine = create_engine(f"sqlite:///{tmp_path / 'target.db'}")

    Base.metadata.create_all(source_engine)
    Base.metadata.create_all(target_engine)

    users = Base.metadata.tables["users"]
    tasks = Base.metadata.tables["tasks"]
    documents = Base.metadata.tables["documents"]
    knowledge_bases = Base.metadata.tables["knowledge_bases"]
    now = datetime.now(UTC)

    with source_engine.begin() as connection:
        connection.execute(
            users.insert(),
            [{
                "id": 1,
                "username": "alice",
                "email": "alice@example.com",
                "password_hash": "hash",
                "is_active": True,
                "role": "user",
                "token_version": 0,
            }],
        )
        connection.execute(
            tasks.insert(),
            [{
                "id": 1,
                "title": "Migrate data",
                "done": False,
                "archived": False,
                "user_id": 1,
                "priority": 1,
                "due_date": date(2026, 8, 11),
                "updated_at": now,
            }],
        )
        connection.execute(
            documents.insert(),
            [{
                "id": 1,
                "user_id": 1,
                "knowledge_base_id": 1,
                "filename": "resume.pdf",
                "storage_path": "/app/python_practice/data/resume.pdf",
                "status": "ready",
                "error_message": None,
                "created_at": now,
            }],
        )

    monkeypatch.setattr(importer, "mysql_engine", target_engine)

    counts = importer.import_sqlite_data(str(source_engine.url))

    assert counts == {
        "users": 1,
        "tasks": 1,
        "documents": 1,
    }

    with target_engine.connect() as connection:
        assert connection.scalar(
            select(func.count()).select_from(users)
        ) == 1
        assert connection.scalar(
            select(func.count()).select_from(tasks)
        ) == 1
        assert connection.scalar(
            select(func.count()).select_from(documents)
        ) == 1
        assert connection.scalar(
            select(func.count()).select_from(knowledge_bases)
        ) == 1

    with pytest.raises(RuntimeError, match="target MySQL database is not empty"):
        importer.import_sqlite_data(str(source_engine.url))

    source_engine.dispose()
    target_engine.dispose()


def test_import_sqlite_data_rejects_non_sqlite_source():
    with pytest.raises(ValueError, match="source database must use SQLite"):
        importer.import_sqlite_data(
            "mysql+pymysql://user:password@mysql:3306/todo_app"
        )

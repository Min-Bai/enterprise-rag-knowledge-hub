from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from python_practice.day57.database import Base, get_db
from python_practice.day57.main import app
from python_practice.day57.models.user import UserORM


TEST_DB_FILE = Path(__file__).resolve().parents[1] / "test_tasks.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(test_engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    db.add(
        UserORM(
            id=1,
            username="test_admin",
            password_hash="test-only-hash",
            role="admin",
        )
    )
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    TEST_DB_FILE.unlink(missing_ok=True)

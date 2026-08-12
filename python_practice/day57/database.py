from pathlib import Path
from .config import DATABASE_URL, SQL_ECHO

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DB_FILE = Path(__file__).parent / "tasks.db"
database_url = DATABASE_URL or f"sqlite:///{DB_FILE}"

engine_options = {"echo": SQL_ECHO}

is_sqlite = database_url.startswith("sqlite")

if is_sqlite:
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    database_url,
    **engine_options,
)


if is_sqlite:
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

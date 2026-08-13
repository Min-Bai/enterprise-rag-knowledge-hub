from argparse import ArgumentParser

from sqlalchemy import MetaData, create_engine, func, select

from backend.app.database import Base, engine as mysql_engine
from backend.app.legacy_task_table import legacy_tasks
from backend.app.models.document import DocumentORM
from backend.app.models.knowledge_base import KnowledgeBaseORM
from backend.app.models.user import UserORM


DEFAULT_SOURCE_URL = "sqlite:////app/data/tasks.db"
TABLE_NAMES = ("users", "tasks", "documents")
def parse_args():
    parser = ArgumentParser(
        description="Copy application data from SQLite to MySQL.",
    )
    parser.add_argument(
        "--source-url",
        default=DEFAULT_SOURCE_URL,
        help="SQLAlchemy URL of the source SQLite database.",
    )
    return parser.parse_args()


def load_source_tables(source_engine):
    source_metadata = MetaData()
    source_metadata.reflect(
        bind=source_engine,
        only=list(TABLE_NAMES),
    )

    missing_tables = [
        table_name
        for table_name in TABLE_NAMES
        if table_name not in source_metadata.tables
    ]
    if missing_tables:
        raise RuntimeError(
            f"source database is missing tables: {', '.join(missing_tables)}"
        )

    return source_metadata.tables


def ensure_mysql_is_empty():
    with mysql_engine.connect() as connection:
        nonempty_tables = [
            table_name
            for table_name in TABLE_NAMES
            if connection.scalar(
                select(func.count()).select_from(target_table(table_name))
            )
        ]

    if nonempty_tables:
        raise RuntimeError(
            "target MySQL database is not empty: "
            f"{', '.join(nonempty_tables)}"
        )


def copy_table(
    source_connection,
    target_connection,
    source_tables,
    table_name: str,
) -> int:
    rows = source_connection.execute(
        select(source_tables[table_name])
    ).mappings().all()

    if rows:
        target_connection.execute(
            target_table(table_name).insert(),
            [dict(row) for row in rows],
        )

    return len(rows)


def target_table(table_name: str):
    if table_name == "tasks":
        return legacy_tasks
    return Base.metadata.tables[table_name]


def create_default_knowledge_bases(source_connection, target_connection) -> dict[int, int]:
    users = source_connection.execute(
        select(Base.metadata.tables["users"])
    ).mappings().all()
    knowledge_base_ids: dict[int, int] = {}

    for user in users:
        result = target_connection.execute(
            KnowledgeBaseORM.__table__.insert().values(
                owner_user_id=user["id"],
                name="Default knowledge base",
            )
        )
        knowledge_base_ids[int(user["id"])] = int(result.inserted_primary_key[0])

    return knowledge_base_ids


def copy_documents_with_default_knowledge_bases(
    source_connection,
    target_connection,
    source_tables,
    knowledge_base_ids: dict[int, int],
) -> int:
    rows = source_connection.execute(
        select(source_tables["documents"])
    ).mappings().all()
    if rows:
        target_connection.execute(
            Base.metadata.tables["documents"].insert(),
            [
                {
                    **dict(row),
                    "knowledge_base_id": knowledge_base_ids[int(row["user_id"])],
                }
                for row in rows
            ],
        )
    return len(rows)


def import_sqlite_data(source_url: str) -> dict[str, int]:
    if not source_url.startswith("sqlite"):
        raise ValueError("source database must use SQLite")

    source_engine = create_engine(source_url)

    try:
        source_tables = load_source_tables(source_engine)
        ensure_mysql_is_empty()

        with source_engine.connect() as source_connection:
            with mysql_engine.begin() as target_connection:
                counts = {}
                for table_name in ("users", "tasks"):
                    counts[table_name] = copy_table(
                        source_connection,
                        target_connection,
                        source_tables,
                        table_name,
                    )
                knowledge_base_ids = create_default_knowledge_bases(
                    source_connection,
                    target_connection,
                )
                counts["documents"] = copy_documents_with_default_knowledge_bases(
                    source_connection,
                    target_connection,
                    source_tables,
                    knowledge_base_ids,
                )
    finally:
        source_engine.dispose()

    return counts


def main():
    args = parse_args()
    counts = import_sqlite_data(args.source_url)

    print("SQLite to MySQL import completed.")
    for table_name in TABLE_NAMES:
        print(f"{table_name}: {counts[table_name]} row(s)")


if __name__ == "__main__":
    main()

from argparse import ArgumentParser

from sqlalchemy import MetaData, create_engine, func, select

from python_practice.day57.database import Base, engine as mysql_engine
from python_practice.day57.models.document import DocumentORM
from python_practice.day57.models.task import TaskORM
from python_practice.day57.models.user import UserORM


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
                select(func.count()).select_from(
                    Base.metadata.tables[table_name]
                )
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
            Base.metadata.tables[table_name].insert(),
            [dict(row) for row in rows],
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
                counts = {
                    table_name: copy_table(
                        source_connection,
                        target_connection,
                        source_tables,
                        table_name,
                    )
                    for table_name in TABLE_NAMES
                }
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
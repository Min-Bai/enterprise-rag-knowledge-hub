"""Private schema mapping used only to import records from the retired Todo app."""

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, MetaData, String, Table


legacy_metadata = MetaData()
legacy_tasks = Table(
    "tasks",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(50), nullable=False),
    Column("done", Boolean, nullable=False),
    Column("user_id", Integer, nullable=True),
    Column("priority", Integer, nullable=False),
    Column("due_date", Date, nullable=True),
    Column("updated_at", DateTime, nullable=False),
    Column("archived", Boolean, nullable=False),
)

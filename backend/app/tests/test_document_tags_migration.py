from unittest.mock import Mock

import sqlalchemy as sa

from backend.app.migrations.versions import e2f3a4b5c6d7_add_document_tags as migration


def test_document_tags_migration_backfills_before_making_column_required(monkeypatch):
    operation = Mock()
    batch_operation = Mock()
    batch_context = Mock()
    batch_context.__enter__ = Mock(return_value=batch_operation)
    batch_context.__exit__ = Mock(return_value=False)
    operation.batch_alter_table.return_value = batch_context
    monkeypatch.setattr(migration, "op", operation)

    migration.upgrade()

    column = operation.add_column.call_args.args[1]
    assert column.name == "tags"
    assert isinstance(column.type, sa.JSON)
    assert column.nullable is True
    assert column.server_default is None
    operation.execute.assert_called_once_with("UPDATE documents SET tags = JSON_ARRAY() WHERE tags IS NULL")
    batch_operation.alter_column.assert_called_once()
    args, kwargs = batch_operation.alter_column.call_args
    assert args == ("tags",)
    assert isinstance(kwargs["existing_type"], sa.JSON)
    assert kwargs["nullable"] is False

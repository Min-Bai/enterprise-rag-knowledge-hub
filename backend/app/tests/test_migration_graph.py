import ast
from pathlib import Path


VERSIONS_DIRECTORY = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _assignment_value(module: ast.Module, name: str):
    for statement in module.body:
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target] if isinstance(statement, ast.AnnAssign) else []
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return ast.literal_eval(statement.value)
    raise AssertionError(f"Missing {name} assignment")


def test_migration_graph_has_one_unique_head():
    revisions = {}
    parent_revisions = set()

    for path in VERSIONS_DIRECTORY.glob("*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        revision = _assignment_value(module, "revision")
        down_revision = _assignment_value(module, "down_revision")

        assert revision not in revisions, f"Duplicate Alembic revision {revision}: {path} and {revisions[revision]}"
        revisions[revision] = path

        if down_revision is None:
            continue
        parent_revisions.update((down_revision,) if isinstance(down_revision, str) else down_revision)

    assert parent_revisions <= revisions.keys(), "A migration references a missing parent revision"
    assert set(revisions) - parent_revisions == {"0a1b2c3d4e5f"}

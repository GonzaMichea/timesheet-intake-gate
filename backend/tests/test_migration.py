"""Los modelos SQLAlchemy y las migraciones SQL describen las mismas tablas (design §5)."""
import re

from backend.app.db.models import Base
from backend.tests.helpers import ROOT

NOT_COLUMNS = {"unique", "check", "primary", "constraint", "references", "foreign"}


def migration_columns() -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for path in sorted((ROOT / "supabase" / "migrations").glob("*.sql")):
        sql = re.sub(r"--.*", "", path.read_text(encoding="utf-8"))
        for name, body in re.findall(r"create table public\.(\w+) \((.*?)\n\);", sql, re.S):
            tables[name] = {line.split()[0] for line in body.splitlines()
                            if line.strip() and line.split()[0] not in NOT_COLUMNS and line.startswith("  ")
                            and not line.startswith("    ")}
        for table, column in re.findall(r"alter table public\.(\w+) add column (\w+)", sql):
            tables[table].add(column)
    return tables


def test_migration_matches_models():
    models = {t.name: {c.name for c in t.columns} for t in Base.metadata.sorted_tables}
    assert migration_columns() == models


def test_every_table_has_rls_enabled_in_migrations():
    sql = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "supabase" / "migrations").glob("*.sql"))
    created = set(re.findall(r"create table public\.(\w+)", sql))
    secured = set(re.findall(r"alter table public\.(\w+) enable row level security", sql))
    assert created == secured

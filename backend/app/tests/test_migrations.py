"""
Static analysis tests for Alembic migration files.

These tests catch SQL compatibility issues that only surface on PostgreSQL
but are silently accepted by SQLite (used in the test suite).

Covers:
  - No bare integer 0/1 literals as values in INSERT statements
    (PostgreSQL requires TRUE/FALSE for boolean columns)
"""

import ast
import re
from pathlib import Path

MIGRATION_DIR = Path(__file__).parent.parent.parent / "alembic" / "versions"


def _extract_execute_sql(source: str) -> list[str]:
    """Return string arguments passed to op.execute() calls in a migration file."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "execute"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            results.append(node.args[0].value)
    return results


def test_no_integer_boolean_literals_in_migration_inserts():
    """
    Raw SQL INSERT statements in migrations must use TRUE/FALSE for boolean
    columns, not integer 0/1.

    PostgreSQL is strict about type matching; SQLite silently coerces integers
    to booleans. Using integers in raw SQL causes migration failures on
    PostgreSQL while passing all SQLite-based tests undetected.

    Good:  INSERT INTO t (flag) VALUES (TRUE)  or  SELECT ..., TRUE, FALSE
    Bad:   INSERT INTO t (flag) VALUES (0)     or  SELECT ..., 0, 1
    """
    # Matches a line that is nothing but optional whitespace + 0 or 1 + optional
    # comma — i.e. a bare integer standing alone as an INSERT value.
    bare_int_value = re.compile(r"^\s+[01]\s*,?\s*$", re.MULTILINE)

    failures = []
    for migration_file in sorted(MIGRATION_DIR.glob("*.py")):
        source = migration_file.read_text()
        for sql in _extract_execute_sql(source):
            if "INSERT" not in sql.upper():
                continue
            matches = bare_int_value.findall(sql)
            if matches:
                failures.append(
                    f"{migration_file.name}: bare integer value in INSERT SQL — "
                    f"use TRUE/FALSE instead of 0/1 for boolean columns: {matches!r}"
                )

    assert not failures, "\n".join(failures)

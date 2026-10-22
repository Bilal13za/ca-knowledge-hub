"""Versioned migration framework.

Each migration is a SQL file in ``hubcore/migrations/`` named
``NNN_description.sql`` with two sections::

    -- UP --
    <DDL / seed SQL>
    -- DOWN --
    <SQL that reverses the UP section>

The runner applies pending migrations in order and records them in
``schema_migrations``. Rollback applies DOWN sections in reverse order.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
DOWN_MARKER = re.compile(r"^\s*--\s*DOWN\s*--\s*$", re.MULTILINE)


def discover_migrations() -> list[tuple[int, str, Path]]:
    """Return [(version, description, path)] sorted by version."""
    found: list[tuple[int, str, Path]] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        m = re.match(r"(\d+)_(.+)\.sql$", path.name)
        if not m:
            continue
        found.append((int(m.group(1)), m.group(2), path))
    return found


def parse_migration(path: Path) -> tuple[str, str]:
    """Split a migration file into (up_sql, down_sql)."""
    text = path.read_text(encoding="utf-8")
    parts = DOWN_MARKER.split(text, maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Migration {path.name} is missing a '-- DOWN --' section")
    up = _strip_up_header(parts[0])
    return up.strip(), parts[1].strip()


def _strip_up_header(up: str) -> str:
    lines = up.splitlines()
    # drop a leading "-- UP --" marker line if present
    if lines and re.match(r"^\s*--\s*UP\s*--\s*$", lines[0]):
        lines = lines[1:]
    return "\n".join(lines)


def applied_versions(conn: sqlite3.Connection) -> list[int]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    )
    if cur.fetchone() is None:
        return []
    return [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]


def migrate(conn: sqlite3.Connection) -> list[int]:
    """Apply all pending migrations in order. Returns newly applied versions."""
    applied = set(applied_versions(conn))
    newly: list[int] = []
    for version, description, path in discover_migrations():
        if version in applied:
            continue
        up_sql, _ = parse_migration(path)
        with conn:
            conn.executescript(up_sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (version, description),
            )
        newly.append(version)
    return newly


def rollback(conn: sqlite3.Connection, target_version: int = 0) -> list[int]:
    """Roll back migrations down to (and excluding) target_version."""
    applied = applied_versions(conn)
    by_version = {v: p for v, _, p in discover_migrations()}
    rolled: list[int] = []
    for version in sorted(applied, reverse=True):
        if version <= target_version:
            break
        path = by_version.get(version)
        if path is None:
            raise ValueError(f"No migration file found for applied version {version}")
        _, down_sql = parse_migration(path)
        with conn:
            conn.executescript(down_sql)
            # The DOWN section may itself drop schema_migrations (a full
            # reversal to version 0); only delete the row if the table
            # still exists.
            still_there = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
            if still_there:
                conn.execute(
                    "DELETE FROM schema_migrations WHERE version = ?", (version,)
                )
        rolled.append(version)
    return rolled


def current_version(conn: sqlite3.Connection) -> int:
    versions = applied_versions(conn)
    return max(versions) if versions else 0

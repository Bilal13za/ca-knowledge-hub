"""SQLite connection handling and schema helpers."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import migrations


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Open (creating parent dirs) a Hub database with sane pragmas."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def initialise(conn: sqlite3.Connection) -> list[int]:
    """Apply pending migrations. Returns newly applied versions."""
    return migrations.migrate(conn)


def integrity_check(conn: sqlite3.Connection) -> str:
    """Run PRAGMA integrity_check; returns 'ok' or the problem report."""
    rows = conn.execute("PRAGMA integrity_check").fetchall()
    texts = [r[0] for r in rows]
    if texts == ["ok"]:
        return "ok"
    return "\n".join(texts)


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Row counts for every table (excluding sqlite internals and FTS shadows)."""
    counts: dict[str, int] = {}
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' "
            "AND name NOT LIKE '%_fts_config' AND name NOT LIKE '%_fts_data' "
            "AND name NOT LIKE '%_fts_docsize' AND name NOT LIKE '%_fts_idx' "
            "AND name NOT LIKE '%_fts_content' "
            "ORDER BY name"
        )
    ]
    for table in tables:
        try:
            counts[table] = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        except sqlite3.Error:
            counts[table] = -1
    return counts

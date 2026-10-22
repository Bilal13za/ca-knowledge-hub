"""Export format (spec section 4, Layer 5).

export_all() produces, under out_dir/:
    modules/<module>/knowledge_records.json
    modules/<module>/knowledge_records.csv
    modules/<module>/rules.json
    modules/<module>/procedures.json
    modules/<module>/calculations.json
    modules/<module>/relations.json
    hub.sqlite.dump            -- full SQLite dump (re-importable SQL)
    manifest.json              -- schema version, module versions, counts, date

Everything is human-readable and re-importable. No proprietary formats.
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import db as dbmod

CORE_TABLES = (
    "knowledge_records",
    "rules",
    "procedures",
    "calculations",
    "sources",
)


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params)]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def export_module_records(
    conn: sqlite3.Connection, module: str, out_dir: str | Path
) -> dict[str, int]:
    """Export one module's core tables to JSON (+ CSV for knowledge_records).
    Returns {table: row_count}."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    records = _rows(
        conn, "SELECT * FROM knowledge_records WHERE module = ? ORDER BY id", (module,)
    )
    (out / "knowledge_records.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    counts["knowledge_records"] = len(records)
    if records:
        with (out / "knowledge_records.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)

    for table in ("rules", "procedures", "calculations"):
        rows = _rows(conn, f'SELECT * FROM "{table}" WHERE module = ? ORDER BY id', (module,))
        (out / f"{table}.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        counts[table] = len(rows)

    relations = _rows(
        conn,
        """SELECT rr.* FROM record_relations rr
           JOIN knowledge_records kr ON kr.id = rr.source_record_id
           WHERE kr.module = ? ORDER BY rr.id""",
        (module,),
    )
    (out / "relations.json").write_text(
        json.dumps(relations, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    counts["relations"] = len(relations)
    return counts


def export_sqlite_dump(conn: sqlite3.Connection, out_path: str | Path) -> Path:
    """Write a full re-importable SQL dump of the database."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(line + "\n")
    return out


def list_modules_present(conn: sqlite3.Connection) -> list[str]:
    rows = _rows(conn, "SELECT DISTINCT module FROM knowledge_records ORDER BY 1")
    mods = [r["module"] for r in rows]
    for table in ("rules", "procedures", "calculations"):
        for r in _rows(conn, f"SELECT DISTINCT module FROM {table}"):
            if r["module"] not in mods:
                mods.append(r["module"])
    return sorted(mods)


def export_all(conn: sqlite3.Connection, out_dir: str | Path) -> Path:
    """Full export per the format above. Returns the manifest path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    per_module: dict[str, dict[str, int]] = {}
    for module in list_modules_present(conn):
        per_module[module] = export_module_records(conn, module, out / "modules" / module)

    export_sqlite_dump(conn, out / "hub.sqlite.dump")

    manifest = {
        "format": "ca-knowledge-hub-export",
        "format_version": 1,
        "exported_at": _utcnow(),
        "schema_version": dbmod.migrations.current_version(conn),
        "module_versions": {
            r["name"]: r["version"]
            for r in _rows(conn, "SELECT name, version FROM modules ORDER BY name")
        },
        "modules": per_module,
        "table_counts": dbmod.table_counts(conn),
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def export_summary(conn: sqlite3.Connection) -> dict:
    """Lightweight summary without writing files (for UI display)."""
    return {
        "schema_version": dbmod.migrations.current_version(conn),
        "modules": list_modules_present(conn),
        "table_counts": dbmod.table_counts(conn),
    }

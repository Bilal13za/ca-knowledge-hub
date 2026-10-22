"""Knowledge-record management (Phase 1C).

CRUD plus versioned revision (never silently overwrite important rules),
review-due surfacing, and cross-module relationships (spec section 4B).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

VERIFICATION_STATUSES = (
    "verified", "extracted_unverified", "user_note", "interpretation", "superseded",
)


def _check_status(status: str) -> None:
    if status not in VERIFICATION_STATUSES:
        raise ValueError(f"Invalid verification_status {status!r}")


def _check_extension_json(value: str) -> None:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"extension_json is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("extension_json must be a JSON object")


def create_record(conn: sqlite3.Connection, data: dict) -> int:
    """Insert a knowledge record. Returns the new id."""
    status = data.get("verification_status", "user_note")
    _check_status(status)
    ext = data.get("extension_json", "{}")
    if isinstance(ext, dict):
        ext = json.dumps(ext)
    _check_extension_json(ext)
    cur = conn.execute(
        """INSERT INTO knowledge_records
           (module, topic, subtopic, title, description, keywords, content,
            source_id, source_page, jurisdiction, effective_date,
            applicable_period, verification_status, last_reviewed,
            review_due_date, extension_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data.get("module", "core"), data.get("topic", ""),
            data.get("subtopic", ""), data["title"],
            data.get("description", ""), data.get("keywords", ""),
            data.get("content", ""), data.get("source_id"),
            data.get("source_page", ""), data.get("jurisdiction", ""),
            data.get("effective_date", ""), data.get("applicable_period", ""),
            status, data.get("last_reviewed", ""),
            data.get("review_due_date", ""), ext,
        ),
    )
    record_id = cur.lastrowid
    _index_record_fts(conn, record_id)
    return record_id


def _index_record_fts(conn: sqlite3.Connection, record_id: int) -> None:
    conn.execute("DELETE FROM record_fts WHERE record_id = ?", (record_id,))
    row = conn.execute(
        "SELECT title, description, keywords, content, module "
        "FROM knowledge_records WHERE id = ?",
        (record_id,),
    ).fetchone()
    if row:
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content, record_id, module)"
            " VALUES (?,?,?,?,?,?)",
            (row["title"], row["description"], row["keywords"],
             row["content"], record_id, row["module"]),
        )


def get_record(conn: sqlite3.Connection, record_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM knowledge_records WHERE id = ?", (record_id,)
    ).fetchone()
    return dict(row) if row else None


def update_record(conn: sqlite3.Connection, record_id: int, data: dict) -> None:
    """Direct update (for minor edits). For important rule changes use
    revise_record(), which versions the change."""
    allowed = (
        "module", "topic", "subtopic", "title", "description", "keywords",
        "content", "source_id", "source_page", "jurisdiction",
        "effective_date", "applicable_period", "verification_status",
        "last_reviewed", "review_due_date", "extension_json",
    )
    sets, params = [], []
    for key in allowed:
        if key in data:
            if key == "verification_status":
                _check_status(data[key])
            if key == "extension_json":
                ext = data[key]
                _check_extension_json(ext if isinstance(ext, str) else json.dumps(ext))
            sets.append(f"{key} = ?")
            val = data[key]
            params.append(json.dumps(val) if key == "extension_json" and isinstance(val, dict) else val)
    if not sets:
        return
    sets.append("updated_at = datetime('now')")
    params.append(record_id)
    conn.execute(f"UPDATE knowledge_records SET {', '.join(sets)} WHERE id = ?", params)
    _index_record_fts(conn, record_id)


def revise_record(conn: sqlite3.Connection, record_id: int, new_data: dict, *,
                  reason: str, source_of_change: str = "") -> int:
    """Versioned revision: snapshots the old content into revision_history,
    then applies the update. Returns the new revision version number."""
    old = get_record(conn, record_id)
    if old is None:
        raise ValueError(f"No knowledge record {record_id}")
    version = conn.execute(
        "SELECT COALESCE(MAX(version),0)+1 FROM revision_history "
        "WHERE entity_type='knowledge_record' AND entity_id=?",
        (record_id,),
    ).fetchone()[0]
    conn.execute(
        """INSERT INTO revision_history
           (entity_type, entity_id, version, previous_content_json,
            revised_content_json, reason, source_of_change, effective_date,
            verification_status)
           VALUES ('knowledge_record',?,?,?,?,?,?,?,?)""",
        (
            record_id, version, json.dumps(old), json.dumps(new_data),
            reason, source_of_change, new_data.get("effective_date", ""),
            new_data.get("verification_status", old["verification_status"]),
        ),
    )
    update_record(conn, record_id, new_data)
    return version


def delete_record(conn: sqlite3.Connection, record_id: int) -> None:
    """Delete a record. revision_history rows are kept (no FK), so the
    change is never silent."""
    conn.execute("DELETE FROM record_fts WHERE record_id = ?", (record_id,))
    conn.execute("DELETE FROM record_relations WHERE source_record_id = ? OR target_record_id = ?",
                 (record_id, record_id))
    conn.execute("DELETE FROM knowledge_records WHERE id = ?", (record_id,))


def list_records(conn: sqlite3.Connection, *, module: str | None = None,
                 topic: str | None = None,
                 verification_status: str | None = None,
                 limit: int = 200) -> list[dict]:
    sql, params = "SELECT * FROM knowledge_records WHERE 1=1", []
    if module:
        sql += " AND module = ?"; params.append(module)
    if topic:
        sql += " AND topic = ?"; params.append(topic)
    if verification_status:
        _check_status(verification_status)
        sql += " AND verification_status = ?"; params.append(verification_status)
    sql += " ORDER BY module, topic, title LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]


def due_for_review(conn: sqlite3.Connection, *, within_days: int = 30) -> list[dict]:
    """Records whose review_due_date is past or within `within_days`."""
    cutoff = (date.today() + timedelta(days=within_days)).isoformat()
    return [dict(r) for r in conn.execute(
        """SELECT * FROM knowledge_records
           WHERE review_due_date != '' AND review_due_date <= ?
             AND verification_status != 'superseded'
           ORDER BY review_due_date""",
        (cutoff,),
    )]


def add_relation(conn: sqlite3.Connection, source_id: int, target_id: int, *,
                 rel_type: str = "related", note: str = "") -> int:
    """Create a cross-module link (no-code relationship record, spec 4B)."""
    if source_id == target_id:
        raise ValueError("A record cannot relate to itself")
    cur = conn.execute(
        """INSERT OR IGNORE INTO record_relations
           (source_record_id, target_record_id, rel_type, note)
           VALUES (?,?,?,?)""",
        (source_id, target_id, rel_type, note),
    )
    return cur.lastrowid


def get_relations(conn: sqlite3.Connection, record_id: int) -> list[dict]:
    """All relations touching a record, with the other side's title/module."""
    return [dict(r) for r in conn.execute(
        """SELECT rr.*, kr.title AS other_title, kr.module AS other_module,
                  CASE WHEN rr.source_record_id = ? THEN 'outgoing' ELSE 'incoming' END AS direction
           FROM record_relations rr
           JOIN knowledge_records kr ON kr.id =
             CASE WHEN rr.source_record_id = ? THEN rr.target_record_id ELSE rr.source_record_id END
           WHERE rr.source_record_id = ? OR rr.target_record_id = ?
           ORDER BY rr.rel_type""",
        (record_id, record_id, record_id, record_id),
    )]


def related_in_other_modules(conn: sqlite3.Connection, record_id: int,
                             active_modules: list[str]) -> list[dict]:
    """Relations pointing into modules NOT in the active workspace —
    drives the 'load this module?' prompt (spec 4B.5)."""
    rels = get_relations(conn, record_id)
    return [r for r in rels if r["other_module"] not in active_modules]


def validate_extension_against_schema(extension: dict, schema: dict) -> list[str]:
    """Minimal JSON-Schema-ish validation (type/object/properties only).
    Returns a list of problems (empty = valid). Full JSON Schema is not
    required; keep the dependency footprint at zero."""
    problems: list[str] = []
    if not isinstance(schema, dict):
        return problems
    if schema.get("type") == "object" and not isinstance(extension, dict):
        return ["extension must be an object"]
    props = schema.get("properties", {})
    for key, subschema in props.items():
        if key in extension:
            want = subschema.get("type")
            got = type(extension[key]).__name__
            type_map = {"string": "str", "array": "list", "object": "dict",
                        "number": ("int", "float"), "boolean": "bool",
                        "integer": "int"}
            expected = type_map.get(want)
            if expected and (
                (isinstance(expected, tuple) and got not in expected)
                or (isinstance(expected, str) and got != expected)
            ):
                problems.append(f"extension.{key}: expected {want}, got {got}")
    return problems

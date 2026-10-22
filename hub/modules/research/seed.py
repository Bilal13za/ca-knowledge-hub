"""Phase 12 seeder: research module (methodology guides + schema)."""
from __future__ import annotations

import json
from pathlib import Path

GUIDES = [
    ("How to register a research issue",
     "State the question precisely, add background facts, and keep the "
     "issue open until every source is compared. A vague question "
     "produces a vague conclusion.",
     "research,issue,method"),
    ("How to compare sources",
     "For each aspect of the question, record what each source says and "
     "whether they agree, conflict, or are unclear. Prefer primary "
     "sources (statute, circulars) over commentary; note the hierarchy "
     "in the comparison note.",
     "research,comparison,sources"),
    ("How to version conclusions",
     "Every conclusion is a version, never an edit. When new evidence "
     "arrives, record a new version with its basis. The history shows "
     "how your understanding evolved — that trail is the professional "
     "value.",
     "research,conclusion,versioning"),
]


def seed_research(conn, data_dir=None) -> dict:
    conn.executescript(
        (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    conn.execute("DELETE FROM record_fts WHERE module='research'")
    conn.execute("DELETE FROM knowledge_records WHERE module='research'")
    n = 0
    for title, desc, kw in GUIDES:
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('research','guide',?,?,?,?, 'user_note', '{}')""",
            (title, desc, kw, f"{title}. {desc}"))
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, desc, kw, f"{title}. {desc}", rid, "research"))
        n += 1
    conn.commit()
    return {"rs_issues": 0, "knowledge_records(research)": n}

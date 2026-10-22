"""Phase 11 seeder: company-law module."""
from __future__ import annotations

import json
from pathlib import Path

STATUS_LABEL = {
    "verified": "✅ verified",
    "extracted_unverified": "⚠️ extracted — unverified",
    "user_note": "📝 user note",
    "interpretation": "💡 interpretation",
    "superseded": "🗃️ superseded",
}


def seed_complaw(conn, data_dir=None) -> dict:
    data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    conn.executescript(
        (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    topics = json.loads(
        (data_dir / "starter_topics.json").read_text(encoding="utf-8"))
    for t in topics["topics"]:
        exists = conn.execute(
            "SELECT 1 FROM law_provisions WHERE title = ?",
            (t["title"],)).fetchone()
        if exists:
            continue
        conn.execute(
            """INSERT INTO law_provisions
               (act, section_no, title, summary, source_ref,
                verification_status, notes)
               VALUES ('Companies Act, 2017', NULL, ?, ?, 'UNTRACED STARTER TOPIC -- verify against the official Companies Act, 2017 text (SECP) before relying on it.', 'user_note', ?)""",
            (t["title"],
             "Research checklist item. No section number is asserted.",
             t["lookup_guidance"]))
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM law_provisions").fetchone()[0]
    stubs = _register_stubs(conn)
    conn.commit()
    return {"law_provisions": n, "knowledge_records(complaw)": stubs}


def _register_stubs(conn) -> int:
    conn.execute("DELETE FROM record_fts WHERE module='complaw'")
    conn.execute("DELETE FROM knowledge_records WHERE module='complaw'")
    n = 0
    for r in conn.execute("SELECT * FROM law_provisions ORDER BY id"):
        title = f"{r['act']} — {r['title']}"
        desc = (f"[{STATUS_LABEL.get(r['verification_status'], '?')}] "
                f"Section: {r['section_no'] or 'not yet traced'}. "
                f"{r['source_ref'] or ''}")[:600]
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('complaw','provision',?,?,?,?,?,?)""",
            (title, desc, "companies act compliance",
             f"{title}. {desc}", r["verification_status"],
             json.dumps({"law_provision": r["id"]})))
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, desc, "companies act compliance",
             f"{title}. {desc}", rid, "complaw"))
        n += 1
    conn.commit()
    return n

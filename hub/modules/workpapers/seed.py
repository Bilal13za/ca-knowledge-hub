"""Phase 9 seeder: workpapers module (template library)."""
from __future__ import annotations

import json
from pathlib import Path


def seed_workpapers(conn, data_dir=None) -> dict:
    data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    conn.executescript(
        (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    templates = json.loads(
        (data_dir / "templates.json").read_text(encoding="utf-8"))["templates"]
    for t in templates:
        conn.execute(
            """INSERT OR REPLACE INTO wp_templates
               (id, category, title, purpose, structure_json, guidance,
                verification_status, disclaimer)
               VALUES (?,?,?,?,?,?,?,?)""",
            (t["id"], t["category"], t["title"], t.get("purpose"),
             json.dumps(t.get("structure", []), ensure_ascii=False),
             t.get("guidance"),
             t.get("verification_status", "user_note"),
             t.get("disclaimer",
                   "Generic template for study and practice. Does not "
                   "satisfy any particular firm's audit methodology.")))
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM wp_templates").fetchone()[0]
    stubs = _register_stubs(conn)
    conn.commit()
    return {"wp_templates": n, "knowledge_records(workpapers)": stubs}


def _register_stubs(conn) -> int:
    conn.execute("DELETE FROM record_fts WHERE module='workpapers'")
    conn.execute("DELETE FROM knowledge_records WHERE module='workpapers'")
    n = 0
    for r in conn.execute("SELECT * FROM wp_templates ORDER BY id"):
        title = f"{r['id']}: {r['title']}"
        desc = (r["purpose"] or "")[:500]
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('workpapers','template',?,?,?,?,?,?)""",
            (title, desc, r["id"], f"{title}. {desc}",
             "user_note", json.dumps({"wp_template": r["id"]})))
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, desc, r["id"], f"{title}. {desc}", rid, "workpapers"))
        n += 1
    conn.commit()
    return n

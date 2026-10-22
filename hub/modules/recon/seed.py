"""Phase 5 seeder: reconciliation module (schema only — no seed data).

Reconciliation data is Bilal's own working data, imported per run.
"""
from __future__ import annotations

from pathlib import Path


def seed_recon(conn, data_dir: str | Path | None = None) -> dict:
    conn.executescript(
        (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    return {"recon_runs": 0, "recon_datasets": 0, "recon_findings": 0,
            "knowledge_records(recon)": _register_stubs(conn)}


def _register_stubs(conn) -> int:
    """Help-topic stubs so the module is discoverable in global search."""
    conn.execute("DELETE FROM record_fts WHERE module='recon'")
    conn.execute("DELETE FROM knowledge_records WHERE module='recon'")
    topics = [
        ("Bank reconciliation",
         "Match bank statement lines to the cash book: exact and tolerance-based matching, unmatched items, amount differences.",
         "bank supplier customer gl inventory payroll tax reconciliation matching"),
        ("Duplicate detection",
         "Find rows sharing the same key values (invoice numbers, references). Blank keys are ignored, never false-positive.",
         "duplicate invoices references keys"),
        ("File validation",
         "Row-level checks: required columns, date formats, numeric amounts, sign rules, arithmetic totals, outliers.",
         "validation dates amounts totals outliers"),
    ]
    n = 0
    for title, desc, keywords in topics:
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('recon','howto',?,?,?,?,?,?)""",
            (title, desc, keywords, f"{title}. {desc}", "user_note", "{}"))
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, desc, keywords, f"{title}. {desc}", rid, "recon"))
        n += 1
    conn.commit()
    return n

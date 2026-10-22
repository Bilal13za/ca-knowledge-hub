"""Phase 8 seeder: FS analysis module (schema + help stubs)."""
from __future__ import annotations

from pathlib import Path


def seed_fsanalysis(conn, data_dir=None) -> dict:
    conn.executescript(
        (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    n = _register_stubs(conn)
    conn.commit()
    return {"fs_runs": 0, "knowledge_records(fsanalysis)": n}


def _register_stubs(conn) -> int:
    conn.execute("DELETE FROM record_fts WHERE module='fsanalysis'")
    conn.execute("DELETE FROM knowledge_records WHERE module='fsanalysis'")
    topics = [
        ("Ratio analysis",
         "Profitability, liquidity, solvency, efficiency and cash ratios from P&L/SFP line items. Ratios with missing inputs are skipped, never invented.",
         "ratios profitability liquidity solvency efficiency"),
        ("Trend and common-size analysis",
         "Period-over-period ratio trends and common-size statements (% of revenue / total assets).",
         "trends common-size horizontal vertical analysis"),
        ("Working capital cycle",
         "Receivable days, inventory days, payable days and the cash conversion cycle.",
         "working capital cash conversion cycle"),
        ("Red-flag indicators",
         "Investigation prompts (liquidity, earnings quality, solvency, efficiency) — indicators only, never proof of error or fraud.",
         "red flags indicators earnings quality"),
    ]
    n = 0
    for title, desc, keywords in topics:
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('fsanalysis','howto',?,?,?,?,?,?)""",
            (title, desc, keywords, f"{title}. {desc}", "user_note", "{}"))
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, desc, keywords, f"{title}. {desc}", rid, "fsanalysis"))
        n += 1
    conn.commit()
    return n

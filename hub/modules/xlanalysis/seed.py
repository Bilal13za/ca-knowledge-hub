"""Phase 6 seeder: data-analysis module (schema + help stubs)."""
from __future__ import annotations

import json
from pathlib import Path


def seed_xlanalysis(conn, data_dir: str | Path | None = None) -> dict:
    conn.executescript(
        (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    n = _register_stubs(conn)
    conn.commit()
    return {"xla_runs": 0, "knowledge_records(xlanalysis)": n}


def _register_stubs(conn) -> int:
    conn.execute("DELETE FROM record_fts WHERE module='xlanalysis'")
    conn.execute("DELETE FROM knowledge_records WHERE module='xlanalysis'")
    topics = [
        ("Data cleaning",
         "Strip whitespace, drop blank rows, normalise dates — every change logged, nothing silent.",
         "cleaning whitespace dates normalise"),
        ("Variance analysis",
         "Actual vs budget/prior period with explicit thresholds; flagged rows exported to a formatted workbook.",
         "variance budget actual threshold"),
        ("Group-by summaries",
         "Summarise by any column with sum, mean, count, min, max.",
         "summary pivot group-by totals"),
        ("Calculated columns",
         "Safe formula columns (arithmetic + abs/min/max/round); the recipe is stored for reproducibility.",
         "formula calculated column reproducible"),
        ("Exception reporting",
         "Threshold rules over any column: gt/lt/between/outside/blank.",
         "exceptions threshold outliers"),
    ]
    n = 0
    for title, desc, keywords in topics:
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('xlanalysis','howto',?,?,?,?,?,?)""",
            (title, desc, keywords, f"{title}. {desc}", "user_note", "{}"))
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, desc, keywords, f"{title}. {desc}", rid, "xlanalysis"))
        n += 1
    conn.commit()
    return n

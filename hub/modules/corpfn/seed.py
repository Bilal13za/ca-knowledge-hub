"""Phase 10 seeder: corporate finance module."""
from __future__ import annotations

import json
from pathlib import Path


GUIDES = [
    ("Investment appraisal",
     "Compare projects with NPV (accept if > 0), IRR (accept if above the "
     "hurdle rate) and payback (liquidity view only — it ignores the time "
     "value of money unless discounted). Assumptions: cash flows at period "
     "ends; the discount rate reflects the project's risk.",
     "investment appraisal,npv,irr,payback"),
    ("Cost of capital",
     "CAPM gives the cost of equity Ke = Rf + β(Rm − Rf). WACC blends Ke "
     "with after-tax cost of debt using market-value weights. Use WACC as "
     "the discount rate for the firm's typical projects.",
     "cost of capital,capm,wacc"),
    ("Valuation basics",
     "The Gordon growth model values a share as D1 / (ke − g) — only valid "
     "when ke > g and growth is stable forever. DCF values the firm from "
     "projected free cash flows discounted at WACC.",
     "valuation,gordon,dcf"),
    ("Financing decisions",
     "Debt adds a tax shield (interest is deductible) but raises financial "
     "risk; equity avoids fixed obligations but dilutes. The optimal mix "
     "balances tax benefit against distress cost — there is no universal "
     "formula, only trade-offs to document.",
     "financing,gearing,capital structure"),
    ("Sensitivity analysis",
     "Vary one assumption at a time (discount rate, outlay, cash flows) "
     "and watch NPV. A project whose accept/reject decision flips on a "
     "small change is high-risk however good the base case looks.",
     "sensitivity,what-if"),
]


def seed_corpfn(conn, data_dir=None) -> dict:
    conn.executescript(
        (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    conn.execute("DELETE FROM record_fts WHERE module='corpfn'")
    conn.execute("DELETE FROM knowledge_records WHERE module='corpfn'")
    n = 0
    for title, desc, kw in GUIDES:
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('corpfn','guide',?,?,?,?, 'user_note', '{}')""",
            (title, desc, kw, f"{title}. {desc}"))
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, desc, kw, f"{title}. {desc}", rid, "corpfn"))
        n += 1
    conn.commit()
    return {"cf_runs": 0, "knowledge_records(corpfn)": n}

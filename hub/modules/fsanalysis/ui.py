"""fsanalysis module UI pages (Phase 8).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations

import json


def _save_run(conn, name, kind, inputs, result):
    conn.execute(
        """INSERT INTO fs_runs (name, kind, inputs_json, result_json)
           VALUES (?,?,?,?)""",
        (name, kind, json.dumps(inputs, default=str),
         json.dumps(result, default=str)))
    conn.commit()


def _inputs_form(st, items, prefix):
    inputs = {}
    cols = st.columns(3)
    for i, item in enumerate(items):
        with cols[i % 3]:
            v = st.text_input(item, key=f"{prefix}_{item}")
            if v.strip():
                inputs[item] = v
    return inputs


def render_ratios(ctx):
    """Single-period ratio analysis + red flags."""
    import streamlit as st
    from . import ratios as rmod
    from . import redflags

    st.header("Ratio Analysis")
    st.caption("Ratios with missing inputs are skipped — never invented. "
               "Red flags are investigation prompts, never proof of error.")
    conn = ctx["conn"]
    name = st.text_input("Analysis name", placeholder="e.g. ABC Co FY2026")
    st.subheader("Profit & loss")
    pl_items = ["revenue", "cost_of_sales", "gross_profit",
                "operating_expenses", "operating_profit", "finance_costs",
                "profit_before_tax", "tax_expense", "profit_after_tax",
                "dividends_paid"]
    pl = _inputs_form(st, pl_items, "pl")
    st.subheader("Statement of financial position")
    sfp_items = ["total_assets", "non_current_assets", "current_assets",
                 "inventory", "trade_receivables", "cash",
                 "total_liabilities", "current_liabilities", "trade_payables",
                 "non_current_liabilities", "total_equity", "share_capital"]
    sfp = _inputs_form(st, sfp_items, "sfp")
    st.subheader("Cash flow")
    ocf = st.text_input("operating_cash_flow", key="cf_ocf")

    if st.button("Compute ratios", type="primary"):
        inputs = {**pl, **sfp}
        if ocf.strip():
            inputs["operating_cash_flow"] = ocf
        res = rmod.compute_ratios(inputs)
        by_cat: dict[str, list] = {}
        for rname, r in res["ratios"].items():
            by_cat.setdefault(r["category"], []).append((rname, r))
        for cat in ["profitability", "liquidity", "solvency",
                    "efficiency", "cash"]:
            if cat in by_cat:
                st.subheader(cat.title())
                for rname, r in by_cat[cat]:
                    st.write(f"**{r['label']}:** {r['value']}{r['unit']}")
        if res["skipped"]:
            with st.expander(f"{len(res['skipped'])} ratios skipped "
                             "(missing inputs)"):
                for s in res["skipped"]:
                    st.write(f"• {s['ratio']}: {s['reason']}")
        flags = redflags.evaluate_flags(res["ratios"])
        if flags:
            st.subheader("Red flags (investigate — not conclusions)")
            for f in flags:
                icon = "🚩" if f["severity"] == "warning" else "ℹ️"
                with st.expander(f"{icon} {f['code']}: {f['title']}"):
                    st.write(f["observed"])
                    st.write("**Why it can matter:** " + f["why_it_can_matter"])
                    st.write("**Investigate:** " + f["investigate"])
        if name:
            _save_run(conn, name, "ratios", inputs,
                      {"ratios": {k: str(v["value"])
                                  for k, v in res["ratios"].items()},
                       "flags": [f["code"] for f in flags]})
            st.success("Analysis saved.")


def render_trends(ctx):
    """Multi-period trends + common size."""
    import streamlit as st
    from . import ratios as rmod

    st.header("Trends & Common Size")
    conn = ctx["conn"]
    name = st.text_input("Analysis name", key="t_name")
    n = st.number_input("Periods", min_value=2, max_value=5, value=2)
    periods = []
    for p in range(int(n)):
        with st.expander(f"Period {p + 1}", expanded=p == 0):
            label = st.text_input("Label", value=f"FY{2025 + p}",
                                  key=f"t_label_{p}")
            rev = st.text_input("revenue", key=f"t_rev_{p}")
            pat = st.text_input("profit_after_tax", key=f"t_pat_{p}")
            rd = st.text_input("trade_receivables", key=f"t_rd_{p}")
            inv = st.text_input("inventory", key=f"t_inv_{p}")
            inputs = {}
            for k, v in (("revenue", rev), ("profit_after_tax", pat),
                         ("trade_receivables", rd), ("inventory", inv)):
                if v.strip():
                    inputs[k] = v
            periods.append({"label": label, "inputs": inputs})
    if st.button("Compute trends", type="primary"):
        trends = rmod.trend_analysis(periods)
        for rname, t in trends.items():
            if t["direction"] == "insufficient":
                continue
            arrow = {"up": "↗", "down": "↘", "flat": "→",
                     "mixed": "↔"}.get(t["direction"], "?")
            vals = " → ".join(f"{lbl}: {v}" for lbl, v in t["values"])
            st.write(f"**{t['label']}** {arrow} _{t['direction']}_ — {vals}")
        if name:
            _save_run(conn, name, "trends",
                      {"periods": [p["label"] for p in periods]},
                      {"directions": {k: v["direction"]
                                      for k, v in trends.items()}})
            st.success("Analysis saved.")


def render_working_capital(ctx):
    """Working capital cycle calculator."""
    import streamlit as st
    from . import ratios as rmod

    st.header("Working Capital Cycle")
    conn = ctx["conn"]
    c1, c2, c3 = st.columns(3)
    rev = c1.text_input("revenue")
    cogs = c2.text_input("cost_of_sales")
    rec = c1.text_input("trade_receivables")
    inv = c2.text_input("inventory")
    pay = c3.text_input("trade_payables")
    if st.button("Compute", type="primary"):
        inputs = {k: v for k, v in
                  (("revenue", rev), ("cost_of_sales", cogs),
                   ("trade_receivables", rec), ("inventory", inv),
                   ("trade_payables", pay)) if v.strip()}
        res = rmod.compute_ratios(inputs)
        for rname in ("receivable_days", "inventory_days", "payable_days",
                      "cash_conversion_cycle"):
            r = res["ratios"].get(rname)
            if r:
                st.write(f"**{r['label']}:** {r['value']} days")
        _save_run(conn, "working capital", "working_capital", inputs,
                  {k: str(v["value"])
                   for k, v in res["ratios"].items()})


def render_history(ctx):
    """Saved analyses."""
    import streamlit as st

    st.header("Saved Analyses")
    conn = ctx["conn"]
    for r in conn.execute("SELECT * FROM fs_runs ORDER BY id DESC"):
        with st.expander(f"#{r['id']}: {r['name']} ({r['kind']})"):
            st.json(json.loads(r["result_json"]))


def register_pages():
    return [
        {"id": "fsa_ratios", "title": "Ratio Analysis",
         "render": render_ratios, "modes": ["study", "practice", "professional"]},
        {"id": "fsa_trends", "title": "Trends & Common Size",
         "render": render_trends, "modes": ["study", "practice"]},
        {"id": "fsa_wc", "title": "Working Capital",
         "render": render_working_capital, "modes": ["study", "practice"]},
        {"id": "fsa_history", "title": "History",
         "render": render_history, "modes": ["study", "practice", "professional"]},
    ]

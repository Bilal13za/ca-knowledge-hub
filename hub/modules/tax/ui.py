"""Tax module UI pages (Phase 3).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations

import json


def _engine():
    from .engine import decision, calc

    return decision, calc


def _status_badge(status: str) -> str:
    return {"verified": "✅ verified", "draft": "📝 draft",
            "under_review": "🔍 under review"}.get(status, status)


def render_analyzer(ctx):
    """14-step tax analysis chain."""
    import streamlit as st

    st.header("Tax Analyzer — 14-step chain")
    st.caption("Deterministic: missing facts are reported as *needs input* — "
               "never guessed. Unverified rules are flagged, never presented "
               "as authoritative.")
    decision, calc = _engine()
    conn = ctx["conn"]

    with st.form("tax_facts"):
        c1, c2, c3 = st.columns(3)
        taxpayer_type = c1.selectbox("Taxpayer type",
                                     ["", "individual", "aop", "company"])
        province = c2.selectbox("Province", ["", "punjab", "sindh", "kpk",
                                             "balochistan", "ict", "gb", "ajk"])
        tax_year = c3.text_input("Tax year", value="2026")
        c1, c2, c3 = st.columns(3)
        tax_category = c1.selectbox("Tax category",
                                    ["", "income_tax", "withholding_tax",
                                     "sales_tax_federal", "sales_tax_provincial"])
        transaction_type = c2.text_input("Transaction type",
                                         placeholder="e.g. payment_for_goods")
        transaction_date = c3.text_input("Transaction date (YYYY-MM-DD)",
                                         placeholder="2026-07-15")
        amount = st.text_input("Amount (PKR, optional)", placeholder="1000000")
        go = st.form_submit_button("Run analysis", type="primary")

    if go:
        facts = {k: v for k, v in {
            "taxpayer_type": taxpayer_type or None,
            "province": province or None,
            "jurisdiction": province or None,
            "tax_year": tax_year or None,
            "tax_category": tax_category or None,
            "transaction_type": transaction_type or None,
            "transaction_date": transaction_date or None,
            "amount": float(amount) if amount else None,
        }.items() if v is not None}

        def calc_runner(calc_code, inputs):
            return calc.run_calculation(conn, calc_code, inputs,
                                        on_date=facts.get("transaction_date"),
                                        tax_year=facts.get("tax_year"))

        steps = decision.analyze(conn, {}, facts, calc_runner=calc_runner)
        for s in steps:
            icon = {"info": "ℹ️", "needs_input": "❓",
                    "unverified_rule": "⚠️",
                    "exception_flagged": "🚩"}.get(s["confidence"], "•")
            with st.expander(f"{icon} Step {s['step_no']}: {s['step_name']}",
                             expanded=s["confidence"] != "info"):
                st.write(s["finding"])
                if s["detail"]:
                    st.json(s["detail"])


def render_rules(ctx):
    """Browse the tax rule library."""
    import streamlit as st

    st.header("Tax Rule Library")
    conn = ctx["conn"]
    c1, c2 = st.columns(2)
    cats = [r[0] for r in conn.execute(
        "SELECT DISTINCT tax_category FROM tax_rules ORDER BY 1")]
    cat = c1.selectbox("Category", ["all"] + cats)
    only_verified = c2.checkbox("Verified only", value=True)
    sql = ("SELECT code, version, title, tax_category, verification_status,"
           " expected_treatment FROM tax_rules WHERE 1=1")
    params: list = []
    if cat != "all":
        sql += " AND tax_category=?"; params.append(cat)
    if only_verified:
        sql += " AND verification_status='verified'"
    sql += " ORDER BY code, version"
    rules = conn.execute(sql, params).fetchall()
    st.write(f"{len(rules)} rules")
    for r in rules[:200]:
        with st.expander(f"{r['code']} v{r['version']}: {r['title']} "
                         f"[{_status_badge(r['verification_status'])}]"):
            full = conn.execute(
                "SELECT * FROM tax_rules WHERE code=? AND version=?",
                (r["code"], r["version"])).fetchone()
            st.write(f"**Category:** {full['tax_category']} · "
                     f"**Jurisdiction:** {full['jurisdiction']}")
            st.write(f"**Trigger:** {full['triggering_transaction']}")
            st.write(f"**Expected treatment:** {full['expected_treatment']}")
            st.write(f"**Effective:** {full['effective_from']} → "
                     f"{full['effective_to'] or 'present'}")
            if full["interpretation_note"]:
                st.info("Interpretation (not statute): " +
                        full["interpretation_note"])
            if full["review_notes"]:
                st.caption("Review notes: " + full["review_notes"])


def render_calcs(ctx):
    """Browse calculation tables."""
    import streamlit as st

    st.header("Calculation Tables")
    st.caption("Rates, slabs and thresholds live here — never in code.")
    conn = ctx["conn"]
    rows = conn.execute(
        "SELECT code, version, name, kind, tax_category, verification_status,"
        " legislation_ref, effective_from, effective_to, tax_year, params"
        " FROM tax_calc_tables ORDER BY code, version").fetchall()
    for r in rows:
        with st.expander(f"{r['code']} v{r['version']}: {r['name']} "
                         f"[{_status_badge(r['verification_status'])}]"):
            st.write(f"**Kind:** {r['kind']} · **Category:** {r['tax_category']}")
            st.write(f"**Legislation:** {r['legislation_ref'] or '—'}")
            st.write(f"**Effective:** {r['effective_from']} → "
                     f"{r['effective_to'] or 'present'}"
                     + (f" · TY {r['tax_year']}" if r['tax_year'] else ""))
            st.json(json.loads(r["params"]))


def render_scenarios(ctx):
    """Browse predefined scenarios."""
    import streamlit as st

    st.header("Tax Scenarios")
    conn = ctx["conn"]
    rows = conn.execute(
        "SELECT code, name, category, description, review_status"
        " FROM tax_scenarios ORDER BY code").fetchall()
    for r in rows:
        with st.expander(f"{r['code']}: {r['name']} "
                         f"[{_status_badge(r['review_status'])}]"):
            st.write(f"**Category:** {r['category']}")
            st.write(r["description"])


def register_pages():
    return [
        {"id": "tax_analyzer", "title": "Tax Analyzer (14-step)",
         "render": render_analyzer, "modes": ["study", "practice", "professional"]},
        {"id": "tax_rules", "title": "Rule Library",
         "render": render_rules, "modes": ["study", "practice", "professional"]},
        {"id": "tax_calcs", "title": "Calculation Tables",
         "render": render_calcs, "modes": ["study", "practice", "professional"]},
        {"id": "tax_scenarios", "title": "Scenarios",
         "render": render_scenarios, "modes": ["study", "practice"]},
    ]

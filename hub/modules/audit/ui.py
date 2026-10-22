"""Audit module UI pages (Phase 2).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations


def _engine(conn):
    from .engine import RuleEngine

    return RuleEngine(conn)


def render_explorer(ctx):
    """Risk Explorer: select factors -> rule engine -> testing plan."""
    import streamlit as st

    st.header("Audit Risk Explorer")
    st.caption("Select the business factors that apply. The rule engine "
               "builds a testing plan. A factor is a *risk indicator* — "
               "never proof of misstatement.")
    conn = ctx["conn"]
    cycles = conn.execute(
        "SELECT id, name FROM audit_cycles ORDER BY name").fetchall()
    cycle_labels = {f"{c['id']}: {c['name']}": c["id"] for c in cycles}
    chosen_cycles = st.multiselect("Business cycles", list(cycle_labels))
    cycle_ids = [cycle_labels[c] for c in chosen_cycles]

    q = ("SELECT id, name, cycle_id FROM audit_factors "
         "WHERE review_status='Verified' ORDER BY cycle_id, id")
    factors = conn.execute(q).fetchall()
    if cycle_ids:
        factors = [f for f in factors if f["cycle_id"] in cycle_ids]
    options = {f"{f['id']}: {f['name']}": f["id"] for f in factors}
    selected_labels = st.multiselect("Business factors", list(options))
    selected = [options[l] for l in selected_labels]

    if st.button("Run assessment", type="primary", disabled=not selected):
        plan = _engine(conn).assess(selected, cycle_ids)
        st.subheader(f"Triggered rules ({plan['counts']['rules_triggered']})")
        for t in plan["triggered_rules"]:
            with st.expander(f"{t['rule_id']}: {t['rule_name']}"):
                st.write(t["rationale"])
                if t["missing_information"]:
                    st.warning("Missing information: " +
                               "; ".join(t["missing_information"]))
                st.caption(f"Priority {t['priority']} · v{t['version']} · "
                           f"{t['review_status']}")
        st.subheader(f"Risks ({plan['counts']['risks']})")
        for r in plan["risks"]:
            with st.expander(f"{r['id']}: {r['title']}"):
                st.write(r["description"])
                st.write("**Assertions:** " +
                         ", ".join(a["id"] for a in r["assertions"]))
                if r["triggered_by_rules"]:
                    st.caption("Surfaced by: " + ", ".join(r["triggered_by_rules"]))
        st.subheader(f"Procedures ({plan['counts']['procedures']})")
        for p in plan["procedures"]:
            with st.expander(f"{p['id']}: {p['title']} "
                             f"({p['test_type']})"):
                st.write(f"**Objective:** {p['objective']}")
                st.write("**Steps:**")
                st.text(p["steps"])
                st.write(f"**Expected result:** {p['expected_result']}")
                st.write(f"**If exception:** {p['exception_criteria']}")
                st.write(f"**Follow-up:** {p['follow_up']}")
                if p["evidence"]:
                    st.write("**Evidence:** " +
                             ", ".join(e["id"] for e in p["evidence"]))
                st.caption("Addresses risks: " + ", ".join(p["risk_ids"]))


def render_rules(ctx):
    """Browse the 30 editable rules."""
    import streamlit as st

    st.header("Audit Rule Library")
    conn = ctx["conn"]
    rules = conn.execute(
        "SELECT id, name, version, priority, status, review_status "
        "FROM audit_rules ORDER BY priority, id").fetchall()
    for r in rules:
        with st.expander(f"{r['id']}: {r['name']} (v{r['version']})"):
            import json

            full = conn.execute(
                "SELECT * FROM audit_rules WHERE id=?", (r["id"],)).fetchone()
            d = json.loads(full["definition"])
            st.write(f"**Status:** {r['status']} · **Review:** {r['review_status']}")
            st.write(full["rationale"] or "")
            when, then = d.get("when", {}), d.get("then", {})
            st.write("**When:** " + json.dumps(when))
            st.write("**Then risks:** " + ", ".join(then.get("risk_ids", [])))
            st.write("**Then procedures:** " + ", ".join(then.get("procedure_ids", [])))
            if then.get("note"):
                st.info(then["note"])


def render_procedures(ctx):
    """Procedure library with type filters."""
    import streamlit as st

    st.header("Audit Procedures")
    conn = ctx["conn"]
    types = [r[0] for r in conn.execute(
        "SELECT DISTINCT procedure_type FROM audit_procedures ORDER BY 1")]
    ttypes = [r[0] for r in conn.execute(
        "SELECT DISTINCT test_type FROM audit_procedures ORDER BY 1")]
    c1, c2 = st.columns(2)
    pt = c1.selectbox("Procedure type", ["all"] + types)
    tt = c2.selectbox("Test type", ["all"] + ttypes)
    sql = "SELECT id, title, procedure_type, test_type FROM audit_procedures WHERE 1=1"
    params: list = []
    if pt != "all":
        sql += " AND procedure_type=?"; params.append(pt)
    if tt != "all":
        sql += " AND test_type=?"; params.append(tt)
    sql += " ORDER BY id"
    procs = conn.execute(sql, params).fetchall()
    st.write(f"{len(procs)} procedures")
    for p in procs[:100]:
        with st.expander(f"{p['id']}: {p['title']}"):
            full = conn.execute(
                "SELECT * FROM audit_procedures WHERE id=?", (p["id"],)).fetchone()
            st.write(f"**Objective:** {full['objective']}")
            st.text(full["steps"])
            st.write(f"**Expected:** {full['expected_result']}")
            st.write(f"**Exception:** {full['exception_criteria']}")
            st.write(f"**Follow-up:** {full['follow_up']}")


def register_pages():
    return [
        {"id": "audit_explorer", "title": "Risk Explorer",
         "render": render_explorer, "modes": ["study", "practice"]},
        {"id": "audit_rules", "title": "Rule Library",
         "render": render_rules, "modes": ["study", "practice", "professional"]},
        {"id": "audit_procedures", "title": "Procedures",
         "render": render_procedures, "modes": ["practice", "professional"]},
    ]

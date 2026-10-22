"""FR module UI pages (Phase 4).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations

import json


def _journals(journals_json: str) -> list:
    try:
        return json.loads(journals_json or "[]")
    except (ValueError, TypeError):
        return []


def render_treatments(ctx):
    """Browse the treatment library."""
    import streamlit as st

    st.header("Accounting Treatments")
    st.caption("Study material at CAF level — marked unverified throughout. "
               "Verify against the official standard text before relying on "
               "any treatment. No paragraph numbers are cited, by policy.")
    conn = ctx["conn"]
    stds = [r[0] for r in conn.execute(
        "SELECT id FROM fr_standards ORDER BY id")]
    f = st.selectbox("Standard", ["all"] + stds)
    sql = ("SELECT t.id, t.title FROM fr_treatments t")
    params: list = []
    if f != "all":
        sql += (" JOIN fr_treatment_standard l ON l.treatment_id = t.id"
                " WHERE l.standard_id = ?")
        params.append(f)
    sql += " ORDER BY t.id"
    rows = conn.execute(sql, params).fetchall()
    st.write(f"{len(rows)} treatments")
    for r in rows:
        t = conn.execute(
            "SELECT * FROM fr_treatments WHERE id=?", (r["id"],)).fetchone()
        with st.expander(f"{t['id']}: {t['title']}"):
            linked = ", ".join(x[0] for x in conn.execute(
                "SELECT standard_id FROM fr_treatment_standard"
                " WHERE treatment_id=? ORDER BY standard_id", (t["id"],)))
            st.write(f"**Standards:** {linked or '—'}")
            st.write("**Transaction analysis:** " + (t["transaction_analysis"] or ""))
            if t["recognition"]:
                st.write("**Recognition:** " + t["recognition"])
            if t["initial_measurement"]:
                st.write("**Initial measurement:** " + t["initial_measurement"])
            if t["subsequent_measurement"]:
                st.write("**Subsequent measurement:** " + t["subsequent_measurement"])
            journals = _journals(t["journals_json"])
            if journals:
                st.write("**Journal entries:**")
                for j in journals:
                    st.write(f"• Dr {j.get('debit', '?')} / "
                             f"Cr {j.get('credit', '?')}"
                             + (f" — {j['narration']}" if j.get("narration") else ""))
            if t["presentation"]:
                st.write("**Presentation:** " + t["presentation"])
            if t["disclosure"]:
                st.write("**Disclosure:** " + t["disclosure"])
            if t["statement_impact"]:
                st.write("**Statement impact:** " + t["statement_impact"])
            mistakes = _journals(t["common_mistakes_json"])
            if mistakes:
                st.write("**Common mistakes:**")
                for m in mistakes:
                    st.write(f"• {m}")
            risks = conn.execute(
                "SELECT audit_risk_id, note FROM fr_treatment_audit_risk"
                " WHERE treatment_id=?", (t["id"],)).fetchall()
            if risks:
                st.write("**Linked audit risks:** " +
                         ", ".join(x[0] for x in risks))


def render_standards(ctx):
    """Browse standards."""
    import streamlit as st

    st.header("Standards")
    conn = ctx["conn"]
    for r in conn.execute("SELECT * FROM fr_standards ORDER BY id"):
        with st.expander(f"{r['id']}: {r['title']}"):
            st.write(r["summary"] or "")
            if r["effective_from"]:
                st.caption(f"Effective from {r['effective_from']}")
            st.caption("⚠️ Study-aid summary — verify against the official text.")


def render_examples(ctx):
    """Worked examples."""
    import streamlit as st

    st.header("Worked Examples")
    conn = ctx["conn"]
    for r in conn.execute(
            "SELECT e.*, t.title AS ttitle FROM fr_examples e "
            "JOIN fr_treatments t ON t.id = e.treatment_id ORDER BY e.id"):
        with st.expander(f"{r['id']}: {r['title']}"):
            st.caption(f"Treatment: {r['treatment_id']} — {r['ttitle']}")
            st.write("**Facts:** " + r["facts"])
            st.write("**Solution:** " + r["solution"])
            for j in _journals(r["journals_json"]):
                st.write(f"• Dr {j.get('debit', '?')} / Cr {j.get('credit', '?')}"
                         + (f" — {j['narration']}" if j.get("narration") else ""))


def render_suggester(ctx):
    """Rule-based treatment suggester (candidates only)."""
    import streamlit as st

    from .suggest import CHARACTERISTICS, suggest

    st.header("Treatment Suggester")
    st.caption("Tick what the transaction involves. You get *candidate* "
               "standards to investigate — never a determination.")
    conn = ctx["conn"]
    chosen = [cid for cid, label in CHARACTERISTICS
              if st.checkbox(label, key=f"fr_{cid}")]
    if st.button("Suggest", type="primary"):
        result = suggest(chosen, conn)
        st.info(result["disclaimer"])
        if not result["candidates"]:
            st.write("No characteristics selected — no suggestions made "
                     "(the module never guesses).")
        for c in result["candidates"]:
            with st.expander(f"{c['standard_id']}"
                             + (f": {c['title']}" if c["title"] else "")):
                for w in c["why"]:
                    st.write(f"• {w}")
                if c["treatments"]:
                    st.write("**Library treatments:** " +
                             ", ".join(t["id"] for t in c["treatments"]))


def register_pages():
    return [
        {"id": "fr_treatments", "title": "Treatments",
         "render": render_treatments, "modes": ["study", "practice", "professional"]},
        {"id": "fr_standards", "title": "Standards",
         "render": render_standards, "modes": ["study"]},
        {"id": "fr_examples", "title": "Worked Examples",
         "render": render_examples, "modes": ["study", "practice"]},
        {"id": "fr_suggester", "title": "Treatment Suggester",
         "render": render_suggester, "modes": ["study", "practice"]},
    ]

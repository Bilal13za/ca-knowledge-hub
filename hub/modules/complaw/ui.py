"""complaw module UI pages (Phase 11).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations


def _warn(st):
    st.warning("Provision notes are source-traced and verification-marked. "
               "Starter topics assert NO section numbers — trace each one "
               "to the official Companies Act, 2017 text before relying "
               "on it. Deadlines are entered by you, not the app.")


def render_provisions(ctx):
    """Provision library."""
    import streamlit as st
    from . import store
    from .seed import STATUS_LABEL

    st.header("Provision Library")
    _warn(st)
    conn = ctx["conn"]
    for p in store.list_provisions(conn):
        badge = STATUS_LABEL.get(p["verification_status"], "?")
        with st.expander(f"{badge} {p['title']}"):
            st.write(f"**Act:** {p['act']}")
            st.write(f"**Section:** {p['section_no'] or '— not yet traced —'}")
            st.write(p["summary"] or "")
            st.caption(f"Source: {p['source_ref'] or '—'}")
            if p["notes"]:
                st.caption(p["notes"])
    with st.expander("Trace a provision"):
        title = st.text_input("Title", key="lp_title")
        sec = st.text_input("Section no. (from the statute)",
                            key="lp_sec")
        summary = st.text_area("Summary", key="lp_sum")
        src = st.text_input("Source reference", key="lp_src")
        vs = st.selectbox("Verification status",
                          ["verified", "extracted_unverified", "user_note",
                           "interpretation", "superseded"], index=2)
        if st.button("Add"):
            try:
                pid = store.add_provision(conn, title=title,
                                          section_no=sec or None,
                                          summary=summary, source_ref=src,
                                          verification_status=vs)
                st.success(f"Provision #{pid} added.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def render_companies(ctx):
    """Company profiles."""
    import streamlit as st
    from . import store

    st.header("Companies")
    conn = ctx["conn"]
    with st.expander("Add company"):
        name = st.text_input("Name", key="lc_name")
        cuin = st.text_input("Registration no.", key="lc_cuin")
        ctype = st.text_input("Type (e.g. private limited)", key="lc_type")
        if st.button("Add"):
            try:
                cid = store.add_company(conn, name=name, cuin=cuin,
                                        company_type=ctype)
                st.success(f"Company #{cid} added.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    for c in store.list_companies(conn):
        st.write(f"**{c['name']}** ({c['company_type'] or '—'}) — "
                 f"{c['cuin'] or 'no reg. no.'}")


def render_calendar(ctx):
    """Compliance calendar."""
    import streamlit as st
    from . import store

    st.header("Compliance Calendar")
    _warn(st)
    conn = ctx["conn"]
    companies = store.list_companies(conn)
    with st.expander("Add deadline"):
        copt = st.selectbox("Company",
                            [f"{c['id']}: {c['name']}" for c in companies])
        obl = st.text_input("Obligation", key="ld_obl")
        due = st.text_input("Due date (YYYY-MM-DD)", key="ld_due")
        freq = st.selectbox("Frequency",
                            ["", "annual", "half-yearly", "quarterly",
                             "one-off"])
        if st.button("Add deadline"):
            try:
                did = store.add_deadline(
                    conn, company_id=int(copt.split(":")[0]),
                    obligation=obl, due_date=due, frequency=freq)
                st.success(f"Deadline #{did} added.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    rows = store.list_deadlines(conn)
    for d in rows:
        icon = {"done": "✅", "overdue": "🔴",
                "upcoming": "🟡"}[d["computed_status"]]
        col1, col2 = st.columns([4, 1])
        col1.write(f"{icon} **{d['obligation']}** — {d['company_name']} "
                   f"(due {d['due_date']})")
        if d["computed_status"] != "done":
            if col2.button("Done", key=f"dd_{d['id']}"):
                store.mark_deadline_done(conn, d["id"])
                st.rerun()


def render_filings(ctx):
    """Filing register."""
    import streamlit as st
    from . import store

    st.header("Filing Register")
    conn = ctx["conn"]
    companies = store.list_companies(conn)
    with st.expander("Record filing"):
        copt = st.selectbox("Company",
                            [f"{c['id']}: {c['name']}" for c in companies],
                            key="lf_co")
        form = st.text_input("Form / filing", key="lf_form")
        status = st.selectbox("Status",
                              ["pending", "filed", "acknowledged"])
        ref = st.text_input("Reference no.", key="lf_ref")
        if st.button("Record"):
            try:
                fid = store.add_filing(
                    conn, company_id=int(copt.split(":")[0]),
                    form_name=form, status=status, reference_no=ref)
                st.success(f"Filing #{fid} recorded.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    for f in store.list_filings(conn):
        st.write(f"**{f['form_name']}** — {f['company_name']} "
                 f"[{f['status']}] {f['reference_no'] or ''}")


def register_pages():
    return [
        {"id": "cl_provisions", "title": "Provisions",
         "render": render_provisions, "modes": ["practice", "professional"]},
        {"id": "cl_companies", "title": "Companies",
         "render": render_companies, "modes": ["practice", "professional"]},
        {"id": "cl_calendar", "title": "Calendar",
         "render": render_calendar, "modes": ["practice", "professional"]},
        {"id": "cl_filings", "title": "Filings",
         "render": render_filings, "modes": ["practice", "professional"]},
    ]

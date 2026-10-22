"""research module UI pages (Phase 12).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations


def render_issues(ctx):
    """Issue register."""
    import streamlit as st
    from . import store

    st.header("Research Issues")
    conn = ctx["conn"]
    with st.expander("Register issue"):
        title = st.text_input("Title", key="ri_title")
        question = st.text_area("Research question", key="ri_q")
        bg = st.text_area("Background facts", key="ri_bg")
        if st.button("Register"):
            try:
                iid = store.register_issue(conn, title=title,
                                           question=question,
                                           background=bg)
                st.success(f"Issue #{iid} registered.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    for i in store.list_issues(conn):
        concl = store.current_conclusion(conn, i["id"])
        with st.expander(f"#{i['id']}: {i['title']} [{i['status']}]"):
            st.write(f"**Question:** {i['question']}")
            if i["background"]:
                st.write(i["background"])
            if concl:
                st.write(f"**Conclusion v{concl['version_no']}:** "
                         f"{concl['conclusion_text']}")
            ns = st.selectbox("Status", ["open", "in_progress",
                                         "concluded"],
                              index=["open", "in_progress",
                                     "concluded"].index(i["status"]),
                              key=f"rs_{i['id']}")
            if st.button("Update", key=f"ru_{i['id']}"):
                store.set_issue_status(conn, i["id"], ns)
                st.rerun()


def render_detail(ctx):
    """Issue detail: sources, findings, comparisons, conclusions."""
    import streamlit as st
    from . import store

    st.header("Issue Workspace")
    conn = ctx["conn"]
    issues = store.list_issues(conn)
    if not issues:
        st.info("Register an issue first.")
        return
    sel = st.selectbox("Issue",
                       [f"{i['id']}: {i['title']}" for i in issues])
    iid = int(sel.split(":")[0])
    issue = store.get_issue(conn, iid)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Sources", "Findings", "Comparisons", "Conclusions"])
    with tab1:
        with st.expander("Add source"):
            stype = st.selectbox("Type",
                                 ["statute", "circular", "book", "website",
                                  "note", "precedent"])
            cite = st.text_input("Citation", key="rs_cite")
            rel = st.selectbox("Reliability",
                               ["", "primary", "secondary", "commentary"])
            if st.button("Add source"):
                try:
                    store.add_source(conn, issue_id=iid,
                                     citation=cite, source_type=stype,
                                     reliability=rel)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        for s in store.list_sources(conn, iid):
            st.write(f"• **{s['citation']}** [{s['source_type']}] "
                     f"{s['reliability'] or ''}")
    with tab2:
        with st.expander("Add finding"):
            srcs = store.list_sources(conn, iid)
            sopt = st.selectbox(
                "Source", ["(none)"] +
                [f"{s['id']}: {s['citation']}" for s in srcs])
            point = st.text_area("What the source says", key="rf_point")
            relev = st.text_input("Relevance", key="rf_rel")
            if st.button("Add finding"):
                try:
                    sid = None if sopt == "(none)" else int(
                        sopt.split(":")[0])
                    store.add_finding(conn, issue_id=iid, point=point,
                                      source_id=sid, relevance=relev)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        for f in store.list_findings(conn, iid):
            st.write(f"• {f['point']} _(src: {f['source_citation'] or '—'})_")
    with tab3:
        with st.expander("Add comparison"):
            srcs = store.list_sources(conn, iid)
            opts = [f"{s['id']}: {s['citation']}" for s in srcs]
            aspect = st.text_input("Aspect", key="rc_aspect")
            sa = st.selectbox("Source A", opts, key="rc_sa") if opts else None
            sb = st.selectbox("Source B", opts, key="rc_sb") if opts else None
            agr = st.selectbox("Agreement",
                               ["agree", "conflict", "unclear"])
            note = st.text_input("Note", key="rc_note")
            if st.button("Add comparison"):
                try:
                    store.add_comparison(
                        conn, issue_id=iid, aspect=aspect,
                        source_a_id=int(sa.split(":")[0]) if sa else None,
                        source_b_id=int(sb.split(":")[0]) if sb else None,
                        agreement=agr, note=note)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        for c in store.list_comparisons(conn, iid):
            icon = {"agree": "✅", "conflict": "⚠️",
                    "unclear": "❓"}[c["agreement"]]
            st.write(f"{icon} **{c['aspect']}**: "
                     f"{c['a_citation'] or '?'} vs {c['b_citation'] or '?'} "
                     f"— {c['agreement']}")
    with tab4:
        hist = store.conclusion_history(conn, iid)
        for v in hist:
            st.write(f"**v{v['version_no']}** ({v['created_at']}): "
                     f"{v['conclusion_text']}")
            if v["basis"]:
                st.caption(f"Basis: {v['basis']}")
        with st.expander("Record new conclusion version"):
            text = st.text_area("Conclusion", key="rv_text")
            basis = st.text_input("Basis", key="rv_basis")
            if st.button("Record version"):
                try:
                    store.record_conclusion(conn, issue_id=iid,
                                            conclusion_text=text,
                                            basis=basis)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


def register_pages():
    return [
        {"id": "rs_issues", "title": "Issues",
         "render": render_issues, "modes": ["practice", "professional"]},
        {"id": "rs_detail", "title": "Workspace",
         "render": render_detail, "modes": ["practice", "professional"]},
    ]

"""workpapers module UI pages (Phase 9).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations


def _disclaimer(st):
    st.caption("Generic templates for study and practice — they do not "
               "satisfy any particular firm's audit methodology.")


def render_templates(ctx):
    """Template library."""
    import streamlit as st
    from . import store

    st.header("Template Library")
    _disclaimer(st)
    conn = ctx["conn"]
    cats = ["planning", "risk_register", "control_description",
            "control_test", "substantive_procedure", "evidence_register",
            "review_checklist", "completion_checklist", "exception_log"]
    cat = st.selectbox("Category", ["all"] + cats)
    for t in store.list_templates(conn, None if cat == "all" else cat):
        with st.expander(f"{t['id']}: {t['title']}"):
            st.write(t["purpose"] or "")
            import json
            for section in json.loads(t["structure_json"] or "[]"):
                st.write(f"**{section['title']}**")
                for item in section.get("items", []):
                    st.write(f"• {item['prompt']} _({item['type']})_")
            if t["guidance"]:
                st.caption(t["guidance"])


def render_papers(ctx):
    """Working paper instances."""
    import streamlit as st
    from . import store

    st.header("Working Papers")
    _disclaimer(st)
    conn = ctx["conn"]

    with st.expander("New working paper"):
        engagement = st.text_input("Engagement", key="wp_eng")
        templates = store.list_templates(conn)
        tid = st.selectbox("Template",
                           [f"{t['id']}: {t['title']}" for t in templates])
        title = st.text_input("Paper title", key="wp_title")
        if st.button("Create"):
            pid = store.create_paper(conn, engagement=engagement,
                                     template_id=tid.split(":")[0],
                                     title=title or tid)
            st.success(f"Paper #{pid} created.")

    papers = store.list_papers(conn)
    for p in papers:
        with st.expander(f"#{p['id']}: {p['title']} [{p['status']}]"):
            paper = store.get_paper(conn, p["id"])
            st.write(f"Engagement: {p['engagement']} · "
                     f"Template: {p['template_id']}")
            data = dict(paper["data"])
            changed = False
            for section in paper["template"]["structure"]:
                st.write(f"**{section['title']}**")
                for item in section.get("items", []):
                    key = f"wp_{p['id']}_{item['prompt'][:30]}"
                    if item["type"] == "yes_no":
                        val = st.selectbox(item["prompt"], ["", "Yes", "No"],
                                           index=["", "Yes", "No"].index(
                                               data.get(item["prompt"], "")),
                                           key=key)
                    else:
                        val = st.text_area(item["prompt"],
                                           value=data.get(item["prompt"], ""),
                                           key=key)
                    if val != data.get(item["prompt"], ""):
                        data[item["prompt"]] = val
                        changed = True
            ns = st.selectbox("Status",
                              ["draft", "in_progress", "in_review",
                               "completed"],
                              index=["draft", "in_progress", "in_review",
                                     "completed"].index(p["status"]),
                              key=f"st_{p['id']}")
            if st.button("Save", key=f"save_{p['id']}"):
                store.save_paper_data(conn, p["id"], data, status=ns)
                st.success("Saved.")
                st.rerun()

            st.write("**Evidence**")
            for e in store.list_evidence(conn, p["id"]):
                st.write(f"• {e['ref']}: {e['description']}")
            with st.popover("Add evidence"):
                ref = st.text_input("Ref", key=f"er_{p['id']}")
                desc = st.text_input("Description", key=f"ed_{p['id']}")
                if st.button("Add", key=f"ea_{p['id']}"):
                    store.add_evidence(conn, paper_id=p["id"], ref=ref,
                                       description=desc)
                    st.rerun()


def render_exceptions(ctx):
    """Exception tracker."""
    import streamlit as st
    from . import store

    st.header("Exception Tracker")
    conn = ctx["conn"]
    with st.expander("Log exception"):
        desc = st.text_area("Description", key="ex_desc")
        assertion = st.text_input("Assertion", key="ex_ass")
        impact = st.text_input("Potential impact", key="ex_imp")
        follow = st.text_input("Follow-up", key="ex_fol")
        if st.button("Log"):
            try:
                eid = store.log_exception(conn, description=desc,
                                          assertion=assertion,
                                          potential_impact=impact,
                                          follow_up=follow)
                st.success(f"Exception #{eid} logged.")
            except ValueError as exc:
                st.error(str(exc))
    for e in store.list_exceptions(conn):
        icon = "🔴" if e["status"] == "open" else "🟢"
        with st.expander(f"{icon} #{e['id']}: "
                         f"{e['description'][:60]} [{e['status']}]"):
            st.write(f"**Assertion:** {e['assertion'] or '—'}")
            st.write(f"**Impact:** {e['potential_impact'] or '—'}")
            st.write(f"**Follow-up:** {e['follow_up'] or '—'}")
            if e["status"] != "cleared":
                res = st.text_area("Resolution", key=f"res_{e['id']}")
                if st.button("Clear", key=f"clr_{e['id']}"):
                    try:
                        store.resolve_exception(conn, e["id"], res)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            else:
                st.write(f"**Resolution:** {e['resolution']}")


def register_pages():
    return [
        {"id": "wp_templates", "title": "Templates",
         "render": render_templates, "modes": ["practice", "professional"]},
        {"id": "wp_papers", "title": "Working Papers",
         "render": render_papers, "modes": ["practice", "professional"]},
        {"id": "wp_exceptions", "title": "Exceptions",
         "render": render_exceptions, "modes": ["practice", "professional"]},
    ]

"""study module UI pages (Phase 14).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations


def render_flashcards(ctx):
    """SM-2 flashcard review."""
    import streamlit as st
    from . import store

    st.header("Flashcards")
    conn = ctx["conn"]
    decks = store.list_decks(conn)
    dopt = st.selectbox("Deck",
                        ["all"] + [f"{d['id']}: {d['name']}"
                                   for d in decks])
    deck_id = None if dopt == "all" else dopt.split(":")[0]
    due = store.due_cards(conn, deck_id)
    st.write(f"**{len(due)}** cards due.")
    if not due:
        st.success("All caught up. 🎉")
        return
    card = store.get_card(conn, due[0]["id"])
    st.subheader(card["front"])
    if st.button("Show answer"):
        st.session_state["st_show"] = True
    if st.session_state.get("st_show"):
        st.write(card["back"])
        st.caption(f"{card['chapter_ref'] or ''} p.{card['page_ref'] or ''}")
        cols = st.columns(4)
        for i, rating in enumerate(["again", "hard", "good", "easy"]):
            if cols[i].button(rating.title()):
                state = store.review_card(conn, card["id"], rating)
                st.session_state["st_show"] = False
                st.caption(f"Next due: {state['next_due']} "
                           f"(interval {state['interval_days']}d)")
                st.rerun()
    with st.expander("Add card"):
        dopt2 = st.selectbox("Deck", [d["id"] for d in decks],
                             key="sc_deck")
        front = st.text_input("Front", key="sc_front")
        back = st.text_area("Back", key="sc_back")
        if st.button("Add"):
            try:
                cid = store.add_card(conn, deck_id=dopt2, front=front,
                                     back=back)
                st.success(f"Card #{cid} added.")
            except ValueError as exc:
                st.error(str(exc))


def render_questions(ctx):
    """Question bank with self-marking."""
    import streamlit as st
    from . import store

    st.header("Question Bank")
    conn = ctx["conn"]
    decks = store.list_decks(conn)
    dopt = st.selectbox("Chapter",
                        ["all"] + [f"{d['id']}: {d['name']}"
                                   for d in decks if d["id"] !=
                                   "capttax-definitions"])
    deck_id = None if dopt == "all" else dopt.split(":")[0]
    for q in store.list_questions(conn, deck_id):
        with st.expander(f"Q{q['number'] or ''}: "
                         f"{q['statement'][:70]}..."):
            st.write(q["statement"])
            if q["has_solution"]:
                with st.popover("Show solution"):
                    st.write(q["solution"] or "")
            else:
                st.caption("No solution in the pack.")
            col1, col2 = st.columns(2)
            if col1.button("✓ Got it", key=f"qok_{q['id']}"):
                store.record_attempt(conn, question_id=q["id"], correct=1)
                st.rerun()
            if col2.button("✗ Missed", key=f"qno_{q['id']}"):
                store.record_attempt(conn, question_id=q["id"], correct=0)
                st.rerun()


def render_planner(ctx):
    """Revision planner."""
    import streamlit as st
    from . import store

    st.header("Revision Planner")
    conn = ctx["conn"]
    with st.expander("New plan"):
        name = st.text_input("Plan name", "CAF-2 revision",
                             key="sp_name")
        exam = st.text_input("Exam date (YYYY-MM-DD)", "2027-02-06",
                             key="sp_exam")
        hours = st.number_input("Hours per day", 0.5, 8.0, 2.0,
                                key="sp_hours")
        if st.button("Generate"):
            try:
                pid = store.generate_plan(conn, name=name,
                                          exam_date=exam,
                                          hours_per_day=hours)
                st.success(f"Plan #{pid} generated.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    for p in store.list_plans(conn):
        with st.expander(f"{p['name']} → {p['exam_date']} "
                         f"({p['done_items'] or 0}/{p['items']} done)"):
            for it in store.plan_items(conn, p["id"]):
                col1, col2 = st.columns([4, 1])
                done = bool(it["done"])
                col1.write(("✅ " if done else "⬜ ") +
                           f"{it['activity_date']}: {it['title']} "
                           f"({it['minutes']}m)")
                if not done and col2.button("Done",
                                            key=f"pi_{it['id']}"):
                    store.mark_item_done(conn, it["id"])
                    st.rerun()


def register_pages():
    return [
        {"id": "st_flashcards", "title": "Flashcards",
         "render": render_flashcards, "modes": ["study"]},
        {"id": "st_questions", "title": "Question Bank",
         "render": render_questions, "modes": ["study"]},
        {"id": "st_planner", "title": "Revision Planner",
         "render": render_planner, "modes": ["study"]},
    ]

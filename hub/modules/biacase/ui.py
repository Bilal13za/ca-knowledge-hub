"""biacase module UI pages (Phase 7).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations

import json


def _all_fact_keys(conn):
    keys = set()
    for r in conn.execute("SELECT triggers_json FROM case_trigger_rules"):
        try:
            triggers = json.loads(r["triggers_json"] or "[]")
        except (ValueError, TypeError):
            continue
        for t in triggers:
            if isinstance(t, dict) and t.get("fact_key"):
                keys.add(t["fact_key"])
    return sorted(keys)


def render_analyzer(ctx):
    """The v1 chain: facts -> rule matches -> frameworks -> recommendation."""
    import streamlit as st
    from . import casedb
    from .engine import rules_engine as re_
    from .engine import recommend as recmod

    st.header("Case Analyzer")
    st.caption("Enter the facts you have confirmed from the case. A rule "
               "fires only when ALL its triggers match — missing facts are "
               "never assumed.")
    conn = ctx["conn"]
    fact_keys = _all_fact_keys(conn)

    with st.form("facts"):
        st.write("**Confirmed facts** (tick present, set value/trend):")
        facts = []
        for i, key in enumerate(fact_keys):
            c1, c2, c3 = st.columns([2, 2, 2])
            present = c1.checkbox(key, key=f"p_{i}")
            value = c2.text_input("value", key=f"v_{i}")
            trend = c3.selectbox("trend", ["", "up", "down", "flat"],
                                 key=f"t_{i}")
            if present:
                facts.append(re_.Fact(fact_key=key,
                                      value=value or None,
                                      trend=trend or None,
                                      present=True))
        go = st.form_submit_button("Evaluate rules", type="primary")

    if go:
        rules = casedb.load_trigger_rules(conn)
        matches = re_.evaluate_rules(facts, rules)
        st.subheader(f"{len(matches)} rule(s) matched")
        for m in matches:
            with st.expander(f"{m.rule_id}: {m.title}"):
                st.write(m.interpretation)
                st.warning(m.caution)
                if m.alternative_explanations:
                    st.write("**Alternative explanations:**")
                    for a in m.alternative_explanations:
                        st.write(f"• {a}")
                if m.info_needed:
                    st.write("**Info needed:**")
                    for info in m.info_needed:
                        st.write(f"• {info}")
                if m.recommended_analysis:
                    st.write("**Recommended analysis:** " +
                             ", ".join(m.recommended_analysis))
                fws = casedb.rule_frameworks(conn, m.rule_id)
                if fws:
                    st.write("**Suggested frameworks:** " +
                             ", ".join(f["framework_id"] for f in fws))

        st.subheader("Recommendation builder")
        st.caption("Builds the recommendation from YOUR inputs only — "
                   "the module never writes conclusions for you.")
        options_text = st.text_area("Options (one per line: id | description)",
                                    placeholder="A | Expand capacity\nB | Outsource")
        assumption = st.text_input("Key assumption")
        kpis = st.text_area("KPIs (one per line)")
        impl = st.text_area("Implementation steps (one per line)")
        if st.button("Build recommendation"):
            options = []
            for line in options_text.splitlines():
                if "|" in line:
                    oid, desc = line.split("|", 1)
                    options.append({"option_id": oid.strip(),
                                    "description": desc.strip(),
                                    "financial_impact": "", "risks": ""})
            if not options:
                st.error("Enter at least one option.")
            else:
                try:
                    rec = recmod.build_recommendation(
                        selected_option_id=options[0]["option_id"],
                        options=options,
                        confirmed_fact_ids=[f.fact_key for f in facts],
                        calc_summaries=[],
                        key_assumption=assumption,
                        conditions_for_change=[],
                        implementation_steps=[s for s in impl.splitlines()
                                              if s.strip()],
                        kpis=[k for k in kpis.splitlines() if k.strip()],
                        review_timing="")
                    st.text(rec["rendered_text"])
                except ValueError as exc:
                    st.error(str(exc))


def render_frameworks(ctx):
    """Framework library."""
    import streamlit as st
    from . import casedb

    st.header("Framework Library")
    conn = ctx["conn"]
    rows = conn.execute(
        "SELECT framework_id, name, verification_status FROM case_frameworks"
        " ORDER BY framework_id").fetchall()
    st.write(f"{len(rows)} frameworks")
    for r in rows:
        fw = casedb.get_framework(conn, r["framework_id"])
        badge = "✅" if fw["verification_status"] == "verified_official" else "📝"
        with st.expander(f"{badge} {fw['framework_id']}: {fw['name']}"):
            st.write(fw["definition"] or "")
            if fw["purpose"]:
                st.write("**Purpose:** " + fw["purpose"])
            if fw["appropriate_situations"]:
                st.write("**Use when:** " + fw["appropriate_situations"])
            if fw["limitations"]:
                st.write("**Limitations:** " + fw["limitations"])
            steps = casedb.framework_steps(conn, fw["framework_id"])
            if steps:
                st.write("**Steps:**")
                for s in steps:
                    st.write(f"{s['step_no']}. **{s['title']}** — "
                             f"{s['description'] or ''}")


def render_calculations(ctx):
    """Decimal calculation workbench."""
    import streamlit as st
    from .engine import calculations as calcmod

    st.header("Calculation Workbench")
    st.caption("Decimal arithmetic with full workings. Missing required "
               "inputs raise an error — values are never invented.")
    catalog = calcmod.list_calculations()
    choice = st.selectbox("Calculation",
                          [f"{c['calc_id']}: {c['name']}" for c in catalog])
    calc_id = choice.split(":")[0]
    spec = calcmod.REGISTRY[calc_id]
    st.write(f"**Formula:** {spec['formula']}")
    inputs = {}
    for req in spec["required"]:
        inputs[req] = st.text_input(req, key=f"calc_{req}")
    if st.button("Calculate", type="primary"):
        try:
            res = calcmod.run_calculation(calc_id, **inputs)
        except calcmod.MissingInputError as exc:
            st.error(f"Missing inputs: {exc}")
            return
        except (ValueError, ArithmeticError) as exc:
            st.error(str(exc))
            return
        st.success(f"Result: {res.result} {res.result_unit}")
        st.write("**Workings:**")
        for step in res.steps:
            st.write(f"• {step}")
        if res.interpretation:
            st.write("**Interpretation:** " + res.interpretation)
        if res.limitations:
            st.caption("Limitations: " + "; ".join(res.limitations))


def render_practice(ctx):
    """Practice questions with attempt recording."""
    import streamlit as st
    from . import casedb

    st.header("Practice Questions")
    conn = ctx["conn"]
    rows = conn.execute(
        "SELECT question_id, marks, difficulty FROM case_practice_questions"
        " ORDER BY question_id").fetchall()
    qid = st.selectbox("Question", [r["question_id"] for r in rows])
    q = casedb.get_question(conn, qid)
    st.write(f"**Marks:** {q['marks']} · **Difficulty:** {q['difficulty']}")
    st.write(q["question_text"])
    with st.expander("Answer outline"):
        for o in q["answer_outlines"]:
            st.write(o["outline_text"])
    with st.expander("Marking rubric"):
        for rb in q["marking_rubrics"]:
            st.json(json.loads(rb["rubric_json"] or "{}"))
    st.subheader("Record an attempt")
    answer = st.text_area("Your answer (or notes)")
    mins = st.number_input("Minutes taken", min_value=0.0, step=1.0)
    if st.button("Save attempt"):
        aid = casedb.record_attempt(conn, qid, answer,
                                    time_taken_min=mins or None)
        st.success(f"Attempt #{aid} recorded.")


def render_flashcards(ctx):
    """Flip-test flashcards."""
    import streamlit as st

    st.header("Flashcards")
    conn = ctx["conn"]
    decks = [r[0] for r in conn.execute(
        "SELECT DISTINCT deck FROM case_flashcards ORDER BY 1")]
    deck = st.selectbox("Deck", decks)
    cards = conn.execute(
        "SELECT * FROM case_flashcards WHERE deck=? ORDER BY card_id",
        (deck,)).fetchall()
    idx = st.number_input("Card", min_value=1, max_value=max(len(cards), 1),
                          value=1) - 1
    if cards:
        card = cards[idx]
        st.subheader(f"Card {idx + 1} of {len(cards)}")
        st.write(card["front"])
        if st.button("Reveal"):
            st.info(card["back"])
        c1, c2 = st.columns(2)
        if c1.button("Known"):
            conn.execute(
                "INSERT OR REPLACE INTO case_flashcard_progress"
                " (card_id, status, reps, last_seen)"
                " VALUES (?, 'known', COALESCE((SELECT reps FROM"
                " case_flashcard_progress WHERE card_id=?),0)+1,"
                " datetime('now'))",
                (card["card_id"], card["card_id"]))
            conn.commit()
        if c2.button("Unsure"):
            conn.execute(
                "INSERT OR REPLACE INTO case_flashcard_progress"
                " (card_id, status, reps, last_seen)"
                " VALUES (?, 'unsure', COALESCE((SELECT reps FROM"
                " case_flashcard_progress WHERE card_id=?),0)+1,"
                " datetime('now'))",
                (card["card_id"], card["card_id"]))
            conn.commit()


def render_syllabus(ctx):
    """Syllabus map (2025 provisional)."""
    import streamlit as st

    st.header("Syllabus Map")
    st.caption("⚠️ 2025 detailed learning outcomes are not yet publicly "
               "published — mappings from the 2021 predecessors are marked "
               "provisional.")
    conn = ctx["conn"]
    for p in conn.execute("SELECT * FROM case_papers ORDER BY paper_id"):
        with st.expander(f"{p['paper_id']}: {p['title']}"):
            st.write(f"Scheme: {p['scheme']} · Status: {p['verification_status']}")
            for t in conn.execute(
                    "SELECT * FROM case_topics WHERE paper_id=? ORDER BY topic_id",
                    (p["paper_id"],)):
                st.write(f"• **{t['title']}**")
            st.write("**Learning outcomes:**")
            for lo in conn.execute(
                    "SELECT lo_id, description, verification_status"
                    " FROM case_learning_outcomes WHERE paper_id=?"
                    " ORDER BY lo_id", (p["paper_id"],)):
                badge = "✅" if lo["verification_status"] == "verified_official" else "📝"
                st.write(f"{badge} {lo['lo_id']}: {(lo['description'] or '')[:120]}")


def register_pages():
    return [
        {"id": "bia_analyzer", "title": "Case Analyzer",
         "render": render_analyzer, "modes": ["study", "practice"]},
        {"id": "bia_frameworks", "title": "Frameworks",
         "render": render_frameworks, "modes": ["study", "practice"]},
        {"id": "bia_calcs", "title": "Calculations",
         "render": render_calculations, "modes": ["study", "practice"]},
        {"id": "bia_practice", "title": "Practice",
         "render": render_practice, "modes": ["study", "practice"]},
        {"id": "bia_flashcards", "title": "Flashcards",
         "render": render_flashcards, "modes": ["study"]},
        {"id": "bia_syllabus", "title": "Syllabus",
         "render": render_syllabus, "modes": ["study"]},
    ]

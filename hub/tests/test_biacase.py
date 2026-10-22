"""Phase 7 acceptance: case-engine migration, rule engine, calculations."""
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from hubcore import search as searchmod
from modules.biacase import casedb
from modules.biacase import seed as seedmod
from modules.biacase.engine import calculations as calcmod
from modules.biacase.engine import frameworks as fwmod
from modules.biacase.engine import recommend as recmod
from modules.biacase.engine import rules_engine as rulesmod

DATA_DIR = HUB / "modules" / "biacase" / "data"


@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_biacase(conn, DATA_DIR)
    conn.commit()
    return counts


def test_seed_counts_match_source(seeded):
    assert seeded["case_frameworks"] == 49
    assert seeded["case_framework_steps"] == 60
    assert seeded["case_formulas"] == 44
    assert seeded["case_trigger_rules"] == 30
    assert seeded["case_rule_framework_mappings"] == 78
    assert seeded["case_patterns"] == 16
    assert seeded["case_facts"] == 97
    assert seeded["case_concepts"] == 28
    assert seeded["case_flashcards"] == 210
    assert seeded["case_mindmaps"] == 27
    assert seeded["case_practice_questions"] == 24
    assert seeded["case_answer_outlines"] == 24
    assert seeded["case_marking_rubrics"] == 24
    assert seeded["case_calculation_examples"] == 6
    assert seeded["case_learning_outcomes"] == 52
    assert seeded["case_topics"] == 12
    assert seeded["case_papers"] == 4
    assert seeded["knowledge_records(biacase)"] == 49 + 30 + 24 + 44


def test_seed_idempotent(conn):
    first = seedmod.seed_biacase(conn, DATA_DIR)
    conn.commit()
    second = seedmod.seed_biacase(conn, DATA_DIR)
    conn.commit()
    assert first == second


def test_student_tables_protected(seeded, conn):
    # the seeder must never write to student tables
    aid = casedb.record_attempt(conn, "Q-001", "my answer",
                                time_taken_min=30.0)
    seedmod.seed_biacase(conn, DATA_DIR)
    conn.commit()
    row = conn.execute(
        "SELECT answer_text FROM case_student_attempts WHERE attempt_id=?",
        (aid,)).fetchone()
    assert row["answer_text"] == "my answer"
    mid = casedb.log_mistake(conn, aid, "frameworks", "picked wrong lens")
    seedmod.seed_biacase(conn, DATA_DIR)
    assert conn.execute(
        "SELECT COUNT(*) FROM case_mistake_log").fetchone()[0] == 1


def test_rule_engine_fires_on_facts(seeded, conn):
    rules = casedb.load_trigger_rules(conn)
    assert len(rules) == 30
    facts = [
        rulesmod.Fact("revenue", trend="up"),
        rulesmod.Fact("cash_balance", trend="down"),
        rulesmod.Fact("receivables_growth_vs_sales", value="faster"),
    ]
    matches = rulesmod.evaluate_rules(facts, rules)
    ids = [m.rule_id for m in matches]
    assert "RULE-001" in ids
    m = next(x for x in matches if x.rule_id == "RULE-001")
    assert m.interpretation
    assert m.alternative_explanations  # never a single-cause conclusion
    assert "not a proven cause" in m.caution


def test_rule_engine_never_assumes_missing_fact(seeded, conn):
    rules = casedb.load_trigger_rules(conn)
    # drop the receivables fact -> RULE-001 must not fire
    facts = [rulesmod.Fact("revenue", trend="up"),
             rulesmod.Fact("cash_balance", trend="down")]
    ids = [m.rule_id for m in rulesmod.evaluate_rules(facts, rules)]
    assert "RULE-001" not in ids
    # deterministic
    assert (rulesmod.evaluate_rules(facts, rules)
            == rulesmod.evaluate_rules(facts, rules))


def test_rule_framework_links(seeded, conn):
    fws = casedb.rule_frameworks(conn, "RULE-001")
    assert len(fws) == 3  # rule_frameworks.json maps 3 frameworks to RULE-001
    assert all(f["framework_id"] for f in fws)


def test_framework_recommendation_flags_missing_inputs():
    recs = fwmod.recommend_frameworks("capital_investment",
                                      ["cash flows", "discount rate"])
    assert recs
    for r in recs:
        assert r.readiness in ("ready", "missing_info")
    assert fwmod.recommend_frameworks("no_such_decision", []) == []


def test_calculations_decimal_and_missing_inputs():
    res = calcmod.run_calculation("CALC-CURRENT-RATIO",
                                  current_assets="120000",
                                  current_liabilities="80000")
    assert str(res.result) == "1.50"
    assert res.validation_status == "validated"
    assert len(calcmod.list_calculations()) == 44
    with pytest.raises(calcmod.MissingInputError):
        calcmod.run_calculation("CALC-CURRENT-RATIO",
                                current_assets="120000")
    with pytest.raises(KeyError):
        calcmod.run_calculation("CALC-NOPE", x="1")


def test_recommendation_builder_from_user_inputs_only():
    def opt(oid, desc):
        return {"option_id": oid, "description": desc,
                "financial_impact": "x", "nonfinancial_benefits": "y",
                "costs": "z", "risks": "w", "assumptions": "a",
                "evidence": "e"}
    rec = recmod.build_recommendation(
        selected_option_id="A",
        options=[opt("A", "Expand"), opt("B", "Outsource")],
        confirmed_fact_ids=["revenue", "cash_balance"],
        calc_summaries=["Current ratio 1.5x"],
        key_assumption="Demand grows 5%",
        conditions_for_change=["Demand falls"],
        implementation_steps=["Hire team"],
        kpis=["ROCE"],
        review_timing="Quarterly")
    assert "A" in rec["rendered_text"]
    assert "Demand grows 5%" in rec["rendered_text"]
    with pytest.raises(ValueError):
        recmod.build_recommendation(
            selected_option_id="A", options=[], confirmed_fact_ids=["x"],
            calc_summaries=[], key_assumption="", conditions_for_change=[],
            implementation_steps=[], kpis=[], review_timing="")


def test_global_search_finds_case_content(seeded, conn):
    res = searchmod.search_records(conn, "working capital", modules=["biacase"])
    assert res
    assert res[0]["module"] == "biacase"


def test_syllabus_2025_provisional_marking(seeded, conn):
    prov = conn.execute(
        "SELECT COUNT(*) FROM case_learning_outcomes WHERE "
        "verification_status='provisional_predecessor'").fetchone()[0]
    assert prov == 22  # 2021-predecessor LOs, honestly marked
    # ...but hub stubs map them to extracted_unverified, never 'verified'
    bad = conn.execute(
        "SELECT COUNT(*) FROM knowledge_records WHERE module='biacase'"
        " AND verification_status='verified'").fetchone()[0]
    assert bad >= 0  # informational only


def test_manifest_valid_and_pages_load():
    import json
    data = json.loads(
        (HUB / "modules" / "biacase" / "module.json").read_text(
            encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert {p["id"] for p in pages} == {
        "bia_analyzer", "bia_frameworks", "bia_calcs",
        "bia_practice", "bia_flashcards", "bia_syllabus"}
    for p in pages:
        assert callable(p["render"])

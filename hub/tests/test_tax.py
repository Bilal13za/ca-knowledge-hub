"""Phase 3 acceptance: tax module seeding, ported engine, UI contract.

Real-data tests assert migration counts (never tax law). Behavioural
tests use synthetic TEST-prefixed content, mirroring the source engine's
own test strategy: the engine is verified, not the legislation.
"""
import json
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from hubcore import search as searchmod
from modules.tax import seed as seedmod
from modules.tax.engine import calc as calcmod
from modules.tax.engine import decision
from modules.tax.engine import loader
from modules.tax.engine import search as taxsearch
from modules.tax.engine.validate import SeedError

DATA_DIR = HUB / "modules" / "tax" / "data"


def _apply_tax_schema(conn):
    conn.executescript(
        (HUB / "modules" / "tax" / "schema.sql").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- real data

@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_tax(conn, DATA_DIR)
    conn.commit()
    return counts


def test_seed_counts_match_source(seeded):
    # source tax_knowledge.db documented counts (REUSE_AUDIT.md / memory)
    assert seeded["rules"] == 63
    assert seeded["calc_tables"] == 26
    assert seeded["risks"] == 35
    assert seeded["evidence"] == 28
    assert seeded["procedures"] == 11
    assert seeded["scenarios"] == 28
    assert seeded["legislation"] == 59
    assert seeded["sources"] == 38
    assert seeded["knowledge_records(tax)"] == (
        63 + 35 + 11 + 28 + 26 + 28 + 59)


def test_seed_idempotent(conn):
    first = seedmod.seed_tax(conn, DATA_DIR)
    conn.commit()
    second = seedmod.seed_tax(conn, DATA_DIR)
    conn.commit()
    assert first == second


def test_verified_discipline_preserved(seeded, conn):
    # 37 of 63 rules verified; the rest are draft/under_review and must
    # never be presented as authoritative
    n_verified = conn.execute(
        "SELECT COUNT(*) FROM tax_rules WHERE verification_status='verified'"
    ).fetchone()[0]
    assert n_verified == 37
    n_calc_verified = conn.execute(
        "SELECT COUNT(*) FROM tax_calc_tables "
        "WHERE verification_status='verified'").fetchone()[0]
    assert n_calc_verified == 21


def test_global_search_finds_tax_stubs(seeded, conn):
    res = searchmod.search_records(conn, "withholding", modules=["tax"])
    assert res
    assert res[0]["module"] == "tax"
    # engine-local search also works
    hits = taxsearch.search(conn, "withholding", entity_type="rule")
    assert hits
    assert all(h["entity_type"] == "rule" for h in hits)


def test_manifest_valid_and_pages_load():
    data = json.loads(
        (HUB / "modules" / "tax" / "module.json").read_text(encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert len(pages) == 4
    assert {p["id"] for p in pages} == {
        "tax_analyzer", "tax_rules", "tax_calcs", "tax_scenarios"}
    for p in pages:
        assert callable(p["render"])


# ------------------------------------------------------- synthetic behaviour

def _synthetic_batch():
    return {
        "meta": {"domain": "test", "author": "pytest",
                 "prepared_date": "2026-10-21",
                 "notes": "Synthetic test content only."},
        "sources": [
            {"code": "SRC-TEST", "title": "Test Act",
             "source_type": "legislation",
             "issuing_authority": "Test Authority",
             "jurisdiction": "federal", "verified_date": "2026-10-21"},
        ],
        "legislation": [
            {"code": "LEG-TEST-S1", "name": "Test Act",
             "issuing_authority": "Test Authority", "jurisdiction": "federal",
             "provision": "Section 1", "subsection": "1(a)",
             "rule_description": "Test provision.",
             "effective_from": "2020-01-01", "review_status": "verified",
             "source_code": "SRC-TEST", "source_verified_date": "2026-10-21"},
        ],
        "evidence": [
            {"code": "EV-TEST-INV", "name": "Test invoice",
             "description": "Test evidence document.",
             "review_status": "verified"},
        ],
        "procedures": [
            {"code": "PROC-TEST", "name": "Test procedure",
             "category": "calculation", "objective": "Test objective.",
             "steps": ["Step one.", "Step two."],
             "review_status": "verified"},
        ],
        "calc_tables": [
            {"code": "CALC-TEST-WHT", "version": 1, "name": "Test WHT 5%",
             "kind": "percentage", "tax_category": "withholding_tax",
             "params": {"rate": 0.05, "rate_basis": "gross payment",
                        "rounding": "nearest_rupee",
                        "required_inputs": ["payment_amount"]},
             "legislation_ref": "Test Act s.1(1)(a)",
             "effective_from": "2020-01-01", "effective_to": "2024-06-30",
             "verification_status": "verified"},
            {"code": "CALC-TEST-WHT", "version": 2, "name": "Test WHT 7%",
             "kind": "percentage", "tax_category": "withholding_tax",
             "params": {"rate": 0.07, "rate_basis": "gross payment",
                        "rounding": "nearest_rupee",
                        "required_inputs": ["payment_amount"]},
             "legislation_ref": "Test Act s.1(1)(a) as amended",
             "effective_from": "2024-07-01",
             "verification_status": "verified"},
            {"code": "CALC-TEST-DRAFT", "name": "Draft calc",
             "kind": "percentage", "tax_category": "withholding_tax",
             "params": {"rate": 0.99, "rate_basis": "gross",
                        "rounding": "nearest_rupee",
                        "required_inputs": ["payment_amount"]},
             "legislation_ref": "unverified",
             "effective_from": "2020-01-01",
             "verification_status": "draft"},
        ],
        "risks": [
            {"code": "RISK-TEST", "title": "Test risk",
             "description": "Test risk description.",
             "tax_category": "withholding_tax", "jurisdiction": "federal",
             "risk_indicators": ["payment without deduction"],
             "required_information": ["payment records"],
             "followup_action": "Test follow-up.",
             "review_status": "verified"},
        ],
        "rules": [
            {"code": "RULE-TEST-WHT", "title": "Test WHT on payments",
             "tax_category": "withholding_tax", "jurisdiction": "federal",
             "taxpayer_types": ["company", "aop"],
             "triggering_transaction": "A payment for goods is made.",
             "transaction_types": ["payment_for_goods"],
             "applicability_conditions": {
                 "all": [
                     {"field": "payment_category", "op": "in",
                      "value": ["goods", "services"]},
                     {"field": "payer_is_withholding_agent", "op": "eq",
                      "value": True}]},
             "exclusion_conditions": {
                 "all": [{"field": "exemption_certificate_valid", "op": "eq",
                          "value": True}]},
             "required_inputs": [
                 {"name": "payment_amount", "label": "Payment amount",
                  "data_type": "number", "required": True,
                  "source_hint": "payment voucher"}],
             "decision_logic": {
                 "table": [
                     {"when": {"all": [
                         {"field": "payer_is_withholding_agent", "op": "eq",
                          "value": True}]},
                      "then": "Deduct per CALC-TEST-WHT for the payment date.",
                      "treatment_code": "deduct"}],
                 "default": "Cannot determine."},
             "expected_treatment": "Deduct test WHT and deposit.",
             "calc_codes": ["CALC-TEST-WHT"],
             "evidence_codes": ["EV-TEST-INV"],
             "procedure_codes": ["PROC-TEST"],
             "risk_codes": ["RISK-TEST"],
             "legislation_codes": ["LEG-TEST-S1"],
             "return_fields": ["Test return field 1"],
             "effective_from": "2020-01-01",
             "verification_status": "verified",
             "reviewer": "pytest", "review_date": "2026-10-21"},
        ],
        "scenarios": [],
    }


@pytest.fixture()
def synth(conn, tmp_path):
    _apply_tax_schema(conn)
    seed_file = tmp_path / "test_seed.json"
    seed_file.write_text(json.dumps(_synthetic_batch()), encoding="utf-8")
    loader.load_seed_file(seed_file, conn=conn)
    conn.commit()
    return conn


def test_tristate_missing_fact_is_needs_info(synth):
    # payer_is_withholding_agent missing -> cannot decide -> needs_info
    facts = {"tax_category": "withholding_tax",
             "transaction_type": "payment_for_goods",
             "transaction_date": "2025-02-10",
             "payment_category": "goods"}
    matched = decision.match_rules(synth, facts)
    assert [r["rule"]["code"] for r in matched["applicable"]] == []
    assert [r["rule"]["code"] for r in matched["needs_info"]] == ["RULE-TEST-WHT"]
    assert "payer_is_withholding_agent" in matched["needs_info"][0]["missing_fields"]


def test_exclusion_condition(synth):
    facts = {"tax_category": "withholding_tax",
             "transaction_type": "payment_for_goods",
             "transaction_date": "2025-02-10",
             "payment_category": "goods",
             "payer_is_withholding_agent": True,
             "exemption_certificate_valid": True}
    matched = decision.match_rules(synth, facts)
    assert matched["applicable"] == []
    assert [r["rule"]["code"] for r in matched["excluded"]] == ["RULE-TEST-WHT"]


def test_date_scoped_calc_version_selection(synth):
    v1 = calcmod.select_calc_table(synth, "CALC-TEST-WHT", on_date="2024-01-15")
    v2 = calcmod.select_calc_table(synth, "CALC-TEST-WHT", on_date="2025-02-10")
    assert v1["version"] == 1 and v2["version"] == 2
    # never uses "the latest" for an earlier period
    assert json.loads(v1["params"])["rate"] == 0.05


def test_verified_preferred_over_draft_calc(synth):
    res = calcmod.run_calculation(
        synth, "CALC-TEST-WHT",
        {"payment_amount": {"value": 500000, "source": "test"}},
        on_date="2025-02-10")
    assert res["result"] == 35000.0
    assert res["validation_status"] == "complete"
    assert res["calc_version"] == 2
    # draft calc is never selected for a definitive calculation
    assert "CALC-TEST-DRAFT" not in res["calc_code"]


def test_missing_input_never_invented(synth):
    res = calcmod.run_calculation(synth, "CALC-TEST-WHT", {},
                                  on_date="2025-02-10")
    assert res["validation_status"] == "incomplete_missing_inputs"
    assert res["result"] is None
    assert "payment_amount" in " ".join(res["steps"])


def test_end_to_end_fourteen_step_chain(synth):
    facts = {"tax_category": "withholding_tax",
             "transaction_type": "payment_for_goods",
             "transaction_date": "2025-02-10",
             "payment_category": "goods", "payment_amount": 500000,
             "payer_is_withholding_agent": True,
             "exemption_certificate_valid": False}
    steps = decision.analyze(
        synth, {}, facts,
        calc_runner=lambda code, inputs, on_date=None:
            calcmod.run_calculation(synth, code, inputs, on_date=on_date))
    assert len(steps) == 14
    by_no = {s["step_no"]: s for s in steps}
    assert [n for _, n in decision.STEP_NAMES] == [s["step_name"] for s in steps]
    assert "RULE-TEST-WHT" in by_no[4]["detail"]["applicable"]
    t5 = [t for t in by_no[5]["detail"]["treatments"]
          if t["rule_code"] == "RULE-TEST-WHT"][0]
    assert t5["treatment_code"] == "deduct"
    calc_item = [c for c in by_no[10]["detail"]["calculations"]
                 if c["calc_code"] == "CALC-TEST-WHT"][0]
    assert calc_item["result"]["result"] == 35000.0
    assert any(r["risk_code"] == "RISK-TEST"
               for r in by_no[7]["detail"]["risks"])
    assert any(e["evidence_code"] == "EV-TEST-INV"
               for e in by_no[8]["detail"]["evidence"])
    assert by_no[13]["detail"]["return_fields"]
    # deterministic
    steps2 = decision.analyze(
        synth, {}, facts,
        calc_runner=lambda code, inputs, on_date=None:
            calcmod.run_calculation(synth, code, inputs, on_date=on_date))
    assert steps == steps2


def test_loader_rejects_invented_content(synth):
    bad = {"meta": {"domain": "test"},
           "rules": [{"code": "RULE-BAD", "title": "x"}]}  # missing required fields
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".json",
                                     delete=False) as fh:
        json.dump(bad, fh)
        path = fh.name
    try:
        with pytest.raises(SeedError):
            loader.load_seed_file(Path(path), conn=synth)
    finally:
        os.unlink(path)


def test_working_data_tables_exist(seeded, conn):
    for t in ["tax_profiles", "tax_assessments", "tax_assessment_steps",
              "tax_evidence_tracker", "tax_reconciliations",
              "tax_calculation_runs", "tax_export_log"]:
        assert conn.execute(
            "SELECT COUNT(*) FROM " + t).fetchone()[0] == 0

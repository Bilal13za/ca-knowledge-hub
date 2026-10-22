"""Phase 2 acceptance: audit module seeding, rule engine, UI contract."""
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import db as dbmod
from hubcore import registry
from hubcore import search as searchmod
from modules.audit.engine import RuleEngine
from modules.audit.seed import seed_audit

DATA_DIR = HUB / "modules" / "audit" / "data"


@pytest.fixture()
def seeded(conn):
    counts = seed_audit(conn, DATA_DIR)
    conn.commit()
    return counts


def test_seed_counts_match_source(seeded, conn):
    # source library.db verified counts (REUSE_AUDIT.md)
    assert seeded["audit_rules"] == 30
    assert seeded["audit_factors"] == 29
    assert seeded["audit_risks"] == 29
    assert seeded["audit_procedures"] == 99
    assert seeded["audit_evidence"] == 89
    assert seeded["audit_controls"] == 58
    assert seeded["audit_assertions"] == 15
    assert seeded["audit_cycles"] == 11
    assert seeded["knowledge_records(audit)"] == 30 + 99 + 29


def test_seed_idempotent(conn):
    first = seed_audit(conn, DATA_DIR)
    conn.commit()
    second = seed_audit(conn, DATA_DIR)
    conn.commit()
    assert first == second


def test_rule_engine_triggers_revenue_rule(seeded, conn):
    plan = RuleEngine(conn).assess(["F-REV-001"])
    rule_ids = [t["rule_id"] for t in plan["triggered_rules"]]
    assert "RULE-REV-001" in rule_ids
    assert plan["counts"]["rules_triggered"] >= 1
    assert plan["counts"]["risks"] >= 1
    assert plan["counts"]["procedures"] >= 1
    # every procedure in the plan is Verified (source quality gate)
    for p in plan["procedures"]:
        assert p["review_status"] == "Verified"
    # deterministic: same input -> same output
    plan2 = RuleEngine(conn).assess(["F-REV-001"])
    assert plan == plan2


def test_rule_engine_exclude_and_empty(seeded, conn):
    plan = RuleEngine(conn).assess([])
    assert plan["triggered_rules"] == []
    assert plan["counts"]["risks"] == 0


def test_plan_for_factor(seeded, conn):
    plan = RuleEngine(conn).plan_for_factor("F-INV-001")
    assert plan["factor"]["id"] == "F-INV-001"
    assert len(plan["risks"]) >= 1
    with pytest.raises(ValueError):
        RuleEngine(conn).plan_for_factor("F-NOPE")


def test_engine_search(seeded, conn):
    hits = RuleEngine(conn).search("revenue")
    kinds = {h["kind"] for h in hits}
    assert kinds & {"factor", "risk", "procedure"}


def test_global_search_finds_audit_stubs(seeded, conn):
    res = searchmod.search_records(conn, "premature revenue recognition",
                                   modules=["audit"])
    assert res
    assert res[0]["module"] == "audit"
    assert res[0]["verification_status"] == "verified"  # RULE-REV-001 is Verified


def test_manifest_valid_and_pages_load():
    manifest_path = HUB / "modules" / "audit" / "module.json"
    import json

    data = json.loads(manifest_path.read_text())
    registry.validate_manifest(data, source=str(manifest_path))
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert len(pages) == 3
    assert {p["id"] for p in pages} == {
        "audit_explorer", "audit_rules", "audit_procedures"}
    for p in pages:
        assert callable(p["render"])

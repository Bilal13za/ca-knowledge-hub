"""Phase 9 acceptance: template library, paper workflow, exceptions."""
import json
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from hubcore import search as searchmod
from modules.workpapers import seed as seedmod
from modules.workpapers import store


@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_workpapers(conn)
    conn.commit()
    return counts


def test_seed_templates(seeded):
    assert seeded["wp_templates"] == 9
    assert seeded["knowledge_records(workpapers)"] == 9


def test_seed_idempotent(conn):
    first = seedmod.seed_workpapers(conn)
    conn.commit()
    second = seedmod.seed_workpapers(conn)
    conn.commit()
    assert first == second


def test_templates_carry_disclaimer(seeded, conn):
    rows = conn.execute("SELECT disclaimer FROM wp_templates").fetchall()
    assert rows
    for r in rows:
        assert "firm's audit methodology" in r["disclaimer"]
    cats = {r[0] for r in conn.execute(
        "SELECT DISTINCT category FROM wp_templates")}
    assert {"planning", "risk_register", "control_description",
            "control_test", "substantive_procedure", "evidence_register",
            "review_checklist", "completion_checklist",
            "exception_log"} <= cats


def test_paper_lifecycle(seeded, conn):
    pid = store.create_paper(conn, engagement="ABC FY26",
                             template_id="WP-T-SUBST",
                             title="Revenue cut-off")
    store.save_paper_data(conn, pid, {"Objective": "done"}, status="in_review")
    paper = store.get_paper(conn, pid)
    assert paper["status"] == "in_review"
    assert paper["data"]["Objective"] == "done"
    assert paper["template"]["id"] == "WP-T-SUBST"
    with pytest.raises(ValueError):
        store.create_paper(conn, engagement="x", template_id="WP-T-NOPE",
                           title="bad")
    with pytest.raises(ValueError):
        store.save_paper_data(conn, pid, {}, status="bogus")


def test_exception_tracking_requires_resolution(seeded, conn):
    eid = store.log_exception(conn, description="Cut-off error Rs. 50k",
                              assertion="cut-off", potential_impact="material")
    assert store.list_exceptions(conn, status="open")[0]["id"] == eid
    with pytest.raises(ValueError):  # empty resolution rejected
        store.resolve_exception(conn, eid, "   ")
    store.resolve_exception(conn, eid, "Adjusted; see WP #3.")
    assert store.list_exceptions(conn, status="open") == []
    with pytest.raises(ValueError):
        store.log_exception(conn, description="  ")


def test_evidence_register(seeded, conn):
    pid = store.create_paper(conn, engagement="ABC FY26",
                             template_id="WP-T-EVIDREG", title="Evidence")
    eid = store.add_evidence(conn, paper_id=pid, ref="E-001",
                             description="Bank statement Dec",
                             source="Client bank", reliability="original")
    ev = store.list_evidence(conn, pid)
    assert len(ev) == 1 and ev[0]["ref"] == "E-001"
    with pytest.raises(ValueError):
        store.add_evidence(conn, paper_id=pid, ref="", description="")


def test_global_search_finds_templates(seeded, conn):
    res = searchmod.search_records(conn, "completion checklist",
                                   modules=["workpapers"])
    assert res and res[0]["module"] == "workpapers"


def test_manifest_valid_and_pages_load():
    data = json.loads(
        (HUB / "modules" / "workpapers" / "module.json").read_text(
            encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert {p["id"] for p in pages} == {
        "wp_templates", "wp_papers", "wp_exceptions"}
    for p in pages:
        assert callable(p["render"])

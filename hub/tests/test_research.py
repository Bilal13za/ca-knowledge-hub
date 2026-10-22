"""Phase 12 acceptance: issue workflow, append-only conclusions."""
import json
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from hubcore import search as searchmod
from modules.research import seed as seedmod
from modules.research import store


@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_research(conn)
    conn.commit()
    return counts


def test_seed_guides(seeded, conn):
    assert seeded["knowledge_records(research)"] == 3
    assert seeded["rs_issues"] == 0
    assert seedmod.seed_research(conn)[
        "knowledge_records(research)"] == 3  # idempotent


def test_issue_lifecycle(seeded, conn):
    iid = store.register_issue(conn, title="WHT on services",
                               question="What rate applies?",
                               background="Client pays consultants.")
    store.set_issue_status(conn, iid, "in_progress")
    issue = store.get_issue(conn, iid)
    assert issue["status"] == "in_progress"
    assert issue["conclusion"] is None
    with pytest.raises(ValueError):
        store.register_issue(conn, title=" ", question="q")
    with pytest.raises(ValueError):
        store.set_issue_status(conn, iid, "bogus")
    with pytest.raises(ValueError):
        store.get_issue(conn, 9999)


def test_sources_findings_comparisons(seeded, conn):
    iid = store.register_issue(conn, title="T", question="Q")
    a = store.add_source(conn, issue_id=iid, citation="Ordinance s.153",
                         source_type="statute", reliability="primary")
    b = store.add_source(conn, issue_id=iid, citation="Blog post",
                         source_type="website", reliability="commentary")
    assert len(store.list_sources(conn, iid)) == 2
    store.add_finding(conn, issue_id=iid, source_id=a,
                      point="Rate specified in the section.",
                      relevance="directly answers Q")
    assert len(store.list_findings(conn, iid)) == 1
    cid = store.add_comparison(conn, issue_id=iid, aspect="rate",
                               source_a_id=a, source_b_id=b,
                               agreement="conflict",
                               note="Blog outdated; statute prevails.")
    comps = store.list_comparisons(conn, iid)
    assert len(comps) == 1 and comps[0]["id"] == cid
    assert comps[0]["agreement"] == "conflict"
    with pytest.raises(ValueError):
        store.add_source(conn, issue_id=iid, citation=" ")
    with pytest.raises(ValueError):
        store.add_comparison(conn, issue_id=iid, aspect="x",
                             source_a_id=a, source_b_id=b,
                             agreement="maybe")


def test_conclusions_append_only(seeded, conn):
    iid = store.register_issue(conn, title="T", question="Q")
    store.record_conclusion(conn, issue_id=iid,
                            conclusion_text="Rate is X.",
                            basis="Statute s.153")
    store.record_conclusion(conn, issue_id=iid,
                            conclusion_text="Rate is X, confirmed.",
                            basis="Statute s.153 + circular 2024")
    hist = store.conclusion_history(conn, iid)
    assert [v["version_no"] for v in hist] == [1, 2]
    assert hist[0]["conclusion_text"] == "Rate is X."  # v1 preserved
    cur = store.current_conclusion(conn, iid)
    assert cur["version_no"] == 2
    assert store.get_issue(conn, iid)["versions"] == 2
    with pytest.raises(ValueError):
        store.record_conclusion(conn, issue_id=iid,
                                conclusion_text="  ")


def test_global_search_finds_guides(seeded, conn):
    res = searchmod.search_records(conn, "version conclusions",
                                   modules=["research"])
    assert res and res[0]["module"] == "research"


def test_manifest_and_pages():
    data = json.loads(
        (HUB / "modules" / "research" / "module.json").read_text(
            encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert {p["id"] for p in pages} == {"rs_issues", "rs_detail"}
    for p in pages:
        assert callable(p["render"])

"""Phase 11 acceptance: no invented provisions, calendar logic."""
import json
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from hubcore import search as searchmod
from modules.complaw import seed as seedmod
from modules.complaw import store


@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_complaw(conn)
    conn.commit()
    return counts


def test_seed_starter_topics_assert_no_sections(seeded, conn):
    rows = conn.execute(
        "SELECT section_no, verification_status FROM law_provisions"
    ).fetchall()
    assert len(rows) == 8
    assert all(r["section_no"] is None for r in rows)  # nothing invented
    assert all(r["verification_status"] == "user_note" for r in rows)
    assert seeded["knowledge_records(complaw)"] == 8


def test_seed_idempotent(seeded, conn):
    assert seedmod.seed_complaw(conn)["law_provisions"] == 8


def test_add_traced_provision(seeded, conn):
    pid = store.add_provision(
        conn, title="Test provision", section_no="s. 99",
        summary="Traced from official text.",
        source_ref="Companies Act 2017, official PDF p. 45",
        verification_status="verified")
    rows = store.list_provisions(conn)
    assert len(rows) == 9
    assert store.list_provisions(conn, status="verified")[0]["id"] == pid
    with pytest.raises(ValueError):
        store.add_provision(conn, title="  ")
    with pytest.raises(ValueError):
        store.add_provision(conn, title="x",
                            verification_status="bogus")


def test_deadline_lifecycle_and_computed_status(seeded, conn):
    cid = store.add_company(conn, name="ABC (Pvt) Ltd", cuin="0123456")
    past = store.add_deadline(conn, company_id=cid, obligation="AGM",
                              due_date="2020-01-01")
    future = store.add_deadline(conn, company_id=cid, obligation="Return",
                                due_date="2099-01-01")
    rows = {d["id"]: d for d in
            store.list_deadlines(conn, today="2026-10-21")}
    assert rows[past]["computed_status"] == "overdue"
    assert rows[future]["computed_status"] == "upcoming"
    store.mark_deadline_done(conn, past, done_date="2020-01-02")
    rows = {d["id"]: d for d in
            store.list_deadlines(conn, today="2026-10-21")}
    assert rows[past]["computed_status"] == "done"
    with pytest.raises(ValueError):
        store.add_deadline(conn, company_id=cid, obligation="x",
                           due_date="not-a-date")
    with pytest.raises(ValueError):
        store.add_company(conn, name="  ")


def test_filing_register(seeded, conn):
    cid = store.add_company(conn, name="XYZ Ltd")
    fid = store.add_filing(conn, company_id=cid, form_name="Form A",
                           status="filed", reference_no="R-1")
    filings = store.list_filings(conn)
    assert len(filings) == 1 and filings[0]["id"] == fid
    with pytest.raises(ValueError):
        store.add_filing(conn, company_id=cid, form_name="",
                         status="bogus")
    with pytest.raises(ValueError):
        store.add_filing(conn, company_id=cid, form_name=" ")


def test_global_search_finds_provisions(seeded, conn):
    res = searchmod.search_records(conn, "auditors",
                                   modules=["complaw"])
    assert res and res[0]["module"] == "complaw"


def test_manifest_and_pages():
    data = json.loads(
        (HUB / "modules" / "complaw" / "module.json").read_text(
            encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert {p["id"] for p in pages} == {
        "cl_provisions", "cl_companies", "cl_calendar", "cl_filings"}
    for p in pages:
        assert callable(p["render"])

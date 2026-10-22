"""Phase 4 acceptance: FR library seeding, suggester, UI contract."""
import json
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from hubcore import search as searchmod
from modules.fr import seed as seedmod
from modules.fr import suggest as suggestmod
from modules.audit.seed import seed_audit  # for cross-module link check

DATA_DIR = HUB / "modules" / "fr" / "data"
AUDIT_DATA = HUB / "modules" / "audit" / "data"


@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_fr(conn, DATA_DIR)
    conn.commit()
    return counts


def test_seed_counts(seeded):
    assert seeded["fr_standards"] == 13
    assert seeded["fr_treatments"] == 8
    assert seeded["fr_examples"] == 8
    assert seeded["fr_treatment_standard"] == 8
    assert seeded["knowledge_records(fr)"] == 13 + 8 + 8


def test_seed_idempotent(conn):
    first = seedmod.seed_fr(conn, DATA_DIR)
    conn.commit()
    second = seedmod.seed_fr(conn, DATA_DIR)
    conn.commit()
    assert first == second


def test_journals_and_mistakes_valid_json(seeded, conn):
    for r in conn.execute("SELECT id, journals_json, common_mistakes_json"
                          " FROM fr_treatments"):
        journals = json.loads(r["journals_json"])
        mistakes = json.loads(r["common_mistakes_json"])
        assert isinstance(journals, list) and journals, r["id"]
        assert isinstance(mistakes, list) and mistakes, r["id"]
        for j in journals:
            assert j.get("debit") and j.get("credit"), r["id"]


def test_no_paragraph_numbers_in_content():
    # policy: the module never cites standard paragraph numbers.
    # (The word "paragraph" may appear in the policy statement itself;
    #  what is forbidden are citation patterns like "para. 12" or "IAS 2.10".)
    import re
    citation = re.compile(
        r"\bpara\.?\s*\d+|\bparagraphs?\s+\d+|\b(IAS|IFRS)\s+\d+\.\d+")
    for name in ("standards.json", "treatments.json", "examples.json"):
        text = (DATA_DIR / name).read_text(encoding="utf-8")
        assert not citation.search(text), name


def test_all_content_marked_unverified(seeded, conn):
    for table in ("fr_standards", "fr_treatments", "fr_examples"):
        bad = conn.execute(
            f"SELECT COUNT(*) FROM {table} "
            f"WHERE verification_status != 'extracted_unverified'").fetchone()[0]
        assert bad == 0, table


def test_audit_risk_links_valid(conn):
    # seed audit first, then FR: every FR->audit link must resolve
    seed_audit(conn, AUDIT_DATA)
    seedmod.seed_fr(conn, DATA_DIR)
    conn.commit()
    dangling = conn.execute(
        """SELECT l.treatment_id, l.audit_risk_id
           FROM fr_treatment_audit_risk l
           LEFT JOIN audit_risks r ON r.id = l.audit_risk_id
           WHERE r.id IS NULL""").fetchall()
    assert dangling == []
    n = conn.execute(
        "SELECT COUNT(*) FROM fr_treatment_audit_risk").fetchone()[0]
    assert n >= 5  # revenue, inventory, PPE x2, provision, impairment


def test_suggester_suggests_but_never_asserts(seeded, conn):
    res = suggestmod.suggest(["lease_arrangement"], conn)
    ids = [c["standard_id"] for c in res["candidates"]]
    assert "IFRS 16" in ids
    assert "not a determination" in res["disclaimer"]
    # candidates carry linked treatments
    ifrs16 = next(c for c in res["candidates"]
                  if c["standard_id"] == "IFRS 16")
    assert any(t["id"] == "FR-TREAT-004" for t in ifrs16["treatments"])
    # empty input -> no suggestions, never guesses
    assert suggestmod.suggest([], conn)["candidates"] == []
    # deterministic
    assert suggestmod.suggest(["lease_arrangement"], conn) == res
    # multiple characteristics merge
    res2 = suggestmod.suggest(["sale_of_goods", "inventory_held"], conn)
    ids2 = [c["standard_id"] for c in res2["candidates"]]
    assert "IFRS 15" in ids2 and "IAS 2" in ids2


def test_global_search_finds_fr_stubs(seeded, conn):
    res = searchmod.search_records(conn, "lease liability", modules=["fr"])
    assert res
    assert res[0]["module"] == "fr"


def test_manifest_valid_and_pages_load():
    data = json.loads(
        (HUB / "modules" / "fr" / "module.json").read_text(encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert len(pages) == 4
    assert {p["id"] for p in pages} == {
        "fr_treatments", "fr_standards", "fr_examples", "fr_suggester"}
    for p in pages:
        assert callable(p["render"])

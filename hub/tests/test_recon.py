"""Phase 5 acceptance: workbench port + run persistence.

Workbench behavioural tests are ported from the source app's suite
(hand-computed expectations from the same sample files); store tests
cover run/dataset/finding persistence and manual resolution.
"""
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from modules.recon import seed as seedmod
from modules.recon import store
from modules.recon import workbench as wb
from modules.recon.workbench import ColumnMap, Finding, ValidationRules

SAMPLE = HUB / "modules" / "recon" / "sample_data"


@pytest.fixture()
def bank():
    return wb.load_table(SAMPLE / "bank_statement.csv")


@pytest.fixture()
def book():
    return wb.load_table(SAMPLE / "cash_book.csv")


@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_recon(conn)
    conn.commit()
    return counts


# ------------------------------------------------- ported workbench tests

def test_load_table_row_refs(bank):
    assert len(bank) == 10
    assert list(bank["_src_row"][:3]) == [2, 3, 4]


def test_inspect_table(bank):
    info = wb.inspect_table(bank, "bank")
    assert info["rows"] == 10
    amounts = next(c for c in info["columns"] if c["name"] == "Amount")
    assert amounts["total"] == pytest.approx(50000 + 12500 + 200000 + 18750
                                             + 1500 + 75000 + 30000 + 9000
                                             + 45000 + 12000)


def test_reconciliation_expected_results(bank, book):
    result = wb.reconcile(
        bank, book,
        ColumnMap(id="Ref", amount="Amount", date="Date",
                  description="Description"),
        ColumnMap(id="Ref", amount="Amount", date="Date",
                  description="Narration"),
        amount_tolerance=0.01, label_a="Bank", label_b="Book")
    s = result["summary"]
    assert s["matched"] == 6
    assert s["amount_differences"] == 1
    assert s["unmatched_a"] == 1
    assert s["unmatched_b"] == 1
    assert s["ambiguous_ids"] == 1
    assert len(result["blank_ids_a"]) == 1
    assert result["ambiguous"][0]["id"] == "TXN-008"
    diff = result["amount_differences"][0]
    assert diff["id"] == "TXN-009"
    assert diff["difference"] == pytest.approx(-500.0)


def test_reconciliation_never_silently_merges(bank, book):
    result = wb.reconcile(
        bank, book,
        ColumnMap(id="Ref", amount="Amount"),
        ColumnMap(id="Ref", amount="Amount"),
        label_a="Bank", label_b="Book")
    matched_ids = {m["id"] for m in result["matched"]}
    assert "TXN-008" not in matched_ids
    assert result["duplicates_within_b"] == [{"id": "TXN-008", "rows": [9, 10]}]


def test_duplicate_invoices():
    df = wb.load_table(SAMPLE / "duplicate_invoices.csv")
    findings = wb.find_duplicates(df, ["InvoiceNo"])
    keys = sorted(f.details["key"] for f in findings)
    assert keys == ["INV-1002", "INV-1004"]
    inv1002 = next(f for f in findings if f.details["key"] == "INV-1002")
    assert inv1002.details["rows"] == [3, 5]
    assert inv1002.severity == "error"


def test_duplicate_ignores_blank_keys(bank):
    assert wb.find_duplicates(bank, ["Ref"]) == []


def test_validation_missing_values():
    df = wb.load_table(SAMPLE / "missing_values.csv")
    rules = ValidationRules(
        required_columns=["TxnID", "Date", "Description"],
        date_columns=["Date"],
        amount_columns=["Debit", "Credit"],
        non_negative_columns=["Debit", "Credit"],
    )
    findings = wb.validate_table(df, rules)
    by_kind = {}
    for f in findings:
        by_kind.setdefault(f.kind, []).append(f)
    assert any(f.row_ref == 3 for f in by_kind["blank_required"])
    assert any("32/13/2026" in f.message for f in by_kind["invalid_date"])
    assert any(f.row_ref == 6 for f in by_kind["invalid_amount"])
    negs = by_kind["inconsistent_sign"]
    assert negs and all(f.severity == "warning" for f in negs)
    assert any(f.row_ref == 8 for f in by_kind["outlier"])
    assert "suspicious_round" in by_kind
    for f in by_kind["outlier"] + by_kind["suspicious_round"]:
        assert f.severity in ("info", "warning")


def test_arithmetic_total_check():
    import pandas as pd
    df = pd.DataFrame({
        "A": ["10", "20", "30"],
        "B": ["5", "5", "5"],
        "Total": ["15", "25", "99"],
        "_src_row": [2, 3, 4],
    })
    rules = ValidationRules(total_checks=[{"columns": ["A", "B"],
                                           "equals": "Total",
                                           "label": "A+B=Total"}])
    findings = wb.validate_table(df, rules)
    assert len(findings) == 1
    assert findings[0].kind == "arithmetic_mismatch"
    assert findings[0].row_ref == 4


def test_export_csv_and_xlsx_roundtrip(bank, tmp_path):
    findings = [Finding("duplicate", "error", "test finding",
                        row_ref=3, column="Ref")]
    csv_path = wb.export_report(findings, tmp_path / "rep.csv", fmt="csv")
    xlsx_path = wb.export_report(findings, tmp_path / "rep.xlsx", fmt="xlsx",
                                 summary={"matched": 6})
    import pandas as pd
    assert "test finding" in pd.read_csv(csv_path)["message"].iloc[0]
    back = pd.read_excel(xlsx_path, sheet_name="Findings")
    assert "test finding" in back["message"].iloc[0]
    summary = pd.read_excel(xlsx_path, sheet_name="Summary")
    assert int(summary.loc[summary["item"] == "matched",
                           "value"].iloc[0]) == 6


# ------------------------------------------------------------- store tests

def test_run_persistence_roundtrip(seeded, conn, bank, book):
    run_id = store.create_run(conn, name="Jan bank rec", kind="bank",
                              label_a="Bank", label_b="Book")
    store.save_dataset(conn, run_id, "a", bank, "bank_statement.csv")
    store.save_dataset(conn, run_id, "b", book, "cash_book.csv")
    result = wb.reconcile(
        bank, book,
        ColumnMap(id="Ref", amount="Amount"),
        ColumnMap(id="Ref", amount="Amount"),
        label_a="Bank", label_b="Book")
    n = store.save_reconcile_result(conn, run_id, result)
    assert n > 0
    run = store.get_run(conn, run_id)
    assert run["name"] == "Jan bank rec"
    assert len(run["datasets"]) == 2
    # original data preserved verbatim
    ds_a = conn.execute(
        "SELECT rows_json FROM recon_datasets WHERE run_id=? AND side='a'",
        (run_id,)).fetchone()
    import json
    rows = json.loads(ds_a["rows_json"])
    assert len(rows) == 10
    assert rows[0]["Ref"] == "TXN-001"
    kinds = {f["kind"] for f in run["findings"]}
    assert {"amount_difference", "unmatched", "ambiguous"} <= kinds
    assert run["summary"]["matched"] == 6


def test_manual_resolution_requires_note(seeded, conn, bank):
    run_id = store.create_run(conn, name="dup check", kind="supplier")
    store.save_dataset(conn, run_id, "a", bank, "bank.csv")
    findings = wb.find_duplicates(
        wb.load_table(SAMPLE / "duplicate_invoices.csv"), ["InvoiceNo"])
    store.save_findings(conn, run_id, findings)
    fid = conn.execute(
        "SELECT id FROM recon_findings WHERE run_id=? LIMIT 1",
        (run_id,)).fetchone()[0]
    store.resolve_finding(conn, fid, "Confirmed duplicate entry with vendor.")
    row = conn.execute(
        "SELECT status, resolution_note FROM recon_findings WHERE id=?",
        (fid,)).fetchone()
    assert row["status"] == "resolved"
    assert "duplicate" in row["resolution_note"]
    with pytest.raises(ValueError):
        store.resolve_finding(conn, fid, "x", status="bogus")


def test_export_findings_xlsx(seeded, conn, bank, tmp_path):
    run_id = store.create_run(conn, name="export me", kind="bank")
    store.save_findings(conn, run_id,
                        [Finding("duplicate", "error", "dup", row_ref=3)])
    path = store.export_findings(conn, run_id, tmp_path / "out.xlsx")
    assert path.exists()
    import pandas as pd
    back = pd.read_excel(path, sheet_name="Findings")
    assert "dup" in back["message"].iloc[0]


def test_manifest_valid_and_pages_load():
    import json
    data = json.loads(
        (HUB / "modules" / "recon" / "module.json").read_text(
            encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert {p["id"] for p in pages} == {
        "recon_new", "recon_validate", "recon_history"}
    for p in pages:
        assert callable(p["render"])

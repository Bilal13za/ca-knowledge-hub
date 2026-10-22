"""Phase 6 acceptance: analysis engine, templates, run recipes."""
import json
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from modules.xlanalysis import analyze, seed as seedmod, templates


@pytest.fixture()
def df():
    import pandas as pd
    return pd.DataFrame({
        "Dept": [" Sales ", "Sales", "IT", "IT", ""],
        "Budget": ["1000", "2000", "1500", "1500", ""],
        "Actual": ["1100", "2500", "1400", "900", ""],
        "Date": ["01/02/2026", "2026-02-05", "not-a-date", "2026-02-08", ""],
    })


@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_xlanalysis(conn)
    conn.commit()
    return counts


def test_clean_frame_logs_everything(df):
    cleaned, log = analyze.clean_frame(df)
    actions = {e["action"] for e in log}
    assert "strip_whitespace" in actions
    assert "drop_blank_rows" in actions
    assert len(cleaned) == 4  # blank row dropped
    assert list(cleaned["Dept"][:2]) == ["Sales", "Sales"]
    # unparseable date kept, not dropped or invented
    assert "not-a-date" in cleaned["Date"].tolist()


def test_variance_flags_thresholds(df):
    cleaned, _ = analyze.clean_frame(df)
    res = analyze.variance_analysis(
        cleaned, actual_col="Actual", compare_col="Budget",
        threshold_pct=0.10, threshold_abs=50.0)
    # row0: +100 (+10%) -> flagged (>= thresholds); row2: -100 (-6.7%) -> not
    by_row = {r["row"]: r for r in res["rows"]}
    assert by_row[0]["variance"] == 100.0
    assert by_row[0]["flagged"] is True
    assert by_row[2]["flagged"] is False
    assert res["totals"]["variance"] == pytest.approx(
        (1100 + 2500 + 1400 + 900) - (1000 + 2000 + 1500 + 1500))


def test_summarize_group_by(df):
    cleaned, _ = analyze.clean_frame(df)
    out = analyze.summarize(cleaned, by=["Dept"],
                            aggregations={"Actual": ["sum", "count"]})
    sales = out[out["Dept"] == "Sales"].iloc[0]
    assert sales["Actual__sum"] == pytest.approx(3600.0)
    assert sales["Actual__count"] == 2


def test_calculated_column_and_injection_safety(df):
    cleaned, _ = analyze.clean_frame(df)
    out, recipe = analyze.add_calculated_column(
        cleaned, "variance2", "Actual - Budget")
    assert recipe["inputs"] == ["Actual", "Budget"]
    assert out["variance2"].iloc[0] == pytest.approx(100.0)
    with pytest.raises(ValueError):
        analyze.add_calculated_column(
            cleaned, "evil", "__import__('os').system('x')")
    with pytest.raises(ValueError):
        analyze.add_calculated_column(cleaned, "bad", "Nope - Budget")


def test_exception_report(df):
    cleaned, _ = analyze.clean_frame(df)
    findings = analyze.exception_report(cleaned, [
        {"column": "Actual", "op": "gt", "value": 2000,
         "label": "Large actual", "severity": "warning"},
        {"column": "Date", "op": "blank", "label": "Missing date",
         "severity": "error"},
    ])
    assert any(f["rule"] == "Large actual" and f["row"] == 1
               for f in findings)
    with pytest.raises(ValueError):
        analyze.exception_report(cleaned, [{"column": "Nope", "op": "gt",
                                            "value": 1}])


def test_templates_produce_workbooks(df, tmp_path):
    cleaned, _ = analyze.clean_frame(df)
    res = analyze.variance_analysis(cleaned, actual_col="Actual",
                                    compare_col="Budget")
    p1 = templates.variance_report_wb(res, "Test variance",
                                      tmp_path / "var.xlsx")
    p2 = templates.summary_wb(
        analyze.summarize(cleaned, by=["Dept"],
                          aggregations={"Actual": ["sum"]}),
        "Test summary", tmp_path / "sum.xlsx")
    p3 = templates.findings_wb(
        analyze.exception_report(cleaned, [
            {"column": "Actual", "op": "gt", "value": 2000,
             "label": "Large", "severity": "warning"}]),
        "Test exceptions", tmp_path / "exc.xlsx")
    import openpyxl
    for p, sheet in ((p1, "Variance report"), (p2, "Summary"),
                     (p3, "Exceptions")):
        assert p.exists()
        wb = openpyxl.load_workbook(p)
        assert sheet in wb.sheetnames
        wb.close()
    # flagged row is highlighted and values are right
    wb = openpyxl.load_workbook(p1)
    ws = wb["Variance report"]
    assert ws["A1"].value == "Test variance"
    wb.close()


def test_run_recipe_persisted(seeded, conn):
    conn.execute(
        """INSERT INTO xla_runs (name, operation, recipe_json, summary_json)
           VALUES (?,?,?,?)""",
        ("v1", "variance",
         json.dumps({"actual": "Actual", "compare": "Budget",
                     "threshold_pct": 0.10}),
         json.dumps({"flagged": 1})))
    conn.commit()
    row = conn.execute("SELECT * FROM xla_runs").fetchone()
    recipe = json.loads(row["recipe_json"])
    assert recipe["threshold_pct"] == 0.10  # reproducible from the recipe


def test_manifest_valid_and_pages_load():
    data = json.loads(
        (HUB / "modules" / "xlanalysis" / "module.json").read_text(
            encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert {p["id"] for p in pages} == {"xla_analyze", "xla_history"}
    for p in pages:
        assert callable(p["render"])

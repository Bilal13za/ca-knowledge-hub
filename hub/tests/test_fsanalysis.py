"""Phase 8 acceptance: ratio engine, trends, red flags."""
import sys
from decimal import Decimal
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from modules.fsanalysis import ratios as rmod
from modules.fsanalysis import redflags
from modules.fsanalysis import seed as seedmod


@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_fsanalysis(conn)
    conn.commit()
    return counts


@pytest.fixture()
def full_inputs():
    return {
        "revenue": "1000000", "cost_of_sales": "600000",
        "gross_profit": "400000", "operating_expenses": "150000",
        "operating_profit": "250000", "finance_costs": "50000",
        "profit_before_tax": "200000", "tax_expense": "60000",
        "profit_after_tax": "140000", "dividends_paid": "70000",
        "total_assets": "2000000", "current_assets": "800000",
        "inventory": "300000", "trade_receivables": "250000",
        "cash": "50000", "current_liabilities": "500000",
        "trade_payables": "200000", "non_current_liabilities": "600000",
        "total_equity": "900000", "operating_cash_flow": "100000",
    }


def test_ratios_hand_computed(full_inputs):
    res = rmod.compute_ratios(full_inputs)
    r = res["ratios"]
    assert r["gross_margin"]["value"] == Decimal("40.00")
    assert r["net_margin"]["value"] == Decimal("14.00")
    assert r["current_ratio"]["value"] == Decimal("1.60")
    assert r["quick_ratio"]["value"] == Decimal("1.00")  # (800-300)/500
    assert r["gearing"]["value"] == Decimal("66.67")     # 600/900
    assert r["interest_cover"]["value"] == Decimal("5.00")
    assert r["receivable_days"]["value"] == Decimal("91.2")   # 250/1000*365
    assert r["inventory_days"]["value"] == Decimal("182.5")   # 300/600*365
    assert r["payable_days"]["value"] == Decimal("121.7")     # 200/600*365
    ccc = r["cash_conversion_cycle"]["value"]
    assert ccc == Decimal("152.0")  # 91.2 + 182.5 - 121.7
    assert r["ocf_to_profit"]["value"] == Decimal("0.71")     # 100/140
    assert r["dividend_cover"]["value"] == Decimal("2.00")
    assert res["skipped"] == []


def test_missing_inputs_skip_never_invent(full_inputs):
    thin = {"revenue": "1000000", "profit_after_tax": "140000"}
    res = rmod.compute_ratios(thin)
    assert "net_margin" in res["ratios"]
    assert "gross_margin" not in res["ratios"]
    assert any(s["ratio"] == "gross_margin" and "missing" in s["reason"]
               for s in res["skipped"])
    # zero denominator -> skipped, not crash
    zero = dict(full_inputs, current_liabilities="0")
    res2 = rmod.compute_ratios(zero)
    assert not any(k == "current_ratio" for k in res2["ratios"])


def test_common_size(full_inputs):
    pl = {"revenue": "1000000", "cost_of_sales": "600000",
          "profit_after_tax": "140000"}
    sfp = {"total_assets": "2000000", "inventory": "300000"}
    cs = rmod.common_size(pl, sfp)
    assert cs["profit_and_loss_pct_of_revenue"]["cost_of_sales"] == 60.0
    assert cs["sfp_pct_of_total_assets"]["inventory"] == 15.0


def test_trend_directions():
    periods = [
        {"label": "FY24", "inputs": {"revenue": "800000",
                                    "profit_after_tax": "80000",
                                    "trade_receivables": "150000"}},
        {"label": "FY25", "inputs": {"revenue": "1000000",
                                    "profit_after_tax": "140000",
                                    "trade_receivables": "250000"}},
    ]
    t = rmod.trend_analysis(periods)
    assert t["net_margin"]["direction"] == "up"       # 10% -> 14%
    assert t["receivable_days"]["direction"] == "up"  # 68.4 -> 91.2
    # single period -> insufficient, not guessed
    t1 = rmod.trend_analysis(periods[:1])
    assert t1["net_margin"]["direction"] == "insufficient"


def test_red_flags_are_investigation_prompts(full_inputs):
    res = rmod.compute_ratios(full_inputs)
    flags = redflags.evaluate_flags(res["ratios"])
    codes = {f["code"] for f in flags}
    # ocf/profit = 0.71 < 0.8 -> EARN-01 fires
    assert "EARN-01" in codes
    # current ratio 1.6 -> LIQ-01 must NOT fire
    assert "LIQ-01" not in codes
    for f in flags:
        assert "not evidence of misstatement" in f["investigate"]
        assert f["why_it_can_matter"]
    # distressed inputs fire liquidity + solvency flags
    bad = dict(full_inputs, current_assets="300000",
               current_liabilities="500000",
               non_current_liabilities="1200000", total_equity="900000")
    flags2 = redflags.evaluate_flags(rmod.compute_ratios(bad)["ratios"])
    codes2 = {f["code"] for f in flags2}
    assert {"LIQ-01", "SOLV-01"} <= codes2


def test_red_flags_need_trends_for_trend_flags(full_inputs):
    res = rmod.compute_ratios(full_inputs)
    # no trends passed -> trend-based flags never fire
    flags = redflags.evaluate_flags(res["ratios"], trends=None)
    assert "EFF-01" not in {f["code"] for f in flags}
    trends = {"receivable_days": {"direction": "up"}}
    flags2 = redflags.evaluate_flags(res["ratios"], trends=trends)
    assert "EFF-01" in {f["code"] for f in flags2}


def test_run_persistence(seeded, conn, full_inputs):
    import json
    res = rmod.compute_ratios(full_inputs)
    conn.execute(
        "INSERT INTO fs_runs (name, kind, inputs_json, result_json)"
        " VALUES (?,?,?,?)",
        ("ABC FY26", "ratios", json.dumps(full_inputs),
         json.dumps({k: str(v["value"]) for k, v in res["ratios"].items()})))
    conn.commit()
    row = conn.execute("SELECT * FROM fs_runs").fetchone()
    assert row["name"] == "ABC FY26"
    assert json.loads(row["result_json"])["gross_margin"] == "40.00"


def test_manifest_valid_and_pages_load():
    import json
    data = json.loads(
        (HUB / "modules" / "fsanalysis" / "module.json").read_text(
            encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert {p["id"] for p in pages} == {
        "fsa_ratios", "fsa_trends", "fsa_wc", "fsa_history"}
    for p in pages:
        assert callable(p["render"])

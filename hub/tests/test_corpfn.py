"""Phase 10 acceptance: finance engine hand-verified, runs persist."""
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from hubcore import search as searchmod
from modules.corpfn import finance, seed as seedmod


@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_corpfn(conn)
    conn.commit()
    return counts


def test_npv_hand_computed(seeded):
    # CFs 100, 120, 140 at 10%, outlay 300:
    # PV = 90.9091 + 99.1736 + 105.1833 = 295.2660; NPV = -4.7340 → -4.73
    res = finance.npv(["100", "120", "140"], "0.10", "300")
    assert res["npv"] == Decimal("-4.73")
    assert res["accept"] is False
    assert len(res["workings"]) == 3
    assert res["assumptions"]["discount_rate"] == "0.10"


def test_npv_accept(seeded):
    res = finance.npv(["200", "200", "200"], "0.10", "400")
    assert res["npv"] > 0 and res["accept"] is True


def test_npv_rejects_bad_inputs(seeded):
    with pytest.raises(ValueError):
        finance.npv([], "0.10", "100")
    with pytest.raises(ValueError):
        finance.npv(["100"], "abc", "100")
    with pytest.raises(ValueError):
        finance.npv(["100"], "-1.5", "100")


def test_irr_brackets_zero(seeded):
    # Outlay 300, CFs 100/120/140 → IRR ≈ 9.27%
    res = finance.irr(["100", "120", "140"], "300")
    assert Decimal("9.0") < Decimal(res["irr"]) * 100 < Decimal("9.6")
    assert abs(Decimal(res["check_npv_at_irr"])) < Decimal("1")


def test_irr_no_solution_raises(seeded):
    with pytest.raises(ValueError):
        finance.irr(["-100", "-100"], "300")


def test_payback(seeded):
    res = finance.payback(["100", "120", "140"], "300")
    assert res["discounted"] is False
    assert res["payback_periods"] == Decimal("2.57")  # 2 + 80/140
    res2 = finance.payback(["50", "50"], "300")
    assert res2["payback_periods"] is None
    res3 = finance.payback(["100", "120", "140"], "300", "0.10")
    assert res3["discounted"] is True


def test_capm(seeded):
    # Ke = 0.06 + 1.2*(0.14-0.06) = 0.156 → 15.60%
    res = finance.capm("0.06", "1.2", "0.14")
    assert res["cost_of_equity"] == Decimal("15.60")


def test_wacc(seeded):
    # E=600 D=400 Ke=15.6% Kd=10% t=29%:
    # 0.6*0.156 + 0.4*0.10*0.71 = 0.0936+0.0284 = 0.122 → 12.20%
    res = finance.wacc("600", "400", "0.156", "0.10", "0.29")
    assert res["wacc"] == Decimal("12.20")
    with pytest.raises(ValueError):
        finance.wacc("0", "0", "0.1", "0.1", "0.3")


def test_gordon(seeded):
    # 5 / (0.15 - 0.05) = 50.00
    res = finance.gordon_valuation("5", "0.15", "0.05")
    assert res["value_per_share"] == Decimal("50.00")
    with pytest.raises(ValueError):
        finance.gordon_valuation("5", "0.04", "0.05")


def test_sensitivity(seeded):
    res = finance.sensitivity(
        {"cash_flows": ["100", "120", "140"], "discount_rate": "0.10",
         "initial_outlay": "300"},
        "discount_rate", ["-0.10", "0", "0.10"])
    assert len(res["rows"]) == 3
    assert res["rows"][1]["npv"] == res["base_npv"]  # zero delta = base
    # lower rate must raise NPV
    assert Decimal(res["rows"][0]["npv"]) > Decimal(res["base_npv"])
    with pytest.raises(ValueError):
        finance.sensitivity({"cash_flows": ["100"], "discount_rate": "0.1"},
                            "beta", ["0.1"])


def test_seed_guides(seeded, conn):
    assert seeded["knowledge_records(corpfn)"] == 5
    assert seeded["cf_runs"] == 0
    assert seedmod.seed_corpfn(conn)["knowledge_records(corpfn)"] == 5  # idempotent


def test_global_search(seeded, conn):
    res = searchmod.search_records(conn, "wacc", modules=["corpfn"])
    assert res and res[0]["module"] == "corpfn"


def test_manifest_and_pages():
    data = json.loads(
        (HUB / "modules" / "corpfn" / "module.json").read_text(
            encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert {p["id"] for p in pages} == {
        "cf_appraisal", "cf_costofcap", "cf_valuation", "cf_history"}
    for p in pages:
        assert callable(p["render"])

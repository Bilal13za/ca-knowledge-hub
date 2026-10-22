"""Corporate finance engine (Phase 10).

Deterministic Decimal arithmetic. Every function takes explicit
assumptions as inputs and returns workings alongside results —
assumptions are always visible, calculations always reproducible.
Missing required inputs raise; values are never invented.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def _dec(name: str, value: Any) -> Decimal:
    try:
        s = str(value).strip().replace(",", "")
        if s in ("", "-", "nan", "None"):
            raise ValueError(f"Missing required input '{name}'.")
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid numeric input '{name}': {value!r}") from exc


def _q2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"))


def npv(cash_flows: list[Any], discount_rate: Any,
        initial_outlay: Any = 0) -> dict:
    """Net present value. cash_flows: period 1..n. Returns workings."""
    r = _dec("discount_rate", discount_rate)
    outlay = _dec("initial_outlay", initial_outlay)
    if not cash_flows:
        raise ValueError("cash_flows must not be empty")
    cfs = [_dec(f"cash_flow[{i}]", cf) for i, cf in enumerate(cash_flows)]
    if r <= -1:
        raise ValueError("discount_rate must exceed -100%")
    pv_items = []
    total_pv = Decimal("0")
    for t, cf in enumerate(cfs, start=1):
        df = Decimal("1") / ((Decimal("1") + r) ** t)
        pv = cf * df
        total_pv += pv
        pv_items.append({"period": t, "cash_flow": str(cf),
                         "discount_factor": str(df.quantize(Decimal("0.0001"))),
                         "present_value": str(_q2(pv))})
    value = _q2(total_pv - outlay)
    return {"npv": value,
            "accept": value > 0,
            "workings": pv_items,
            "assumptions": {
                "discount_rate": str(r),
                "initial_outlay": str(outlay),
                "periods": len(cfs),
                "timing": "cash flows assumed at each period end"}}


def irr(cash_flows: list[Any], initial_outlay: Any,
        *, tol: str = "0.0001", max_iter: int = 200) -> dict:
    """Internal rate of return via bisection on NPV(r) = 0."""
    cfs = [_dec(f"cash_flow[{i}]", cf) for i, cf in enumerate(cash_flows)]
    outlay = _dec("initial_outlay", initial_outlay)
    if not cfs:
        raise ValueError("cash_flows must not be empty")

    def npv_at(rate: Decimal) -> Decimal:
        total = Decimal("0")
        for t, cf in enumerate(cfs, start=1):
            total += cf / ((Decimal("1") + rate) ** t)
        return total - outlay

    lo, hi = Decimal("-0.9999"), Decimal("10")
    f_lo, f_hi = npv_at(lo), npv_at(hi)
    if f_lo * f_hi > 0:
        raise ValueError("IRR not bracketed: NPV has the same sign at "
                         "-99.99% and 1000% — no IRR in range.")
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = npv_at(mid)
        if abs(f_mid) < Decimal(tol) * max(abs(outlay), Decimal("1")):
            break
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    rate = ((lo + hi) / 2).quantize(Decimal("0.0001"))
    return {"irr": rate, "irr_pct": str((rate * 100).quantize(Decimal("0.01"))),
            "check_npv_at_irr": str(_q2(npv_at(rate))),
            "assumptions": {"method": "bisection",
                            "timing": "cash flows at period ends"}}


def payback(cash_flows: list[Any], initial_outlay: Any,
            discount_rate: Any | None = None) -> dict:
    """Payback (and discounted payback when a rate is given)."""
    cfs = [_dec(f"cash_flow[{i}]", cf) for i, cf in enumerate(cash_flows)]
    outlay = _dec("initial_outlay", initial_outlay)
    r = _dec("discount_rate", discount_rate) if discount_rate is not None else None

    def period_value(t: int, cf: Decimal) -> Decimal:
        if r is None:
            return cf
        return cf / ((Decimal("1") + r) ** t)

    cumul = Decimal("0")
    for t, cf in enumerate(cfs, start=1):
        prev = cumul
        cumul += period_value(t, cf)
        if cumul >= outlay:
            frac = (outlay - prev) / period_value(t, cf) if period_value(t, cf) else Decimal("0")
            pb = _q2(Decimal(t - 1) + frac)
            return {"payback_periods": pb,
                    "discounted": r is not None,
                    "assumptions": {"discount_rate": str(r) if r is not None else None,
                                    "interpolation": "linear within the payback year"}}
    return {"payback_periods": None, "discounted": r is not None,
            "note": "Outlay never recovered within the forecast horizon.",
            "assumptions": {}}


def capm(risk_free: Any, beta: Any, market_return: Any) -> dict:
    """Cost of equity via CAPM: Ke = Rf + β(Rm − Rf)."""
    rf = _dec("risk_free", risk_free)
    b = _dec("beta", beta)
    rm = _dec("market_return", market_return)
    ke = rf + b * (rm - rf)
    return {"cost_of_equity": _q2(ke * 100),
            "workings": {"risk_free_pct": str(rf * 100),
                         "beta": str(b),
                         "market_return_pct": str(rm * 100)},
            "assumptions": {"model": "CAPM",
                            "inputs_as_decimals": "e.g. 0.08 for 8%"}}


def wacc(equity_value: Any, debt_value: Any, cost_of_equity: Any,
         cost_of_debt: Any, tax_rate: Any) -> dict:
    """Weighted average cost of capital (market-value weights)."""
    e = _dec("equity_value", equity_value)
    d = _dec("debt_value", debt_value)
    ke = _dec("cost_of_equity", cost_of_equity)
    kd = _dec("cost_of_debt", cost_of_debt)
    t = _dec("tax_rate", tax_rate)
    v = e + d
    if v == 0:
        raise ValueError("equity_value + debt_value must not be zero")
    wacc_v = (e / v) * ke + (d / v) * kd * (Decimal("1") - t)
    return {"wacc": _q2(wacc_v * 100),
            "workings": {"weight_equity": str((e / v).quantize(Decimal("0.0001"))),
                         "weight_debt": str((d / v).quantize(Decimal("0.0001"))),
                         "after_tax_cost_of_debt_pct":
                             str((kd * (Decimal("1") - t) * 100).quantize(
                                 Decimal("0.01")))},
            "assumptions": {"weights": "market values",
                            "tax_shield": "kd × (1 − t)"}}


def gordon_valuation(next_dividend: Any, cost_of_equity: Any,
                     growth: Any) -> dict:
    """Gordon growth model: P0 = D1 / (ke − g)."""
    d1 = _dec("next_dividend", next_dividend)
    ke = _dec("cost_of_equity", cost_of_equity)
    g = _dec("growth", growth)
    if ke <= g:
        raise ValueError("cost_of_equity must exceed growth for the "
                         "Gordon model to converge.")
    value = _q2(d1 / (ke - g))
    return {"value_per_share": value,
            "assumptions": {"model": "Gordon growth",
                            "constant_growth_forever": str(g)}}


def sensitivity(base_inputs: dict[str, Any], vary: str,
                deltas: list[Any], calc: str = "npv") -> dict:
    """Vary one input by deltas (as decimals, e.g. ±0.10) and recompute.

    calc: 'npv' only in this version. base_inputs: {cash_flows,
    discount_rate, initial_outlay}.
    """
    if calc != "npv":
        raise ValueError("Only 'npv' sensitivity is implemented.")
    if vary not in ("discount_rate", "initial_outlay", "cash_flows"):
        raise ValueError(f"Cannot vary '{vary}'.")
    rows = []
    for delta in deltas:
        d = _dec("delta", delta)
        inputs = dict(base_inputs)
        if vary == "cash_flows":
            inputs["cash_flows"] = [str(_dec("cf", cf) * (Decimal("1") + d))
                                    for cf in base_inputs["cash_flows"]]
        else:
            inputs[vary] = str(_dec(vary, base_inputs[vary]) * (Decimal("1") + d))
        res = npv(inputs["cash_flows"], inputs["discount_rate"],
                  inputs.get("initial_outlay", 0))
        rows.append({"delta_pct": str((d * 100).quantize(Decimal("0.01"))),
                     "npv": str(res["npv"]), "accept": res["accept"]})
    base = npv(base_inputs["cash_flows"], base_inputs["discount_rate"],
               base_inputs.get("initial_outlay", 0))
    return {"base_npv": str(base["npv"]), "varied_input": vary,
            "rows": rows,
            "assumptions": {"method": "one-at-a-time",
                            "others_held_constant": True}}

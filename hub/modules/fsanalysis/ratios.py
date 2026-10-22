"""Financial-statement ratio engine (Phase 8).

Deterministic Decimal arithmetic over named line items. A ratio is
computed only when ALL its inputs are present and valid — missing
inputs mean the ratio is skipped (reported as such), never invented.

Red-flag indicators are investigation prompts, never proof of error
or fraud: every flag carries an explanation and an explicit
investigate note.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

# canonical input line items
ITEMS = [
    # P&L
    "revenue", "cost_of_sales", "gross_profit", "operating_expenses",
    "operating_profit", "finance_costs", "profit_before_tax", "tax_expense",
    "profit_after_tax", "dividends_paid",
    # SFP
    "total_assets", "non_current_assets", "current_assets", "inventory",
    "trade_receivables", "cash", "total_liabilities",
    "current_liabilities", "trade_payables", "non_current_liabilities",
    "total_equity", "share_capital",
    # cash flow
    "operating_cash_flow",
]


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        s = str(value).strip().replace(",", "")
        if s in ("", "-", "nan", "None"):
            return None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _pct(num: Decimal, den: Decimal) -> Decimal | None:
    if den == 0:
        return None
    return (num / den * 100).quantize(Decimal("0.01"))


def _x(num: Decimal, den: Decimal) -> Decimal | None:
    if den == 0:
        return None
    return (num / den).quantize(Decimal("0.01"))


def _days(balance: Decimal, flow: Decimal) -> Decimal | None:
    if flow == 0:
        return None
    return (balance / flow * 365).quantize(Decimal("0.1"))


# name -> (label, category, required items, function)
_RATIOS: list[tuple[str, str, str, list[str], Any]] = [
    ("gross_margin", "Gross profit margin %", "profitability",
     ["gross_profit", "revenue"],
     lambda d: _pct(d["gross_profit"], d["revenue"])),
    ("net_margin", "Net profit margin %", "profitability",
     ["profit_after_tax", "revenue"],
     lambda d: _pct(d["profit_after_tax"], d["revenue"])),
    ("operating_margin", "Operating profit margin %", "profitability",
     ["operating_profit", "revenue"],
     lambda d: _pct(d["operating_profit"], d["revenue"])),
    ("roce", "Return on capital employed %", "profitability",
     ["operating_profit", "total_assets", "current_liabilities"],
     lambda d: _pct(d["operating_profit"],
                    d["total_assets"] - d["current_liabilities"])),
    ("roe", "Return on equity %", "profitability",
     ["profit_after_tax", "total_equity"],
     lambda d: _pct(d["profit_after_tax"], d["total_equity"])),
    ("current_ratio", "Current ratio (x)", "liquidity",
     ["current_assets", "current_liabilities"],
     lambda d: _x(d["current_assets"], d["current_liabilities"])),
    ("quick_ratio", "Quick (acid-test) ratio (x)", "liquidity",
     ["current_assets", "inventory", "current_liabilities"],
     lambda d: _x(d["current_assets"] - d["inventory"],
                  d["current_liabilities"])),
    ("gearing", "Gearing — debt / equity %", "solvency",
     ["non_current_liabilities", "total_equity"],
     lambda d: _pct(d["non_current_liabilities"], d["total_equity"])),
    ("interest_cover", "Interest cover (x)", "solvency",
     ["operating_profit", "finance_costs"],
     lambda d: _x(d["operating_profit"], d["finance_costs"])),
    ("asset_turnover", "Asset turnover (x)", "efficiency",
     ["revenue", "total_assets"],
     lambda d: _x(d["revenue"], d["total_assets"])),
    ("receivable_days", "Receivable days", "efficiency",
     ["trade_receivables", "revenue"],
     lambda d: _days(d["trade_receivables"], d["revenue"])),
    ("inventory_days", "Inventory days", "efficiency",
     ["inventory", "cost_of_sales"],
     lambda d: _days(d["inventory"], d["cost_of_sales"])),
    ("payable_days", "Payable days", "efficiency",
     ["trade_payables", "cost_of_sales"],
     lambda d: _days(d["trade_payables"], d["cost_of_sales"])),
    ("cash_conversion_cycle", "Cash conversion cycle (days)", "efficiency",
     ["trade_receivables", "revenue", "inventory", "cost_of_sales",
      "trade_payables"],
     lambda d: (_days(d["trade_receivables"], d["revenue"])
                + _days(d["inventory"], d["cost_of_sales"])
                - _days(d["trade_payables"], d["cost_of_sales"])
                if all(v is not None for v in
                       (_days(d["trade_receivables"], d["revenue"]),
                        _days(d["inventory"], d["cost_of_sales"]),
                        _days(d["trade_payables"], d["cost_of_sales"])))
                else None)),
    ("ocf_to_profit", "Operating cash flow / profit after tax (x)", "cash",
     ["operating_cash_flow", "profit_after_tax"],
     lambda d: _x(d["operating_cash_flow"], d["profit_after_tax"])),
    ("dividend_cover", "Dividend cover (x)", "cash",
     ["profit_after_tax", "dividends_paid"],
     lambda d: _x(d["profit_after_tax"], d["dividends_paid"])),
]


def compute_ratios(inputs: dict[str, Any]) -> dict:
    """Compute all ratios whose inputs are present.

    Returns {"ratios": {name: {label, category, value, unit, inputs_used}},
             "skipped": [names]}. Values are Decimals; None never appears
    in ratios (a None result is reported as skipped with a reason).
    """
    data = {k: _dec(v) for k, v in inputs.items()}
    ratios, skipped = {}, []
    for name, label, category, required, func in _RATIOS:
        missing = [c for c in required if data.get(c) is None]
        if missing:
            skipped.append({"ratio": name, "reason": f"missing: {missing}"})
            continue
        try:
            value = func({c: data[c] for c in required})
        except (InvalidOperation, ArithmeticError):
            skipped.append({"ratio": name, "reason": "arithmetic error"})
            continue
        if value is None:
            skipped.append({"ratio": name,
                            "reason": "zero denominator or undefined"})
            continue
        unit = "%" if label.endswith("%") else (
            "x" if "(x)" in label else ("days" if "days" in label.lower()
                                        else ""))
        ratios[name] = {"label": label, "category": category,
                        "value": value, "unit": unit,
                        "inputs_used": required}
    return {"ratios": ratios, "skipped": skipped}


def common_size(pl: dict[str, Any], sfp: dict[str, Any]) -> dict:
    """Common-size statements: P&L lines as % of revenue, SFP as % of assets."""
    rev = _dec(pl.get("revenue"))
    ta = _dec(sfp.get("total_assets"))
    pl_cs = {k: (float(_pct(_dec(v), rev)) if rev and _dec(v) is not None else None)
             for k, v in pl.items()}
    sfp_cs = {k: (float(_pct(_dec(v), ta)) if ta and _dec(v) is not None else None)
              for k, v in sfp.items()}
    return {"profit_and_loss_pct_of_revenue": pl_cs,
            "sfp_pct_of_total_assets": sfp_cs}


def trend_analysis(periods: list[dict]) -> dict:
    """Period-over-period ratio trends.

    periods: [{label, inputs}]. Returns {ratio_name: {values: [...],
    direction: up|down|flat|mixed|insufficient}}.
    """
    computed = [compute_ratios(p["inputs"])["ratios"] for p in periods]
    labels = [p["label"] for p in periods]
    names = set()
    for c in computed:
        names.update(c.keys())
    out = {}
    for name in sorted(names):
        values = [c[name]["value"] if name in c else None for c in computed]
        present = [v for v in values if v is not None]
        if len(present) < 2:
            direction = "insufficient"
        else:
            diffs = [b - a for a, b in zip(present, present[1:])]
            if all(d > 0 for d in diffs):
                direction = "up"
            elif all(d < 0 for d in diffs):
                direction = "down"
            elif all(d == 0 for d in diffs):
                direction = "flat"
            else:
                direction = "mixed"
        out[name] = {"label": computed[0][name]["label"] if name in computed[0]
                     else next(c[name]["label"] for c in computed if name in c),
                     "values": [(labels[i], str(v) if v is not None else None)
                                for i, v in enumerate(values)],
                     "direction": direction}
    return out

"""Red-flag indicators (Phase 8).

Each indicator is a *prompt for investigation* — never proof of error
or fraud. A flag fires only on computed ratios (never on missing
data), and every flag carries: what was observed, why it can matter,
and what to investigate next.
"""
from __future__ import annotations

from decimal import Decimal

INVESTIGATE = ("Indicator only — not evidence of misstatement. "
               "Investigate before concluding anything.")


def _v(ratios: dict, name: str) -> Decimal | None:
    r = ratios.get(name)
    return r["value"] if r else None


def evaluate_flags(ratios: dict, trends: dict | None = None) -> list[dict]:
    """Evaluate red-flag rules against computed ratios (+ optional trends)."""
    flags: list[dict] = []

    def add(code, title, severity, observed, why, investigate):
        flags.append({"code": code, "title": title, "severity": severity,
                      "observed": observed, "why_it_can_matter": why,
                      "investigate": investigate + " " + INVESTIGATE})

    cr = _v(ratios, "current_ratio")
    if cr is not None and cr < 1:
        add("LIQ-01", "Current ratio below 1", "warning",
            f"Current ratio is {cr}x.",
            "Current liabilities exceed current assets — the business may "
            "struggle to meet short-term obligations as they fall due.",
            "Check the composition of current assets/liabilities, unused "
            "facilities, and post-year-end cash flows.")

    ocf = _v(ratios, "ocf_to_profit")
    if ocf is not None and ocf < Decimal("0.8"):
        add("EARN-01", "Operating cash flow trails profit", "warning",
            f"Operating cash flow is {ocf}x profit after tax.",
            "Persistent gaps between profit and cash can signal aggressive "
            "revenue recognition, weak collections, or heavy working-capital "
            "absorption (overtrading).",
            "Reconcile profit to operating cash flow; inspect receivable "
            "days and revenue cut-off.")

    if ocf is not None and ocf < 0:
        add("EARN-02", "Negative operating cash flow", "warning",
            "Operating cash flow is negative while profit is reported.",
            "A business that cannot generate cash from operations depends "
            "on financing — check sustainability.",
            "Review the cash flow statement line by line; compare with "
            "prior periods.")

    gear = _v(ratios, "gearing")
    if gear is not None and gear > 100:
        add("SOLV-01", "Gearing above 100%", "warning",
            f"Gearing is {gear}%.",
            "Debt exceeds equity — the capital structure is highly "
            "leveraged and vulnerable to interest-rate or earnings shocks.",
            "Check debt maturity profile, covenants, and interest cover.")

    ic = _v(ratios, "interest_cover")
    if ic is not None and ic < Decimal("1.5"):
        add("SOLV-02", "Thin interest cover", "warning",
            f"Interest cover is {ic}x.",
            "Operating profit barely covers finance costs — a small "
            "earnings dip could breach obligations.",
            "Stress-test earnings; review covenant headroom.")

    rd = _v(ratios, "receivable_days")
    if trends and rd is not None:
        t = trends.get("receivable_days", {})
        if t.get("direction") == "up":
            add("EFF-01", "Receivable days rising", "info",
                f"Receivable days are {rd} and trending up.",
                "Slower collections tie up cash and can precede bad debts.",
                "Age the receivables ledger; check provision adequacy and "
                "credit terms vs prior periods.")

    inv = _v(ratios, "inventory_days")
    if trends and inv is not None:
        t = trends.get("inventory_days", {})
        if t.get("direction") == "up":
            add("EFF-02", "Inventory days rising", "info",
                f"Inventory days are {inv} and trending up.",
                "Can indicate overstocking, obsolescence, or falling demand.",
                "Review slow-moving lines; check NRV provisions (IAS 2).")

    gm = _v(ratios, "gross_margin")
    if trends and gm is not None:
        t = trends.get("gross_margin", {})
        if t.get("direction") == "down":
            add("PROF-01", "Gross margin declining", "info",
                f"Gross margin is {gm}% and trending down.",
                "Margin pressure from pricing, mix, or cost inflation.",
                "Decompose by product/customer; compare cost of sales "
                "trends with revenue.")

    return flags

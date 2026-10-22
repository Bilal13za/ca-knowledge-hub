"""Treatment suggestion engine (Phase 4).

Rule-based mapping from transaction characteristics to *candidate*
standards/treatments. Suggestions are investigation prompts — the
module NEVER asserts that a standard applies. Every suggestion carries
the instruction to verify against the official standard text.

Deterministic: same characteristics -> same suggestions, same order.
"""
from __future__ import annotations

DISCLAIMER = (
    "These are candidate standards to investigate — not a determination. "
    "A standard applies only if its scope and criteria are met; verify "
    "against the official standard text (no paragraph numbers are cited "
    "in this module, by policy)."
)

# characteristic -> [(standard_id, why)] — ordered by relevance
_CHARACTERISTIC_MAP: dict[str, list[tuple[str, str]]] = {
    "customer_contract": [
        ("IFRS 15", "a contract with a customer to transfer goods or services"),
    ],
    "sale_of_goods": [
        ("IFRS 15", "revenue from transferring goods to a customer"),
        ("IAS 2", "the goods sold came out of inventory"),
    ],
    "rendering_services": [
        ("IFRS 15", "revenue from services transferred over time or at a point in time"),
    ],
    "inventory_held": [
        ("IAS 2", "cost vs net realisable value measurement"),
    ],
    "ppe_acquired": [
        ("IAS 16", "recognition, cost and depreciation of PPE"),
        ("IAS 36", "check whether impairment indicators exist"),
    ],
    "lease_arrangement": [
        ("IFRS 16", "lessee right-of-use asset and lease liability"),
    ],
    "uncertain_obligation": [
        ("IAS 37", "provision vs contingent liability assessment"),
    ],
    "financial_asset": [
        ("IFRS 9", "classification by business model and SPPI"),
    ],
    "financial_liability": [
        ("IFRS 9", "financial liability classification and measurement"),
    ],
    "impairment_indicators": [
        ("IAS 36", "recoverable amount vs carrying amount"),
    ],
    "tax_effects": [
        ("IAS 12", "current and deferred tax on temporary differences"),
    ],
    "intangible_asset": [
        ("IAS 38", "research vs development, amortisation"),
        ("IAS 36", "annual impairment test if indefinite-lived"),
    ],
    "borrowing_costs": [
        ("IAS 16", "borrowing costs may form part of asset cost for qualifying assets"),
    ],
}

CHARACTERISTICS = [
    ("customer_contract", "Contract with a customer"),
    ("sale_of_goods", "Sale of goods"),
    ("rendering_services", "Rendering of services"),
    ("inventory_held", "Inventory held / purchased"),
    ("ppe_acquired", "PPE acquired / constructed"),
    ("lease_arrangement", "Lease arrangement"),
    ("uncertain_obligation", "Uncertain obligation / lawsuit / warranty"),
    ("financial_asset", "Financial asset (receivable, investment, loan)"),
    ("financial_liability", "Financial liability (loan, payable, bond)"),
    ("impairment_indicators", "Possible impairment indicators"),
    ("tax_effects", "Tax effects / temporary differences"),
    ("intangible_asset", "Intangible asset / R&D"),
    ("borrowing_costs", "Borrowing costs on a qualifying asset"),
]


def suggest(characteristics: list[str], conn=None) -> dict:
    """Return candidate standards for the given characteristics.

    Returns {"candidates": [{"standard_id", "title", "why",
    "triggered_by": [...], "treatments": [...]}], "disclaimer": ...}.
    Empty characteristics -> no candidates (never guess).
    """
    seen: dict[str, dict] = {}
    order: list[str] = []
    for ch in characteristics:
        for std_id, why in _CHARACTERISTIC_MAP.get(ch, []):
            if std_id not in seen:
                seen[std_id] = {"standard_id": std_id, "why": [why],
                                "triggered_by": [ch]}
                order.append(std_id)
            else:
                if why not in seen[std_id]["why"]:
                    seen[std_id]["why"].append(why)
                if ch not in seen[std_id]["triggered_by"]:
                    seen[std_id]["triggered_by"].append(ch)
    candidates = []
    for std_id in order:
        c = seen[std_id]
        title = None
        treatments: list[dict] = []
        if conn is not None:
            row = conn.execute(
                "SELECT title FROM fr_standards WHERE id = ?",
                (std_id,)).fetchone()
            title = row["title"] if row else None
            treatments = [
                {"id": r[0], "title": r[1]} for r in conn.execute(
                    "SELECT t.id, t.title FROM fr_treatments t "
                    "JOIN fr_treatment_standard l ON l.treatment_id = t.id "
                    "WHERE l.standard_id = ? ORDER BY t.id", (std_id,))]
        candidates.append({
            "standard_id": std_id, "title": title,
            "why": c["why"], "triggered_by": c["triggered_by"],
            "treatments": treatments,
        })
    return {"candidates": candidates, "disclaimer": DISCLAIMER}

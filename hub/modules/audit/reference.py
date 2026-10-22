"""Fixed reference data for the audit module.

Ported from the Audit Risk and Evidence Library
(``~/workspace/audit-risk-library/db.py``) under Phase 0 decision MIGRATE.
Assertions use ISA 315 (Revised) terminology; paragraph numbers are
intentionally NOT cited (see the source app's docs/REFERENCES.md).
"""

# (id, category, name, description, framework_note)
ASSERTIONS = [
    ("TRN-OCC", "Transactions and events", "Occurrence",
     "Transactions and events that have been recorded have occurred and pertain to the entity.",
     "Assertions about classes of transactions and events."),
    ("TRN-COM", "Transactions and events", "Completeness",
     "All transactions and events that should have been recorded have been recorded.",
     "Assertions about classes of transactions and events."),
    ("TRN-ACC", "Transactions and events", "Accuracy",
     "Amounts and other data relating to recorded transactions and events have been recorded appropriately.",
     "Assertions about classes of transactions and events."),
    ("TRN-CUT", "Transactions and events", "Cut-off",
     "Transactions and events have been recorded in the correct accounting period.",
     "Assertions about classes of transactions and events."),
    ("TRN-CLS", "Transactions and events", "Classification",
     "Transactions and events have been recorded in the proper accounts.",
     "Assertions about classes of transactions and events."),
    ("BAL-EXI", "Account balances", "Existence",
     "Assets, liabilities and equity interests exist.",
     "Assertions about account balances at period end."),
    ("BAL-RGT", "Account balances", "Rights and obligations",
     "The entity holds or controls the rights to assets, and liabilities are the obligations of the entity.",
     "Assertions about account balances at period end."),
    ("BAL-COM", "Account balances", "Completeness",
     "All assets, liabilities and equity interests that should have been recorded have been recorded.",
     "Assertions about account balances at period end."),
    ("BAL-VAL", "Account balances", "Accuracy, valuation and allocation",
     "Assets, liabilities and equity interests have been included in the financial statements at appropriate amounts and any resulting valuation or allocation adjustments have been appropriately recorded.",
     "Assertions about account balances at period end."),
    ("BAL-CLS", "Account balances", "Classification",
     "Assets, liabilities and equity interests have been recorded in the proper accounts.",
     "Assertions about account balances at period end."),
    ("BAL-PRS", "Account balances", "Presentation",
     "Assets, liabilities and equity interests are appropriately aggregated or disaggregated and clearly described, and related disclosures are relevant and understandable.",
     "Assertions about account balances at period end."),
    ("DIS-OCC", "Presentation and disclosure", "Occurrence and rights and obligations",
     "Disclosed events, transactions and other matters have occurred and pertain to the entity.",
     "Assertions about presentation and disclosure."),
    ("DIS-COM", "Presentation and disclosure", "Completeness",
     "All disclosures that should have been included in the financial statements have been included.",
     "Assertions about presentation and disclosure."),
    ("DIS-CLS", "Presentation and disclosure", "Classification and understandability",
     "Financial information is appropriately presented and described, and disclosures are clearly expressed.",
     "Assertions about presentation and disclosure."),
    ("DIS-VAL", "Presentation and disclosure", "Accuracy and valuation",
     "Financial and other information is disclosed fairly and at appropriate amounts.",
     "Assertions about presentation and disclosure."),
]

# (id, name, description)
CYCLES = [
    ("CYC-REV", "Revenue and receivables",
     "Order to cash: sales orders, dispatch, billing, credit notes, cash collection, trade receivables and related allowances."),
    ("CYC-PUR", "Purchases and payables",
     "Procure to pay: supplier selection, purchase orders, goods receipt, invoice matching, payments, trade payables and accruals."),
    ("CYC-INV", "Inventory",
     "Inventory receipt, storage, movement, counting, valuation (including cost and net realisable value), and obsolescence."),
    ("CYC-PAY", "Payroll",
     "Hiring, timekeeping, payroll calculation, payment, deductions, and related liabilities and disclosures."),
    ("CYC-CSH", "Cash and bank",
     "Cash handling, bank accounts, receipts, payments, transfers, reconciliations and petty cash."),
    ("CYC-PPE", "Property, plant and equipment",
     "Acquisition, capitalisation, depreciation, impairment, disposals and physical safeguarding of fixed assets."),
    ("CYC-INVST", "Investments",
     "Acquisition, valuation, income recognition and disposal of investments. (Library content not yet populated.)"),
    ("CYC-BOR", "Borrowings",
     "Loan origination, drawdown, interest, covenants and repayment. (Library content not yet populated.)"),
    ("CYC-PROV", "Provisions and contingencies",
     "Recognition, measurement and disclosure of provisions, contingent liabilities and contingent assets."),
    ("CYC-FRP", "Financial reporting and closing",
     "Period-end close, journal entries, consolidation, management estimates, related parties and financial statement disclosures."),
    ("CYC-TAX", "Taxation",
     "Current and deferred tax computation, compliance and disclosure. (Library content not yet populated.)"),
]

# Source library review_status -> Hub verification_status
REVIEW_TO_VERIFICATION = {
    "Verified": "verified",
    "Draft": "user_note",
    "Under review": "extracted_unverified",
    "Retired": "superseded",
}

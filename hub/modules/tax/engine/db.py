"""Hub adapter for the ported tax engine.

The standalone tax engine used two SQLite files (tax_knowledge.db /
tax_workdata.db). Inside the Hub there is exactly one database; the
knowledge / working-data separation is preserved as a *namespaced*
table split (all tables ``tax_``-prefixed — see ``../schema.sql``).

This module therefore does NOT open connections. The Hub core owns the
connection and passes it explicitly to every engine entry point.
"""
from __future__ import annotations

# Canonical table names inside the hub database.
TABLES = {
    # knowledge
    "sources": "tax_sources",
    "legislation": "tax_legislation",
    "rules": "tax_rules",
    "risks": "tax_risks",
    "evidence": "tax_evidence",
    "procedures": "tax_procedures",
    "calc_tables": "tax_calc_tables",
    "scenarios": "tax_scenarios",
    "rule_legislation": "tax_rule_legislation",
    "rule_risks": "tax_rule_risks",
    "rule_evidence": "tax_rule_evidence",
    "rule_procedures": "tax_rule_procedures",
    "rule_calcs": "tax_rule_calcs",
    "risk_evidence": "tax_risk_evidence",
    "risk_procedures": "tax_risk_procedures",
    # working data
    "profiles": "tax_profiles",
    "assessments": "tax_assessments",
    "assessment_steps": "tax_assessment_steps",
    "evidence_tracker": "tax_evidence_tracker",
    "reconciliations": "tax_reconciliations",
    "calculation_runs": "tax_calculation_runs",
    "export_log": "tax_export_log",
}


def get_knowledge_db():  # pragma: no cover
    raise RuntimeError(
        "The Hub owns the database connection: pass the hub connection "
        "explicitly to the tax engine entry points (e.g. "
        "loader.load_seed_file(path, conn=conn))."
    )


def get_workdata_db():  # pragma: no cover
    raise RuntimeError(
        "The Hub owns the database connection: working-data tables live in "
        "the same hub database (tax_-prefixed). Pass the hub connection "
        "explicitly."
    )

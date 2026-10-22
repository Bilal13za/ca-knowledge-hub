"""Pakistan tax rules engine — ported into the CA Knowledge Hub (Phase 3).

Deterministic, offline, no AI: the 14-step analysis chain (decision.py),
tri-state condition evaluation, date-scoped rule/calc selection
(calc.py), seed validation (validate.py) and loading (loader.py).

Table names are ``tax_``-prefixed to live in the single hub database;
knowledge tables and working-data tables are namespaced apart (the
source engine's two-DB discipline, preserved as a documented split).
"""
from __future__ import annotations

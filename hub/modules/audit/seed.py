"""Audit module seeder (Phase 2).

Loads the staged seed JSONs (``data/seed/seed_*.json``) and rule definitions
(``data/rules/RULE-*.json``) into the Hub's ``audit_*`` tables. Idempotent:
safe to re-run after editing the JSONs (INSERT OR REPLACE throughout).

The JSONs remain the editable, no-code source of truth (spec section 9):
edit a file, re-run this seeder, re-run the tests.

Also rebuilds lightweight knowledge_records stubs (module='audit') so the
Hub's global search finds audit content; each stub links back to its
authority row via extension_json.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .reference import ASSERTIONS, CYCLES, REVIEW_TO_VERIFICATION

MODULE = "audit"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _vstatus(review_status: str | None) -> str:
    return REVIEW_TO_VERIFICATION.get(review_status or "Draft", "user_note")


def _insert_or_replace(conn: sqlite3.Connection, table: str, row: dict) -> None:
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    conn.execute(
        f'INSERT OR REPLACE INTO "{table}" ({cols}) VALUES ({placeholders})',
        list(row.values()),
    )


def seed_audit(conn: sqlite3.Connection, data_dir: str | Path) -> dict:
    """Seed the audit module. Returns {table: row_count}."""
    data_dir = Path(data_dir)
    schema_sql = (data_dir.parent / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema_sql)

    counts: dict[str, int] = {}

    # fixed reference data
    for a in ASSERTIONS:
        _insert_or_replace(conn, "audit_assertions", {
            "id": a[0], "category": a[1], "name": a[2],
            "description": a[3], "framework_note": a[4]})
    for c in CYCLES:
        _insert_or_replace(conn, "audit_cycles", {
            "id": c[0], "name": c[1], "description": c[2],
            "review_status": "Verified"})
    counts["audit_assertions"] = len(ASSERTIONS)
    counts["audit_cycles"] = len(CYCLES)

    # seed files
    for path in sorted((data_dir / "seed").glob("seed_*.json")):
        doc = _load_json(path)
        for f in doc.get("factors", []):
            _insert_or_replace(conn, "audit_factors", {
                "id": f["id"], "name": f["name"], "description": f["description"],
                "cycle_id": f["cycle_id"], "risk_category": f["risk_category"],
                "conditions_relevant": f.get("conditions_relevant"),
                "warning_signs": f.get("warning_signs"),
                "source_reference": f.get("source_reference"),
                "review_status": f.get("review_status", "Draft")})
        for r in doc.get("risks", []):
            _insert_or_replace(conn, "audit_risks", {
                "id": r["id"], "title": r["title"], "description": r["description"],
                "causes": r.get("causes"),
                "potential_consequences": r.get("potential_consequences"),
                "cycle_id": r["cycle_id"],
                "inherent_risk_notes": r.get("inherent_risk_notes"),
                "source_reference": r.get("source_reference"),
                "review_status": r.get("review_status", "Draft")})
        for fr in doc.get("factor_risk", []):
            _insert_or_replace(conn, "audit_factor_risk", {
                "factor_id": fr["factor_id"], "risk_id": fr["risk_id"],
                "trigger_condition": fr.get("trigger_condition"),
                "applicability": fr.get("applicability"),
                "explanation": fr["explanation"],
                "additional_info_needed": fr.get("additional_info_needed"),
                "confidence_basis": fr.get("confidence_basis"),
                "source_reference": fr.get("source_reference"),
                "reviewer": fr.get("reviewer"),
                "review_status": fr.get("review_status", "Draft")})
        for ra in doc.get("risk_assertions", []):
            _insert_or_replace(conn, "audit_risk_assertion", {
                "risk_id": ra["risk_id"], "assertion_id": ra["assertion_id"],
                "why_relevant": ra["why_relevant"], "conditions": ra.get("conditions")})
        for c_ in doc.get("controls", []):
            _insert_or_replace(conn, "audit_controls", {
                "id": c_["id"], "description": c_["description"],
                "objective": c_.get("objective"),
                "preventive_detective": c_.get("preventive_detective"),
                "manual_automated": c_.get("manual_automated"),
                "frequency": c_.get("frequency"),
                "responsible_role": c_.get("responsible_role"),
                "evidence_of_operation": c_.get("evidence_of_operation"),
                "limitations": c_.get("limitations"),
                "source_reference": c_.get("source_reference"),
                "review_status": c_.get("review_status", "Draft")})
        for rc in doc.get("risk_controls", []):
            _insert_or_replace(conn, "audit_risk_control", {
                "risk_id": rc["risk_id"], "control_id": rc["control_id"],
                "explanation": rc.get("explanation")})
        for p in doc.get("procedures", []):
            steps = p["steps"]
            if isinstance(steps, list):
                steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
            _insert_or_replace(conn, "audit_procedures", {
                "id": p["id"], "title": p["title"], "objective": p["objective"],
                "steps": steps, "procedure_type": p["procedure_type"],
                "test_type": p["test_type"], "population": p.get("population"),
                "sampling_notes": p.get("sampling_notes"),
                "expected_result": p["expected_result"],
                "exception_criteria": p["exception_criteria"],
                "follow_up": p["follow_up"],
                "source_reference": p.get("source_reference"),
                "review_status": p.get("review_status", "Draft")})
        for rp in doc.get("risk_procedures", []):
            _insert_or_replace(conn, "audit_risk_procedure", {
                "risk_id": rp["risk_id"], "procedure_id": rp["procedure_id"],
                "reason": rp.get("reason")})
        for e in doc.get("evidence", []):
            _insert_or_replace(conn, "audit_evidence", {
                "id": e["id"], "name": e["name"], "description": e["description"],
                "source": e.get("source"),
                "reliability_notes": e["reliability_notes"],
                "limitations": e.get("limitations"),
                "expected_characteristics": e.get("expected_characteristics"),
                "contradictory_evidence": e.get("contradictory_evidence"),
                "source_reference": e.get("source_reference"),
                "review_status": e.get("review_status", "Draft")})
        for pa in doc.get("procedure_assertions", []):
            _insert_or_replace(conn, "audit_procedure_assertion", {
                "procedure_id": pa["procedure_id"], "assertion_id": pa["assertion_id"]})
        for pe in doc.get("procedure_evidence", []):
            _insert_or_replace(conn, "audit_procedure_evidence", {
                "procedure_id": pe["procedure_id"], "evidence_id": pe["evidence_id"],
                "notes": pe.get("notes")})

    # rule definitions (editable JSON -> audit_rules)
    n_rules = 0
    for path in sorted((data_dir / "rules").glob("RULE-*.json")):
        rule = _load_json(path)
        _insert_or_replace(conn, "audit_rules", {
            "id": rule["rule_id"], "name": rule["name"],
            "version": rule.get("version", 1),
            "priority": rule.get("priority", 100),
            "effective_date": rule.get("effective_date"),
            "status": rule.get("status", "Active"),
            "definition": json.dumps(rule.get("definition", rule)),
            "rationale": rule.get("rationale"),
            "source_reference": rule.get("source_reference"),
            "reviewed_by": rule.get("reviewed_by"),
            "review_status": rule.get("review_status", "Draft")})
        n_rules += 1

    for table in ("audit_factors", "audit_risks", "audit_controls",
                  "audit_procedures", "audit_evidence", "audit_rules"):
        counts[table] = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

    conn.execute(
        "INSERT INTO audit_builds (built_at, note) VALUES (datetime('now'), ?)",
        (f"seeded {sum(counts.values())} rows from data/seed + data/rules",),
    )

    _rebuild_search_stubs(conn)
    counts["knowledge_records(audit)"] = conn.execute(
        "SELECT COUNT(*) FROM knowledge_records WHERE module='audit'"
    ).fetchone()[0]
    return counts


def _rebuild_search_stubs(conn: sqlite3.Connection) -> None:
    """Rebuild lightweight global-search stubs for audit entities.

    The audit_* tables are the authority; stubs are searchable pointers
    (never edited by hand — regenerated on every seed).
    """
    conn.execute("DELETE FROM record_fts WHERE module='audit'")
    conn.execute("DELETE FROM knowledge_records WHERE module='audit'")

    def stub(*, topic, title, description, content, verification_status,
             entity, entity_id, keywords=""):
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('audit',?,?,?,?,?,?,?)""",
            (topic, title, description, keywords, content, verification_status,
             json.dumps({"audit_entity": entity, "audit_id": entity_id})),
        )
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content, record_id, module)"
            " VALUES (?,?,?,?,?,?)",
            (title, description, keywords, content, rid, "audit"),
        )

    cycles = {r[0]: r[1] for r in
              conn.execute("SELECT id, name FROM audit_cycles")}
    for r in conn.execute("SELECT * FROM audit_rules WHERE status='Active'"):
        d = json.loads(r["definition"])
        then = d.get("then", {})
        stub(topic="rule", title=f"{r['id']}: {r['name']}",
             description=(r["rationale"] or "")[:500],
             content=f"Rule {r['id']} v{r['version']} (priority {r['priority']}). "
                     f"Rationale: {r['rationale'] or ''} "
                     f"Note: {then.get('note', '')}",
             verification_status=_vstatus(r["review_status"]),
             entity="rule", entity_id=r["id"],
             keywords="audit rule risk")
    for p in conn.execute("SELECT * FROM audit_procedures"):
        stub(topic="procedure",
             title=f"{p['id']}: {p['title']}",
             description=(p["objective"] or "")[:500],
             content=f"{p['objective']}\nSteps:\n{p['steps']}\n"
                     f"Expected result: {p['expected_result']}\n"
                     f"Exception criteria: {p['exception_criteria']}",
             verification_status=_vstatus(p["review_status"]),
             entity="procedure", entity_id=p["id"],
             keywords=f"audit procedure {p['procedure_type']} {p['test_type']}")
    for f in conn.execute("SELECT * FROM audit_factors"):
        stub(topic="factor",
             title=f"{f['id']}: {f['name']}",
             description=(f["description"] or "")[:500],
             content=f"Cycle: {cycles.get(f['cycle_id'], f['cycle_id'])}. "
                     f"Risk category: {f['risk_category']}. {f['description']}",
             verification_status=_vstatus(f["review_status"]),
             entity="factor", entity_id=f["id"],
             keywords="audit risk factor")

"""Deterministic rule engine for the audit module (Phase 2).

Ported from the Audit Risk and Evidence Library's engine.py (Phase 0
decision MIGRATE). Pure stdlib, no AI, no network, no randomness: the
same database version + the same inputs always produce the same output.
Rules evaluate in (priority, id, version) order; every merge is
order-stable.

Rule JSON format (editable in modules/audit/data/rules/*.json):
    when: {all: [...], any: [...], exclude: [...]}
    then: {risk_ids, assertion_ids, control_ids, procedure_ids,
           missing_information, note}
Condition types: factor_selected, cycle_selected.
"""
from __future__ import annotations

import json
import sqlite3


def load_rule_definitions(rules_dir) -> dict:
    """Read editable rule JSONs. Returns {rule_id: rule_dict}."""
    from pathlib import Path

    out = {}
    for path in sorted(Path(rules_dir).glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Rule file {path.name}: invalid JSON ({exc})")
        rules = doc if isinstance(doc, list) else [doc]
        for rule in rules:
            rid = rule.get("rule_id") or path.stem
            out[rid] = rule
    return out


class RuleEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ------------------------------------------------------------------ API

    def assess(self, selected_factor_ids, cycle_ids=None) -> dict:
        """Run the full assessment.

        Returns triggered rules plus a consolidated, deduplicated
        risk-and-testing plan. A selected factor is a *risk indicator
        requiring testing* — never proof that a misstatement exists.
        """
        selected = sorted(set(selected_factor_ids or []))
        cycles = sorted(set(cycle_ids or []))
        rules = self._active_rules()

        triggered = []
        for rule in rules:
            definition = json.loads(rule["definition"])
            matched, missing = self._evaluate(definition, selected, cycles)
            if matched:
                then = definition.get("then", {})
                triggered.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "version": rule["version"],
                    "priority": rule["priority"],
                    "effective_date": rule["effective_date"],
                    "rationale": rule["rationale"],
                    "source_reference": rule["source_reference"],
                    "review_status": rule["review_status"],
                    "missing_information": then.get("missing_information", []),
                    "unmet_conditions": missing,
                })

        plan = self._build_plan(triggered, selected)
        plan["selected_factor_ids"] = selected
        plan["cycle_ids"] = cycles
        plan["triggered_rules"] = triggered
        return plan

    # ------------------------------------------------------------- internals

    def _active_rules(self):
        return self.conn.execute(
            "SELECT * FROM audit_rules WHERE status = 'Active' "
            "ORDER BY priority, id, version"
        ).fetchall()

    def _evaluate(self, definition, selected, cycles):
        """Return (matched, missing) for one rule definition."""
        when = definition.get("when", {}) or {}
        then = definition.get("then", {}) or {}
        all_conds = when.get("all", []) or []
        any_conds = when.get("any", []) or []
        exclude_conds = when.get("exclude", []) or []

        missing: list[str] = []
        for cond in all_conds:
            if not self._holds(cond, selected, cycles):
                missing.append(self._describe(cond))
        any_ok = True
        if any_conds:
            any_ok = any(self._holds(c, selected, cycles) for c in any_conds)
            if not any_ok:
                missing.append("none of the alternative conditions held: "
                               + "; ".join(self._describe(c) for c in any_conds))
        excluded = any(self._holds(c, selected, cycles) for c in exclude_conds)

        matched = not missing and any_ok and not excluded
        # A rule with no outcomes can never "fire" usefully.
        if matched and not any(then.get(k) for k in
                               ("risk_ids", "procedure_ids",
                                "control_ids", "assertion_ids")):
            matched = False
        return matched, missing

    def _holds(self, cond, selected, cycles) -> bool:
        ctype = cond.get("type")
        if ctype == "factor_selected":
            return cond.get("factor_id") in selected
        if ctype == "cycle_selected":
            return cond.get("cycle_id") in cycles
        return False

    @staticmethod
    def _describe(cond) -> str:
        ctype = cond.get("type")
        if ctype == "factor_selected":
            return f"factor {cond.get('factor_id')} selected"
        if ctype == "cycle_selected":
            return f"cycle {cond.get('cycle_id')} selected"
        return f"unknown condition {cond}"

    def _build_plan(self, triggered, selected):
        """Consolidate triggered rules into a deduplicated testing plan.

        Only Verified items appear in the plan (the source library's
        quality gate). Each item records which rules surfaced it.
        """
        risk_ids, proc_ids, ctrl_ids, assert_ids = [], [], [], []
        rule_for: dict[tuple[str, str], set] = {}
        missing_info: list[str] = []

        for t in triggered:
            then = self._rule_definition(t["rule_id"]).get("then", {})
            for bucket, seen in (("risk_ids", risk_ids),
                                 ("procedure_ids", proc_ids),
                                 ("control_ids", ctrl_ids),
                                 ("assertion_ids", assert_ids)):
                for nid in then.get(bucket, []):
                    if nid not in seen:
                        seen.append(nid)
                    rule_for.setdefault((bucket, nid), set()).add(t["rule_id"])
            for mi in t["missing_information"]:
                if mi not in missing_info:
                    missing_info.append(mi)

        return self._plan_from_risks(
            risk_ids, rule_for, missing_info,
            proc_ids=proc_ids, ctrl_ids=ctrl_ids, assert_ids=assert_ids,
            rules_triggered=len(triggered),
            rules_evaluated=len(self._active_rules()),
            selected=selected,
        )

    def _plan_from_risks(self, risk_ids, rule_for, missing_info, *,
                         proc_ids=None, ctrl_ids=None, assert_ids=None,
                         rules_triggered=0, rules_evaluated=0, selected=None):
        """Build the plan dict from a list of risk ids (Verified only)."""
        proc_ids = proc_ids or []
        ctrl_ids = ctrl_ids or []
        assert_ids = assert_ids or []
        risks = []
        for rid in risk_ids:
            r = self._row("audit_risks", rid)
            if r is None or r["review_status"] != "Verified":
                continue
            risks.append({
                "id": r["id"], "title": r["title"],
                "description": r["description"], "causes": r["causes"],
                "potential_consequences": r["potential_consequences"],
                "cycle_id": r["cycle_id"],
                "inherent_risk_notes": r["inherent_risk_notes"],
                "source_reference": r["source_reference"],
                "triggered_by_rules": sorted(rule_for.get(("risk_ids", rid), [])),
                "assertions": self._risk_assertions(rid),
                "controls": self._risk_controls(rid),
                "procedures": self._risk_procedures(rid, rule_for),
            })

        # One procedure may address several risks: present it once,
        # annotated with the risks it addresses.
        consolidated, seen_proc = [], {}
        for risk in risks:
            for p in risk["procedures"]:
                if p["id"] not in seen_proc:
                    entry = dict(p)
                    entry["risk_ids"] = []
                    seen_proc[p["id"]] = entry
                    consolidated.append(entry)
                if risk["id"] not in seen_proc[p["id"]]["risk_ids"]:
                    seen_proc[p["id"]]["risk_ids"].append(risk["id"])

        return {
            "risks": risks,
            "procedures": consolidated,
            "procedure_ids": [p["id"] for p in consolidated],
            "control_ids": ctrl_ids,
            "assertion_ids": assert_ids,
            "missing_information": missing_info,
            "counts": {
                "rules_triggered": rules_triggered,
                "risks": len(risks),
                "procedures": len(consolidated),
                "controls": len(ctrl_ids),
                "assertions": len(assert_ids),
            },
            "rules_evaluated": rules_evaluated,
            "selected_factor_ids": selected or [],
        }

    def plan_for_factor(self, factor_id: str) -> dict:
        """Full chain for one factor via direct factor->risk links
        (no rule evaluation)."""
        row = self._row("audit_factors", factor_id)
        if row is None:
            raise ValueError(f"Unknown factor {factor_id}")
        risk_ids = [r[0] for r in self.conn.execute(
            "SELECT risk_id FROM audit_factor_risk WHERE factor_id = ? "
            "ORDER BY risk_id", (factor_id,))]
        plan = self._plan_from_risks(risk_ids, {}, [], selected=[factor_id])
        plan["factor"] = dict(row)
        return plan

    def _row(self, table, rid):
        return self.conn.execute(
            f'SELECT * FROM "{table}" WHERE id = ?', (rid,)).fetchone()

    def _risk_assertions(self, risk_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT a.id, a.category, a.name, a.description, "
            "ra.why_relevant, ra.conditions "
            "FROM audit_risk_assertion ra "
            "JOIN audit_assertions a ON a.id = ra.assertion_id "
            "WHERE ra.risk_id = ? ORDER BY a.id", (risk_id,))]

    def _risk_controls(self, risk_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT c.*, rc.explanation AS link_explanation "
            "FROM audit_risk_control rc "
            "JOIN audit_controls c ON c.id = rc.control_id "
            "WHERE rc.risk_id = ? AND c.review_status = 'Verified' "
            "ORDER BY c.id", (risk_id,))]

    def _risk_procedures(self, risk_id, rule_for):
        out = []
        for r in self.conn.execute(
            "SELECT p.*, rp.reason AS link_reason "
            "FROM audit_risk_procedure rp "
            "JOIN audit_procedures p ON p.id = rp.procedure_id "
            "WHERE rp.risk_id = ? AND p.review_status = 'Verified' "
            "ORDER BY p.id", (risk_id,)):
            d = dict(r)
            d["triggered_by_rules"] = sorted(
                rule_for.get(("procedure_ids", r["id"]), []))
            d["evidence"] = self._procedure_evidence(r["id"])
            d["assertions"] = [
                a[0] for a in self.conn.execute(
                    "SELECT assertion_id FROM audit_procedure_assertion "
                    "WHERE procedure_id = ? ORDER BY assertion_id", (r["id"],))]
            out.append(d)
        return out

    def _procedure_evidence(self, procedure_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT e.*, pe.notes AS link_notes "
            "FROM audit_procedure_evidence pe "
            "JOIN audit_evidence e ON e.id = pe.evidence_id "
            "WHERE pe.procedure_id = ? AND e.review_status = 'Verified' "
            "ORDER BY e.id", (procedure_id,))]

    def search(self, query, limit=50):
        """Offline substring search across the library (Verified items)."""
        q = f"%{query.strip().lower()}%"
        results = []

        def grab(sql, kind, label, n_params=2):
            for r in self.conn.execute(sql, (q,) * n_params).fetchmany(limit):
                results.append({"kind": kind, "id": r["id"],
                                "label": label.format(**dict(r))})

        grab("SELECT id, name FROM audit_factors WHERE review_status='Verified'"
             " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?) ORDER BY id",
             "factor", "Factor {id}: {name}")
        grab("SELECT id, title AS name FROM audit_risks WHERE review_status='Verified'"
             " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ?) ORDER BY id",
             "risk", "Risk {id}: {name}")
        grab("SELECT id, title AS name FROM audit_procedures WHERE review_status='Verified'"
             " AND (LOWER(title) LIKE ? OR LOWER(steps) LIKE ?) ORDER BY id",
             "procedure", "Procedure {id}: {name}")
        grab("SELECT id, name FROM audit_evidence WHERE review_status='Verified'"
             " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?) ORDER BY id",
             "evidence", "Evidence {id}: {name}")
        grab("SELECT id, description AS name FROM audit_controls WHERE review_status='Verified'"
             " AND (LOWER(description) LIKE ?) ORDER BY id",
             "control", "Control {id}", 1)
        return results[:limit]

    def _rule_definition(self, rule_id: str) -> dict:
        row = self.conn.execute(
            "SELECT definition FROM audit_rules WHERE id = ? AND status='Active' "
            "ORDER BY version DESC LIMIT 1",
            (rule_id,),
        ).fetchone()
        return json.loads(row["definition"]) if row else {}

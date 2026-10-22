"""Hub adapter: load case-engine rows into the shapes the ported
engines expect (Phase 7).

The ported engines (rules_engine, frameworks, recommend,
calculations, studyaids) are pure and unchanged from the standalone
app; this module reads the case_* tables and feeds them in.
"""
from __future__ import annotations

import json


def _j(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return default
    return value


def load_trigger_rules(conn) -> list[dict]:
    """Trigger rules as dicts with a ``triggers`` list (parsed)."""
    rules = []
    for r in conn.execute(
            "SELECT * FROM case_trigger_rules ORDER BY rule_id"):
        d = dict(r)
        d["triggers"] = _j(r["triggers_json"], [])
        rules.append(d)
    return rules


def rule_frameworks(conn, rule_id: str) -> list[dict]:
    """Frameworks mapped to a rule, with rationales."""
    return [dict(r) for r in conn.execute(
        """SELECT f.*, m.rationale FROM case_rule_framework_mappings m
           JOIN case_frameworks f ON f.framework_id = m.framework_id
           WHERE m.rule_id = ? ORDER BY f.framework_id""", (rule_id,))]


def framework_steps(conn, framework_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM case_framework_steps WHERE framework_id = ?"
        " ORDER BY step_no", (framework_id,))]


def get_framework(conn, framework_id: str) -> dict | None:
    r = conn.execute("SELECT * FROM case_frameworks WHERE framework_id = ?",
                     (framework_id,)).fetchone()
    return dict(r) if r else None


def get_question(conn, question_id: str) -> dict | None:
    r = conn.execute(
        "SELECT * FROM case_practice_questions WHERE question_id = ?",
        (question_id,)).fetchone()
    if r is None:
        return None
    q = dict(r)
    q["answer_outlines"] = [dict(x) for x in conn.execute(
        "SELECT * FROM case_answer_outlines WHERE question_id = ?"
        " ORDER BY outline_id", (question_id,))]
    q["marking_rubrics"] = [dict(x) for x in conn.execute(
        "SELECT * FROM case_marking_rubrics WHERE question_id = ?"
        " ORDER BY rubric_id", (question_id,))]
    return q


def record_attempt(conn, question_id: str, answer_text: str,
                   time_taken_min: float | None = None,
                   marks_self: float | None = None,
                   checklist: dict | None = None,
                   notes: str = "") -> int:
    """Record a student practice attempt (student table — never seeded)."""
    cur = conn.execute(
        """INSERT INTO case_student_attempts
           (question_id, attempted_at, time_taken_min, marks_self,
            checklist_json, answer_text, notes)
           VALUES (?, datetime('now'), ?, ?, ?, ?, ?)""",
        (question_id, time_taken_min, marks_self,
         json.dumps(checklist or {}), answer_text, notes))
    conn.commit()
    return cur.lastrowid


def log_mistake(conn, attempt_id: int, topic: str, description: str) -> int:
    cur = conn.execute(
        """INSERT INTO case_mistake_log
           (attempt_id, topic, description, created_at)
           VALUES (?, ?, ?, datetime('now'))""",
        (attempt_id, topic, description))
    conn.commit()
    return cur.lastrowid

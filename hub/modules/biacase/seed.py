"""Phase 7 seeder: BIA/BFD case analysis module.

Adapts the standalone case engine's seed logic: normalises the staged
JSON payloads (bare-list rules.json, key remaps, rule→framework mapping
expansion, problem-pattern derivation) and upserts every row into the
case_-prefixed tables. Student tables are protected — the seeder never
writes to them.

Then registers knowledge_records stubs for global search.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

# source table name -> hub table name
TABLE_MAP = {
    "Sources": "case_sources",
    "Papers": "case_papers",
    "SyllabusVersions": "case_syllabus_versions",
    "Topics": "case_topics",
    "LearningOutcomes": "case_learning_outcomes",
    "Concepts": "case_concepts",
    "Frameworks": "case_frameworks",
    "FrameworkSteps": "case_framework_steps",
    "CasePatterns": "case_patterns",
    "CaseFacts": "case_facts",
    "ProblemPatterns": "case_problem_patterns",
    "TriggerRules": "case_trigger_rules",
    "RuleFrameworkMappings": "case_rule_framework_mappings",
    "Formulas": "case_formulas",
    "CalculationExamples": "case_calculation_examples",
    "DecisionOptions": "case_decision_options",
    "EvaluationCriteria": "case_evaluation_criteria",
    "PracticeQuestions": "case_practice_questions",
    "AnswerOutlines": "case_answer_outlines",
    "MarkingRubrics": "case_marking_rubrics",
    "ReviewRecords": "case_review_records",
    "Flashcards": "case_flashcards",
    "MindMaps": "case_mindmaps",
}

TABLE_ORDER = [
    ("sources", "Sources"),
    ("papers", "Papers"),
    ("syllabus_versions", "SyllabusVersions"),
    ("topics", "Topics"),
    ("learning_outcomes", "LearningOutcomes"),
    ("concepts", "Concepts"),
    ("frameworks", "Frameworks"),
    ("framework_steps", "FrameworkSteps"),
    ("case_patterns", "CasePatterns"),
    ("case_facts", "CaseFacts"),
    ("problem_patterns", "ProblemPatterns"),
    ("trigger_rules", "TriggerRules"),
    ("rule_framework_mappings", "RuleFrameworkMappings"),
    ("formulas", "Formulas"),
    ("calculation_examples", "CalculationExamples"),
    ("decision_options", "DecisionOptions"),
    ("evaluation_criteria", "EvaluationCriteria"),
    ("practice_questions", "PracticeQuestions"),
    ("answer_outlines", "AnswerOutlines"),
    ("marking_rubrics", "MarkingRubrics"),
    ("review_records", "ReviewRecords"),
    ("flashcards", "Flashcards"),
    ("mindmaps", "MindMaps"),
]

FILES = [
    "syllabus.json", "frameworks.json", "concepts.json", "cases.json",
    "rules.json", "questions.json", "rule_frameworks.json", "formulas.json",
    "calculation_examples.json", "flashcards.json", "mindmaps.json",
]

PROTECTED = {"case_student_attempts", "case_mistake_log",
             "case_flashcard_progress"}

# source verification vocabulary -> hub verification_status enum
STATUS_MAP = {
    "verified_official": "verified",
    "verified": "verified",
    "supplementary": "extracted_unverified",
    "provisional_predecessor": "extracted_unverified",
    "unverified": "extracted_unverified",
    "draft": "user_note",
    "pending": "extracted_unverified",
}


def _hub_status(value: str | None) -> str:
    return STATUS_MAP.get((value or "").strip().lower(), "extracted_unverified")


def _normalise_payload(filename: str, payload: object) -> dict:
    if isinstance(payload, list):
        if filename != "rules.json":
            raise ValueError(f"{filename}: unexpected bare JSON list")
        payload = {"trigger_rules": payload}
    if not isinstance(payload, dict):
        raise ValueError(f"{filename}: expected a JSON object")

    if filename == "questions.json" and "questions" in payload:
        payload["practice_questions"] = payload.pop("questions")
    if filename == "rules.json":
        for rows in payload.values():
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict) and "triggers" in row:
                        row["triggers_json"] = row.pop("triggers")

    if filename == "rule_frameworks.json":
        rows: list[dict] = []
        for rule_id, fw_entries in payload.items():
            for i, entry in enumerate(fw_entries or []):
                if isinstance(entry, dict):
                    fw_id = entry.get("framework_id")
                    rationale = entry.get("rationale", "")
                else:
                    fw_id, rationale = entry, ""
                rows.append({"map_id": f"MAP-{rule_id}-{i + 1}",
                             "rule_id": rule_id,
                             "framework_id": fw_id,
                             "rationale": rationale})
        payload = {"rule_framework_mappings": rows}

    rules = payload.get("trigger_rules") or []
    patterns: list[dict] = []
    seen: set[str] = set()
    for rule in rules:
        pid = rule.get("pattern_id") if isinstance(rule, dict) else None
        if pid and pid not in seen:
            seen.add(pid)
            patterns.append({
                "pattern_id": pid,
                "name": str(pid).replace("PAT-", "").replace("-", " ").title(),
                "description": "",
                "indicators": "[]",
            })
    if patterns:
        payload = {"problem_patterns": patterns, **payload}
    return payload


def _upsert_table(conn, table: str, rows: list[dict]) -> tuple[int, list]:
    if table in PROTECTED:
        raise RuntimeError(f"seeder must never write to {table}")
    count, skipped = 0, []
    for row in rows:
        cols = list(row.keys())
        placeholders = ", ".join(["?"] * len(cols))
        sql = (f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) "
               f"VALUES ({placeholders})")
        values = [json.dumps(v) if isinstance(v, (dict, list)) else v
                  for v in (row[c] for c in cols)]
        try:
            conn.execute(sql, values)
        except sqlite3.IntegrityError as exc:
            skipped.append((str(row.get(cols[0])), str(exc)))
            continue
        count += 1
    return count, skipped


def seed_biacase(conn, data_dir: str | Path | None = None) -> dict:
    """Seed the biacase module. Returns {hub_table: row_count}."""
    data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    conn.executescript(
        (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))

    counts: dict[str, int] = {}
    skipped_total = 0
    for filename in FILES:
        path = data_dir / filename
        if not path.exists():
            continue
        payload = _normalise_payload(
            filename, json.loads(path.read_text(encoding="utf-8")))
        for key, source_table in TABLE_ORDER:
            rows = payload.get(key)
            if not rows:
                continue
            hub_table = TABLE_MAP[source_table]
            n, skipped = _upsert_table(conn, hub_table, rows)
            counts[hub_table] = counts.get(hub_table, 0) + n
            skipped_total += len(skipped)
            for pk, err in skipped:
                print(f"seed: skipped {hub_table} row {pk}: {err}",
                      file=sys.stderr)
    conn.commit()
    if skipped_total:
        print(f"seed: {skipped_total} row(s) skipped", file=sys.stderr)

    counts["knowledge_records(biacase)"] = _register_stubs(conn)
    conn.commit()
    return counts


def _register_stubs(conn) -> int:
    """(Re)build knowledge_records stubs for global search. Idempotent."""
    conn.execute("DELETE FROM record_fts WHERE module='biacase'")
    conn.execute("DELETE FROM knowledge_records WHERE module='biacase'")

    def stub(*, topic, title, description, content, entity, entity_id,
             verification_status="extracted_unverified", keywords=""):
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('biacase',?,?,?,?,?,?,?)""",
            (topic, title, description, keywords, content,
             verification_status,
             json.dumps({"biacase_entity": entity,
                         "biacase_id": entity_id})),
        )
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, description, keywords, content, rid, "biacase"),
        )

    n = 0
    for r in conn.execute("SELECT * FROM case_frameworks ORDER BY framework_id"):
        stub(topic="framework",
             title=f"{r['framework_id']}: {r['name']}",
             description=(r["definition"] or "")[:500],
             content=f"{r['name']} {r['definition'] or ''} "
                     f"{r['purpose'] or ''} {r['appropriate_situations'] or ''}",
             entity="framework", entity_id=r["framework_id"],
             verification_status=_hub_status(r["verification_status"]),
             keywords=r["framework_id"])
        n += 1
    for r in conn.execute("SELECT * FROM case_trigger_rules ORDER BY rule_id"):
        import json as _json
        triggers = r["triggers_json"] or ""
        stub(topic="trigger_rule",
             title=f"{r['rule_id']}: {r['title']}",
             description=(r["interpretation"] or "")[:500],
             content=f"{r['title']} {r['interpretation'] or ''} {triggers}",
             entity="rule", entity_id=r["rule_id"],
             verification_status=_hub_status(r["review_status"]),
             keywords=r["rule_id"])
        n += 1
    for r in conn.execute("SELECT * FROM case_practice_questions ORDER BY question_id"):
        stub(topic="practice_question",
             title=f"{r['question_id']}: {(r['question_text'] or '')[:80]}",
             description=(r["question_text"] or "")[:500],
             content=r["question_text"] or "",
             entity="question", entity_id=r["question_id"],
             verification_status=_hub_status(r["verification_status"]),
             keywords=r["question_id"])
        n += 1
    for r in conn.execute("SELECT * FROM case_formulas ORDER BY formula_id"):
        stub(topic="formula",
             title=f"{r['formula_id']}: {r['name']}",
             description=(r["formula_text"] or "")[:500],
             content=f"{r['name']} {r['formula_text'] or ''}",
             entity="formula", entity_id=r["formula_id"],
             verification_status=_hub_status(r["verification_status"]),
             keywords=r["formula_id"])
        n += 1
    return n

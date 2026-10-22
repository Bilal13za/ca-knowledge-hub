"""Phase 4 seeder: financial reporting library.

Loads standards, treatments, examples from data/*.json (idempotent),
links treatments to standards and (defensively) to audit risks, then
registers knowledge_records stubs for global search.

All content is authored study material at CAF level, marked
extracted_unverified throughout — never verified against official
standard text. No paragraph numbers anywhere, by policy.
"""
from __future__ import annotations

import json
from pathlib import Path


def seed_fr(conn, data_dir: str | Path | None = None) -> dict:
    """Seed the FR module. Returns {table: row_count}."""
    data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    conn.executescript(
        (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))

    counts: dict = {}

    standards = json.loads((data_dir / "standards.json").read_text(
        encoding="utf-8"))["standards"]
    for s in standards:
        conn.execute(
            """INSERT OR REPLACE INTO fr_standards
               (id, title, summary, effective_from, jurisdiction,
                verification_status, source_note)
               VALUES (?,?,?,?,?,?,?)""",
            (s["id"], s["title"], s.get("summary"), s.get("effective_from"),
             s.get("jurisdiction", "international"),
             s.get("verification_status", "extracted_unverified"),
             s.get("source_note")))
    counts["fr_standards"] = len(standards)

    treatments = json.loads((data_dir / "treatments.json").read_text(
        encoding="utf-8"))["treatments"]
    audit_risk_ids = {r[0] for r in conn.execute(
        "SELECT id FROM audit_risks")} if _has_table(conn, "audit_risks") else set()
    for t in treatments:
        conn.execute(
            """INSERT OR REPLACE INTO fr_treatments
               (id, title, transaction_analysis, recognition,
                initial_measurement, subsequent_measurement, journals_json,
                presentation, disclosure, statement_impact,
                common_mistakes_json, applicable_period,
                verification_status, source_note)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (t["id"], t["title"], t["transaction_analysis"],
             t.get("recognition"), t.get("initial_measurement"),
             t.get("subsequent_measurement"),
             json.dumps(t.get("journals", []), ensure_ascii=False),
             t.get("presentation"), t.get("disclosure"),
             t.get("statement_impact"),
             json.dumps(t.get("common_mistakes", []), ensure_ascii=False),
             t.get("applicable_period"),
             t.get("verification_status", "extracted_unverified"),
             t.get("source_note")))
        for std_id in t.get("standards", []):
            conn.execute(
                "INSERT OR REPLACE INTO fr_treatment_standard"
                " (treatment_id, standard_id, note) VALUES (?,?,?)",
                (t["id"], std_id, None))
        for link in t.get("audit_risk_links", []):
            # defensive: only link risks that actually exist
            if link["audit_risk_id"] in audit_risk_ids:
                conn.execute(
                    "INSERT OR REPLACE INTO fr_treatment_audit_risk"
                    " (treatment_id, audit_risk_id, note) VALUES (?,?,?)",
                    (t["id"], link["audit_risk_id"], link.get("note")))
    counts["fr_treatments"] = len(treatments)

    examples = json.loads((data_dir / "examples.json").read_text(
        encoding="utf-8"))["examples"]
    for e in examples:
        conn.execute(
            """INSERT OR REPLACE INTO fr_examples
               (id, treatment_id, title, facts, solution, journals_json,
                verification_status)
               VALUES (?,?,?,?,?,?,?)""",
            (e["id"], e["treatment_id"], e["title"], e["facts"],
             e["solution"], json.dumps(e.get("journals", []),
                                       ensure_ascii=False),
             e.get("verification_status", "extracted_unverified")))
    counts["fr_examples"] = len(examples)

    counts["fr_treatment_standard"] = conn.execute(
        "SELECT COUNT(*) FROM fr_treatment_standard").fetchone()[0]
    counts["fr_treatment_audit_risk"] = conn.execute(
        "SELECT COUNT(*) FROM fr_treatment_audit_risk").fetchone()[0]

    counts["knowledge_records(fr)"] = _register_stubs(conn)
    conn.commit()
    return counts


def _has_table(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)).fetchone() is not None


def _register_stubs(conn) -> int:
    """(Re)build knowledge_records stubs for global search. Idempotent."""
    conn.execute("DELETE FROM record_fts WHERE module='fr'")
    conn.execute("DELETE FROM knowledge_records WHERE module='fr'")

    def stub(*, topic, title, description, content, entity, entity_id,
             keywords=""):
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('fr',?,?,?,?,?,?,?)""",
            (topic, title, description, keywords, content,
             "extracted_unverified",
             json.dumps({"fr_entity": entity, "fr_id": entity_id})),
        )
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, description, keywords, content, rid, "fr"),
        )

    n = 0
    for r in conn.execute("SELECT * FROM fr_standards ORDER BY id"):
        stub(topic="standard", title=f"{r['id']}: {r['title']}",
             description=(r["summary"] or "")[:500],
             content=f"{r['id']} {r['title']} {r['summary'] or ''}",
             entity="standard", entity_id=r["id"], keywords=r["id"])
        n += 1
    for r in conn.execute("SELECT * FROM fr_treatments ORDER BY id"):
        stds = ", ".join(x[0] for x in conn.execute(
            "SELECT standard_id FROM fr_treatment_standard"
            " WHERE treatment_id=? ORDER BY standard_id", (r["id"],)))
        stub(topic="treatment", title=f"{r['id']}: {r['title']}",
             description=(r["transaction_analysis"] or "")[:500],
             content=f"{r['title']} [{stds}] {r['transaction_analysis'] or ''} "
                     f"{r['recognition'] or ''}",
             entity="treatment", entity_id=r["id"],
             keywords=f"{r['id']} {stds}")
        n += 1
    for r in conn.execute("SELECT * FROM fr_examples ORDER BY id"):
        stub(topic="worked_example", title=f"{r['id']}: {r['title']}",
             description=(r["facts"] or "")[:500],
             content=f"{r['title']} {r['facts'] or ''} {r['solution'] or ''}",
             entity="example", entity_id=r["id"], keywords=r["id"])
        n += 1
    return n

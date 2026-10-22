"""Phase 3 seeder: tax module.

Applies ``schema.sql``, loads the staged seed JSONs through the ported
engine loader (``engine/loader.py`` — validation enforced, idempotent),
then registers ``knowledge_records`` stubs so tax content is searchable
in global FTS.

Source apps are read-only; seed files were copied (not moved) from
``staging/tax/``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .engine import loader as tax_loader

# source review_status -> hub verification_status
STATUS_MAP = {
    "verified": "verified",
    "draft": "user_note",
    "under_review": "extracted_unverified",
    "superseded": "superseded",
    "retired": "superseded",
}

SEED_FILES = [
    "evidence_library.json",
    "procedures_library.json",
    "income_tax.json",
    "withholding_tax.json",
    "sales_tax_federal.json",
    "sales_tax_provincial.json",
]

# (table, code_sql, title, topic, subtopic, desc_sql, status_col)
_STUB_SPECS = [
    ("tax_rules", "code || ' v' || version",
     "code || ': ' || title", "rules", "tax_rule",
     "triggering_transaction || ' — ' || expected_treatment",
     "verification_status"),
    ("tax_risks", "code", "code || ': ' || title", "risks", "tax_risk",
     "description", "review_status"),
    ("tax_procedures", "code", "code || ': ' || name",
     "procedures", "tax_procedure", "objective", "review_status"),
    ("tax_evidence", "code", "code || ': ' || name",
     "evidence", "tax_evidence", "description", "review_status"),
    ("tax_calc_tables", "code || ' v' || version",
     "code || ' v' || version || ': ' || name",
     "calculations", "tax_calc", "legislation_ref", "verification_status"),
    ("tax_scenarios", "code", "code || ': ' || name",
     "scenarios", "tax_scenario", "description", "review_status"),
    ("tax_legislation", "code", "provision || ': ' || name",
     "legislation", "tax_legislation", "rule_description", "review_status"),
]


def seed_tax(conn, data_dir: str | Path | None = None) -> dict:
    """Seed the tax module. Returns {entity: new_row_count}."""
    data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    schema_sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema_sql)

    for name in SEED_FILES:
        path = data_dir / name
        if not path.is_file():
            continue
        tax_loader.load_seed_file(path, conn=conn)
    conn.commit()

    stub_count = _register_stubs(conn)
    conn.commit()

    # absolute table counts (stable across reseeds — idempotency check)
    total = {}
    for table, key in [
        ("tax_sources", "sources"), ("tax_legislation", "legislation"),
        ("tax_rules", "rules"), ("tax_risks", "risks"),
        ("tax_evidence", "evidence"), ("tax_procedures", "procedures"),
        ("tax_calc_tables", "calc_tables"), ("tax_scenarios", "scenarios"),
    ]:
        total[key] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    total["knowledge_records(tax)"] = stub_count
    return total


def _register_stubs(conn) -> int:
    """(Re)build knowledge_records stubs for global search. Idempotent.

    The tax_* tables are the authority; stubs are searchable pointers
    (never edited by hand — regenerated on every seed).
    """
    conn.execute("DELETE FROM record_fts WHERE module='tax'")
    conn.execute("DELETE FROM knowledge_records WHERE module='tax'")

    def stub(*, topic, title, description, content, verification_status,
             entity, entity_id, keywords=""):
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('tax',?,?,?,?,?,?,?)""",
            (topic, title, description, keywords, content,
             verification_status,
             json.dumps({"tax_entity": entity, "tax_id": entity_id})),
        )
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, description, keywords, content, rid, "tax"),
        )

    n = 0
    for table, code_sql, title_sql, topic, subtopic, desc_sql, status_col in _STUB_SPECS:
        rows = conn.execute(
            f"SELECT ({code_sql}) AS code, ({title_sql}) AS title, "
            f"({desc_sql}) AS description, {status_col} AS st "
            f"FROM {table}"
        ).fetchall()
        for r in rows:
            stub(topic=topic, title=r["title"] or r["code"],
                 description=(r["description"] or "")[:500],
                 content=r["title"] or r["code"],
                 verification_status=STATUS_MAP.get(r["st"], "user_note"),
                 entity=subtopic, entity_id=r["code"], keywords=r["code"])
            n += 1
    return n

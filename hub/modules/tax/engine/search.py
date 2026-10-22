"""Offline search over the tax knowledge base.

The standalone engine used a dedicated FTS5 table (kb_fts). Inside the
Hub, global full-text search runs over ``knowledge_records`` stubs
(``hubcore.search``); this module provides the engine-local equivalent
as a deterministic LIKE search over the tax tables, returning the same
``[{entity_type, entity_code, title, snippet}]`` shape the source API
used.
"""
from __future__ import annotations

# entity_type -> (table, code_col, title_sql, body_sql)
_SEARCHABLE = {
    "rule": ("tax_rules",
             "code",
             "code || ': ' || title",
             "triggering_transaction || ' ' || expected_treatment"),
    "risk": ("tax_risks",
             "code",
             "code || ': ' || title",
             "description"),
    "legislation": ("tax_legislation",
                    "code",
                    "code || ' ' || provision",
                    "rule_description"),
    "evidence": ("tax_evidence",
                 "code",
                 "code || ': ' || name",
                 "description"),
    "procedure": ("tax_procedures",
                  "code",
                  "code || ': ' || name",
                  "objective"),
    "calc": ("tax_calc_tables",
             "code",
             "code || ' v' || version || ': ' || name",
             "legislation_ref"),
    "scenario": ("tax_scenarios",
                 "code",
                 "code || ': ' || name",
                 "description"),
}


def search(conn, query: str, entity_type: str | None = None,
           limit: int = 50) -> list:
    """Search tax knowledge. Returns [{entity_type, entity_code, title,
    snippet}]. Empty query -> []."""
    query = (query or "").strip()
    if not query:
        return []
    like = f"%{query}%"
    out = []
    types = [entity_type] if entity_type else list(_SEARCHABLE)
    for et in types:
        if et not in _SEARCHABLE:
            continue
        table, code_col, title_sql, body_sql = _SEARCHABLE[et]
        sql = (f"SELECT {code_col} AS code, ({title_sql}) AS title, "
               f"substr(({body_sql}), 1, 160) AS snippet "
               f"FROM {table} "
               f"WHERE ({title_sql}) LIKE ? OR ({body_sql}) LIKE ? "
               f"ORDER BY {code_col} LIMIT ?")
        for r in conn.execute(sql, (like, like, limit)):
            out.append({"entity_type": et, "entity_code": r["code"],
                        "title": r["title"], "snippet": r["snippet"] or ""})
            if len(out) >= limit:
                return out
    return out

"""Global search service (Phase 1C).

Searches knowledge records (record_fts) and document chunks (doc_fts),
optionally scoped to a workspace's module list. Never presents an
irrelevant match as a definitive answer: every hit carries its source
module, verification status, and a snippet.
"""
from __future__ import annotations

import re
import sqlite3

from . import documents as docmod

_FTS_UNSAFE = re.compile(r'["*():^~+-]')


def sanitize_fts(query: str) -> str:
    """Make free text safe for FTS5 MATCH (implicit AND of tokens)."""
    tokens = _FTS_UNSAFE.sub(" ", query).split()
    tokens = [t.strip() for t in tokens if t.strip()]
    return " ".join(f'"{t}"' for t in tokens) if tokens else ""


def search_records(conn: sqlite3.Connection, query: str, *,
                   modules: list[str] | None = None,
                   limit: int = 20) -> list[dict]:
    """FTS5 search over knowledge records, optionally module-scoped."""
    match = sanitize_fts(query)
    if not match:
        return []
    sql = """SELECT kr.*, snippet(record_fts, 0, '<b>', '</b>', '…', 12) AS snippet,
                    bm25(record_fts) AS rank
             FROM record_fts
             JOIN knowledge_records kr ON kr.id = record_fts.record_id
             WHERE record_fts MATCH ?"""
    params: list = [match]
    if modules:
        placeholders = ",".join("?" for _ in modules)
        sql += f" AND kr.module IN ({placeholders})"
        params.extend(modules)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]


def global_search(conn: sqlite3.Connection, query: str, *,
                  modules: list[str] | None = None,
                  limit: int = 20) -> dict:
    """Combined search: {'records': [...], 'chunks': [...]}.

    `modules` scopes knowledge-record search (workspace filtering).
    Document-chunk search is not module-scoped (documents are shared).
    """
    return {
        "records": search_records(conn, query, modules=modules, limit=limit),
        "chunks": docmod.search_chunks(conn, query, limit=limit),
    }


def search_categories(conn: sqlite3.Connection) -> list[str]:
    """Distinct modules present in knowledge records (for filter chips)."""
    return [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT module FROM knowledge_records ORDER BY 1"
        )
    ]

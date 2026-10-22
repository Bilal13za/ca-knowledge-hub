"""Document ingestion and the Refresh Library (Phase 1B).

Implements the 13 Refresh Library requirements from spec section 5:

 1. Scan configured folders and permitted subfolders.
 2. Detect new documents.                 3. Detect modified documents.
 4. Identify unchanged documents.         5. Detect missing source files.
 6. Extract supported text and metadata.  7. Update search indexes.
 8. Preserve document identity (stable row id) where possible.
 9. Record processing results.          10. Report failures.
11. Avoid unnecessary duplicate records. 12. Preserve existing valid content
    when an update fails.
13. Record the refresh date and time.

Missing sources mark the document row (status='missing') — knowledge
records are never deleted automatically. Scanned PDFs with no extractable
text are reported as 'ocr_needed', never silently indexed as empty.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import extractors
from .extractors import ExtractionError

SUPPORTED_EXTENSIONS = {"." + ext for ext in extractors.SUPPORTED}

# Document statuses
ST_INDEXED = "indexed"
ST_FAILED = "failed"
ST_UNSUPPORTED = "unsupported"
ST_OCR_NEEDED = "ocr_needed"
ST_MISSING = "missing"


def file_hash(path: Path) -> str:
    """SHA-256 of file content (streamed)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_chunks(conn: sqlite3.Connection, doc_id: int,
                  extraction: extractors.Extraction) -> int:
    """Chunk an extraction and store chunks + FTS rows. Returns chunk count."""
    n = 0
    for page in extraction.pages:
        for page_no, section, text in extractors.chunk_text(
            page.text, page=page.page, section=page.section
        ):
            cur = conn.execute(
                "INSERT INTO doc_chunks (document_id, chunk_index, page_no, sheet_name, text)"
                " VALUES (?,?,?,?,?)",
                (doc_id, n, page_no, section or "", text),
            )
            chunk_id = cur.lastrowid
            conn.execute(
                "INSERT INTO doc_fts (text, document_id, chunk_id) VALUES (?,?,?)",
                (text, doc_id, chunk_id),
            )
            n += 1
    return n


def _clear_chunks(conn: sqlite3.Connection, doc_id: int) -> None:
    conn.execute("DELETE FROM doc_fts WHERE document_id = ?", (doc_id,))
    conn.execute("DELETE FROM doc_chunks WHERE document_id = ?", (doc_id,))


def _index_document(conn: sqlite3.Connection, path: Path, folder: str,
                    *, ocr_enabled: bool = False) -> tuple[str, str]:
    """Extract + store one file. Returns (status, message).

    Raises nothing: all outcomes are returned as (status, message) so a
    single bad file can never abort a refresh.
    """
    try:
        extraction = extractors.extract(path, ocr_enabled=ocr_enabled)
    except ExtractionError as exc:
        # Record the failure as a document row so it is visible and
        # retried on the next refresh — failures are never silent.
        stat = path.stat()
        conn.execute(
            """INSERT INTO documents
               (path, filename, folder, file_hash, file_size, file_type, title,
                modified_at, status, error_text, meta_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(path), path.name, folder, file_hash(path), stat.st_size,
                path.suffix.lower().lstrip("."), path.stem,
                datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                ST_FAILED, str(exc), "{}",
            ),
        )
        return ST_FAILED, str(exc)

    stat = path.stat()
    image_only_pages = sum(1 for p in extraction.pages if p.image_only)
    status = ST_INDEXED
    notes: list[str] = list(extraction.warnings)
    if image_only_pages and not extraction.has_extractable_text:
        status = ST_OCR_NEEDED
        notes.append("No extractable text — scanned document, OCR needed.")
    elif image_only_pages:
        notes.append(f"{image_only_pages} page(s) are scanned images.")

    file_type = extraction.file_type
    cur = conn.execute(
        """INSERT INTO documents
           (path, filename, folder, file_hash, file_size, file_type, title,
            page_count, modified_at, status, error_text,
            meta_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            str(path), path.name, folder, file_hash(path), stat.st_size,
            file_type, path.stem, extraction.page_count,
            datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            status, "; ".join(notes),
            json.dumps({"warnings": extraction.warnings}),
        ),
    )
    doc_id = cur.lastrowid
    _store_chunks(conn, doc_id, extraction)
    return status, "; ".join(notes)


def _reindex_document(conn: sqlite3.Connection, doc_id: int, path: Path,
                      *, ocr_enabled: bool = False) -> tuple[str, str]:
    """Re-extract a changed file, preserving the document row id.

    Existing chunks are replaced only AFTER the new extraction succeeds —
    a failed update preserves the previous valid content (req. 12).
    """
    try:
        extraction = extractors.extract(path, ocr_enabled=ocr_enabled)
    except ExtractionError as exc:
        return ST_FAILED, f"update failed, previous content kept: {exc}"

    stat = path.stat()
    image_only_pages = sum(1 for p in extraction.pages if p.image_only)
    status = ST_INDEXED
    notes: list[str] = list(extraction.warnings)
    if image_only_pages and not extraction.has_extractable_text:
        status = ST_OCR_NEEDED
        notes.append("No extractable text — scanned document, OCR needed.")

    _clear_chunks(conn, doc_id)
    _store_chunks(conn, doc_id, extraction)
    conn.execute(
        """UPDATE documents SET file_hash=?, file_size=?, file_type=?, title=?,
           page_count=?, modified_at=?, ingested_at=?, status=?, error_text=?, meta_json=?
           WHERE id=?""",
        (
            file_hash(path), stat.st_size, extraction.file_type, path.stem,
            extraction.page_count,
            datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            _utcnow(), status, "; ".join(notes),
            json.dumps({"warnings": extraction.warnings}),
            doc_id,
        ),
    )
    return status, "; ".join(notes)


def refresh_library(conn: sqlite3.Connection, inbox_dir: str | Path,
                    *, ocr_enabled: bool = False,
                    recursive: bool = True) -> dict:
    """Run one Refresh Library pass over inbox_dir.

    Returns a processing report dict with keys: new, updated, unchanged,
    missing, indexed, failed, unsupported, ocr_needed, started_at,
    finished_at. Each list holds file paths (strings).
    """
    inbox = Path(inbox_dir).expanduser().resolve()
    report: dict = {
        "new": [], "updated": [], "unchanged": [], "missing": [],
        "indexed": 0, "failed": [], "unsupported": [],
        "ocr_needed": [], "started_at": _utcnow(), "finished_at": "",
    }
    if not inbox.is_dir():
        report["finished_at"] = _utcnow()
        report["error"] = f"inbox directory not found: {inbox}"
        return report

    # known documents: path -> (id, hash, status)
    known = {
        r["path"]: (r["id"], r["file_hash"], r["status"])
        for r in conn.execute("SELECT id, path, file_hash, status FROM documents")
    }
    seen: set[str] = set()

    files = sorted(inbox.rglob("*") if recursive else inbox.glob("*"))
    for path in files:
        if not path.is_file():
            continue
        if path.name.startswith(".") or path.name.startswith("~"):
            continue
        rel = str(path.relative_to(inbox))
        seen.add(str(path))

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            report["unsupported"].append(rel)
            continue

        digest = file_hash(path)
        if str(path) not in known:
            with conn:
                status, _ = _index_document(conn, path, rel, ocr_enabled=ocr_enabled)
            if status == ST_FAILED:
                report["failed"].append(rel)
            else:
                report["new"].append(rel)
                if status == ST_OCR_NEEDED:
                    report["ocr_needed"].append(rel)
        else:
            doc_id, old_hash, _ = known[str(path)]
            if old_hash == digest:
                report["unchanged"].append(rel)
            else:
                with conn:
                    status, _ = _reindex_document(
                        conn, doc_id, path, ocr_enabled=ocr_enabled
                    )
                if status == ST_FAILED:
                    report["failed"].append(rel)
                else:
                    report["updated"].append(rel)
                    if status == ST_OCR_NEEDED:
                        report["ocr_needed"].append(rel)

    # missing sources: in DB but not on disk — mark, never delete (req. 5)
    for path_str, (doc_id, _, _) in known.items():
        if path_str not in seen:
            with conn:
                conn.execute(
                    "UPDATE documents SET status=? WHERE id=?", (ST_MISSING, doc_id)
                )
            report["missing"].append(path_str)

    report["indexed"] = conn.execute(
        "SELECT COUNT(*) FROM documents WHERE status IN ('indexed','ocr_needed')"
    ).fetchone()[0]
    report["finished_at"] = _utcnow()
    with conn:
        conn.execute(
            "INSERT INTO settings (key, value_json) VALUES ('last_refresh', ?)"
            " ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,"
            " updated_at=excluded.updated_at",
            (json.dumps(report),),
        )
    return report


def get_document(conn: sqlite3.Connection, doc_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    return dict(row) if row else None


def list_documents(conn: sqlite3.Connection, *, status: str | None = None,
                   folder: str | None = None) -> list[dict]:
    sql = "SELECT * FROM documents WHERE 1=1"
    params: list = []
    if status:
        sql += " AND status=?"
        params.append(status)
    if folder:
        sql += " AND folder LIKE ?"
        params.append(folder + "%")
    sql += " ORDER BY filename"
    return [dict(r) for r in conn.execute(sql, params)]


def search_chunks(conn: sqlite3.Connection, query: str, *, limit: int = 20) -> list[dict]:
    """FTS5 search over document chunks (used by global search in Phase 1C)."""
    match = _sanitize_fts(query)
    if not match:
        return []
    rows = conn.execute(
        """SELECT d.filename, d.path, c.page_no, c.sheet_name,
                  snippet(doc_fts, 0, '<b>', '</b>', '…', 12) AS snippet,
                  bm25(doc_fts) AS rank
           FROM doc_fts
           JOIN doc_chunks c ON c.id = doc_fts.chunk_id
           JOIN documents d ON d.id = doc_fts.document_id
           WHERE doc_fts MATCH ? AND d.status IN ('indexed','ocr_needed')
           ORDER BY rank LIMIT ?""",
        (match, limit),
    )
    return [dict(r) for r in rows]


def _sanitize_fts(query: str) -> str:
    """Make free text safe for FTS5 MATCH (implicit AND of tokens)."""
    import re

    tokens = re.sub(r'["*():^~+-]', " ", query).split()
    tokens = [t.strip() for t in tokens if t.strip()]
    return " ".join(f'"{t}"' for t in tokens) if tokens else ""

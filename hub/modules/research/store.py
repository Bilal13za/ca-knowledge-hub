"""Research workflow store (Phase 12)."""
from __future__ import annotations

ISSUE_STATUS = ("open", "in_progress", "concluded")
SOURCE_TYPES = ("statute", "circular", "book", "website", "note", "precedent")
AGREEMENT = ("agree", "conflict", "unclear")


def register_issue(conn, *, title: str, question: str,
                   background: str = "") -> int:
    if not title.strip() or not question.strip():
        raise ValueError("Issue title and question are required.")
    cur = conn.execute(
        "INSERT INTO rs_issues (title, question, background)"
        " VALUES (?,?,?)", (title, question, background))
    conn.commit()
    return cur.lastrowid


def set_issue_status(conn, issue_id: int, status: str) -> None:
    if status not in ISSUE_STATUS:
        raise ValueError(f"Bad issue status {status}")
    conn.execute("UPDATE rs_issues SET status = ? WHERE id = ?",
                 (status, issue_id))
    conn.commit()


def get_issue(conn, issue_id: int) -> dict:
    r = conn.execute("SELECT * FROM rs_issues WHERE id = ?",
                     (issue_id,)).fetchone()
    if r is None:
        raise ValueError(f"Unknown issue {issue_id}")
    d = dict(r)
    d["conclusion"] = current_conclusion(conn, issue_id)
    d["versions"] = conn.execute(
        "SELECT COUNT(*) AS n FROM rs_conclusions WHERE issue_id = ?",
        (issue_id,)).fetchone()["n"]
    return d


def list_issues(conn, status: str | None = None) -> list[dict]:
    sql = "SELECT * FROM rs_issues"
    params: list = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY id DESC"
    return [dict(r) for r in conn.execute(sql, params)]


def add_source(conn, *, issue_id: int, citation: str,
               source_type: str = "note", url_or_ref: str = "",
               reliability: str = "", notes: str = "") -> int:
    if not citation.strip():
        raise ValueError("Source citation is required.")
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"Bad source_type {source_type}")
    cur = conn.execute(
        """INSERT INTO rs_sources (issue_id, source_type, citation,
           url_or_ref, reliability, notes)
           VALUES (?,?,?,?,?,?)""",
        (issue_id, source_type, citation, url_or_ref, reliability, notes))
    conn.commit()
    return cur.lastrowid


def list_sources(conn, issue_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM rs_sources WHERE issue_id = ? ORDER BY id",
        (issue_id,))]


def add_finding(conn, *, issue_id: int, point: str,
                source_id: int | None = None, relevance: str = "") -> int:
    if not point.strip():
        raise ValueError("Finding point is required.")
    cur = conn.execute(
        """INSERT INTO rs_findings (issue_id, source_id, point, relevance)
           VALUES (?,?,?,?)""",
        (issue_id, source_id, point, relevance))
    conn.commit()
    return cur.lastrowid


def list_findings(conn, issue_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT f.*, s.citation AS source_citation FROM rs_findings f
           LEFT JOIN rs_sources s ON s.id = f.source_id
           WHERE f.issue_id = ? ORDER BY f.id""", (issue_id,))]


def add_comparison(conn, *, issue_id: int, aspect: str,
                   source_a_id: int | None, source_b_id: int | None,
                   agreement: str, note: str = "") -> int:
    if not aspect.strip():
        raise ValueError("Comparison aspect is required.")
    if agreement not in AGREEMENT:
        raise ValueError(f"Bad agreement value {agreement}")
    cur = conn.execute(
        """INSERT INTO rs_comparisons (issue_id, aspect, source_a_id,
           source_b_id, agreement, note)
           VALUES (?,?,?,?,?,?)""",
        (issue_id, aspect, source_a_id, source_b_id, agreement, note))
    conn.commit()
    return cur.lastrowid


def list_comparisons(conn, issue_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT c.*, a.citation AS a_citation, b.citation AS b_citation
           FROM rs_comparisons c
           LEFT JOIN rs_sources a ON a.id = c.source_a_id
           LEFT JOIN rs_sources b ON b.id = c.source_b_id
           WHERE c.issue_id = ? ORDER BY c.id""", (issue_id,))]


def record_conclusion(conn, *, issue_id: int, conclusion_text: str,
                      basis: str = "") -> int:
    """Append a new conclusion version. History is never overwritten."""
    if not conclusion_text.strip():
        raise ValueError("Conclusion text is required.")
    row = conn.execute(
        "SELECT COALESCE(MAX(version_no), 0) AS m FROM rs_conclusions"
        " WHERE issue_id = ?", (issue_id,)).fetchone()
    v = row["m"] + 1
    cur = conn.execute(
        """INSERT INTO rs_conclusions (issue_id, version_no,
           conclusion_text, basis) VALUES (?,?,?,?)""",
        (issue_id, v, conclusion_text, basis))
    conn.commit()
    return cur.lastrowid


def current_conclusion(conn, issue_id: int) -> dict | None:
    r = conn.execute(
        "SELECT * FROM rs_conclusions WHERE issue_id = ?"
        " ORDER BY version_no DESC LIMIT 1", (issue_id,)).fetchone()
    return dict(r) if r else None


def conclusion_history(conn, issue_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM rs_conclusions WHERE issue_id = ?"
        " ORDER BY version_no", (issue_id,))]

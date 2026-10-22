"""Working-paper store (Phase 9)."""
from __future__ import annotations

import json
from pathlib import Path


def list_templates(conn, category: str | None = None) -> list[dict]:
    sql = "SELECT * FROM wp_templates"
    params: list = []
    if category:
        sql += " WHERE category = ?"
        params.append(category)
    sql += " ORDER BY category, id"
    return [dict(r) for r in conn.execute(sql, params)]


def get_template(conn, template_id: str) -> dict:
    r = conn.execute("SELECT * FROM wp_templates WHERE id = ?",
                     (template_id,)).fetchone()
    if r is None:
        raise ValueError(f"Unknown template {template_id}")
    d = dict(r)
    d["structure"] = json.loads(d["structure_json"] or "[]")
    return d


def create_paper(conn, *, engagement: str, template_id: str, title: str,
                 prepared_by: str = "") -> int:
    get_template(conn, template_id)  # validates
    cur = conn.execute(
        """INSERT INTO wp_papers (engagement, template_id, title, prepared_by,
           prepared_at) VALUES (?,?,?, ?, datetime('now'))""",
        (engagement, template_id, title, prepared_by))
    conn.commit()
    return cur.lastrowid


def save_paper_data(conn, paper_id: int, data: dict,
                    status: str | None = None) -> None:
    if status and status not in ("draft", "in_progress", "in_review",
                                 "completed"):
        raise ValueError(f"Bad status {status}")
    if status:
        conn.execute("UPDATE wp_papers SET data_json = ?, status = ?"
                     " WHERE id = ?",
                     (json.dumps(data, ensure_ascii=False), status, paper_id))
    else:
        conn.execute("UPDATE wp_papers SET data_json = ? WHERE id = ?",
                     (json.dumps(data, ensure_ascii=False), paper_id))
    conn.commit()


def get_paper(conn, paper_id: int) -> dict:
    r = conn.execute("SELECT * FROM wp_papers WHERE id = ?",
                     (paper_id,)).fetchone()
    if r is None:
        raise ValueError(f"Unknown paper {paper_id}")
    d = dict(r)
    d["data"] = json.loads(d["data_json"] or "{}")
    d["template"] = get_template(conn, d["template_id"])
    return d


def list_papers(conn, engagement: str | None = None) -> list[dict]:
    sql = "SELECT * FROM wp_papers"
    params: list = []
    if engagement:
        sql += " WHERE engagement = ?"
        params.append(engagement)
    sql += " ORDER BY id DESC"
    return [dict(r) for r in conn.execute(sql, params)]


def log_exception(conn, *, paper_id: int | None = None, engagement: str = "",
                  description: str, assertion: str = "",
                  potential_impact: str = "", follow_up: str = "") -> int:
    if not description.strip():
        raise ValueError("Exception description is required.")
    cur = conn.execute(
        """INSERT INTO wp_exceptions (paper_id, engagement, description,
           assertion, potential_impact, follow_up)
           VALUES (?,?,?,?,?,?)""",
        (paper_id, engagement, description, assertion,
         potential_impact, follow_up))
    conn.commit()
    return cur.lastrowid


def resolve_exception(conn, exception_id: int, resolution: str,
                      status: str = "cleared") -> None:
    if status not in ("cleared", "in_follow_up"):
        raise ValueError("status must be 'cleared' or 'in_follow_up'")
    if not resolution.strip():
        raise ValueError("A resolution note is required to clear.")
    conn.execute("UPDATE wp_exceptions SET status = ?, resolution = ?"
                 " WHERE id = ?", (status, resolution, exception_id))
    conn.commit()


def list_exceptions(conn, status: str | None = None) -> list[dict]:
    sql = "SELECT * FROM wp_exceptions"
    params: list = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY id DESC"
    return [dict(r) for r in conn.execute(sql, params)]


def add_evidence(conn, *, paper_id: int, ref: str, description: str,
                 source: str = "", date_obtained: str = "",
                 reliability: str = "") -> int:
    if not ref.strip() or not description.strip():
        raise ValueError("Evidence ref and description are required.")
    cur = conn.execute(
        """INSERT INTO wp_evidence (paper_id, ref, description, source,
           date_obtained, reliability) VALUES (?,?,?,?,?,?)""",
        (paper_id, ref, description, source, date_obtained, reliability))
    conn.commit()
    return cur.lastrowid


def list_evidence(conn, paper_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM wp_evidence WHERE paper_id = ? ORDER BY id",
        (paper_id,))]

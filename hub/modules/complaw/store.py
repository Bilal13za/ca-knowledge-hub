"""Company-law store (Phase 11)."""
from __future__ import annotations

from datetime import date

ALLOWED_STATUS = ("verified", "extracted_unverified", "user_note",
                  "interpretation", "superseded")


def add_provision(conn, *, title: str, act: str = "Companies Act, 2017",
                  section_no: str | None = None, summary: str = "",
                  source_ref: str = "",
                  verification_status: str = "user_note",
                  effective_date: str = "", notes: str = "") -> int:
    if not title.strip():
        raise ValueError("Provision title is required.")
    if verification_status not in ALLOWED_STATUS:
        raise ValueError(f"Bad verification_status {verification_status}")
    cur = conn.execute(
        """INSERT INTO law_provisions (act, section_no, title, summary,
           source_ref, verification_status, effective_date, notes)
           VALUES (?,?,?,?,?,?,?,?)""",
        (act, section_no, title, summary, source_ref, verification_status,
         effective_date, notes))
    conn.commit()
    return cur.lastrowid


def list_provisions(conn, status: str | None = None) -> list[dict]:
    sql = "SELECT * FROM law_provisions"
    params: list = []
    if status:
        sql += " WHERE verification_status = ?"
        params.append(status)
    sql += " ORDER BY act, title"
    return [dict(r) for r in conn.execute(sql, params)]


def add_company(conn, *, name: str, cuin: str = "", company_type: str = "",
                incorporation_date: str = "", registered_office: str = "",
                notes: str = "") -> int:
    if not name.strip():
        raise ValueError("Company name is required.")
    cur = conn.execute(
        """INSERT INTO law_companies (name, cuin, company_type,
           incorporation_date, registered_office, notes)
           VALUES (?,?,?,?,?,?)""",
        (name, cuin, company_type, incorporation_date, registered_office,
         notes))
    conn.commit()
    return cur.lastrowid


def list_companies(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM law_companies ORDER BY name")]


def add_deadline(conn, *, company_id: int, obligation: str, due_date: str,
                 provision_ref: str = "", frequency: str = "",
                 notes: str = "") -> int:
    if not obligation.strip():
        raise ValueError("Obligation is required.")
    _check_iso(due_date, "due_date")
    cur = conn.execute(
        """INSERT INTO law_deadlines (company_id, obligation, provision_ref,
           due_date, frequency, notes) VALUES (?,?,?,?,?,?)""",
        (company_id, obligation, provision_ref, due_date, frequency, notes))
    conn.commit()
    return cur.lastrowid


def mark_deadline_done(conn, deadline_id: int,
                       done_date: str | None = None) -> None:
    _check_iso(done_date, "done_date") if done_date else None
    conn.execute("UPDATE law_deadlines SET done = 1, done_date = ?"
                 " WHERE id = ?",
                 (done_date or date.today().isoformat(), deadline_id))
    conn.commit()


def deadline_status(due_date: str, done: bool,
                    today: str | None = None) -> str:
    """Computed status: done | overdue | upcoming. Never stored."""
    if done:
        return "done"
    today = today or date.today().isoformat()
    return "overdue" if due_date < today else "upcoming"


def list_deadlines(conn, company_id: int | None = None,
                   today: str | None = None) -> list[dict]:
    sql = ("SELECT d.*, c.name AS company_name FROM law_deadlines d"
           " LEFT JOIN law_companies c ON c.id = d.company_id")
    params: list = []
    if company_id:
        sql += " WHERE d.company_id = ?"
        params.append(company_id)
    sql += " ORDER BY d.due_date"
    rows = []
    for r in conn.execute(sql, params):
        d = dict(r)
        d["computed_status"] = deadline_status(d["due_date"], bool(d["done"]),
                                               today)
        rows.append(d)
    return rows


def add_filing(conn, *, company_id: int, form_name: str,
               period_ended: str = "", filed_on: str = "",
               status: str = "pending", reference_no: str = "",
               notes: str = "") -> int:
    if not form_name.strip():
        raise ValueError("Form name is required.")
    if status not in ("pending", "filed", "acknowledged"):
        raise ValueError(f"Bad filing status {status}")
    cur = conn.execute(
        """INSERT INTO law_filings (company_id, form_name, period_ended,
           filed_on, status, reference_no, notes)
           VALUES (?,?,?,?,?,?,?)""",
        (company_id, form_name, period_ended, filed_on, status,
         reference_no, notes))
    conn.commit()
    return cur.lastrowid


def list_filings(conn, company_id: int | None = None) -> list[dict]:
    sql = ("SELECT f.*, c.name AS company_name FROM law_filings f"
           " LEFT JOIN law_companies c ON c.id = f.company_id")
    params: list = []
    if company_id:
        sql += " WHERE f.company_id = ?"
        params.append(company_id)
    sql += " ORDER BY f.id DESC"
    return [dict(r) for r in conn.execute(sql, params)]


def _check_iso(value: str, field: str) -> None:
    parts = value.split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"{field} must be an ISO date (YYYY-MM-DD).")

"""Persistence for reconciliation runs (Phase 5).

The workbench itself is pure (DataFrame in, findings out). This module
stores runs, the original imported datasets (preserved verbatim), and
findings with manual resolutions.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import workbench as wb


def create_run(conn, *, name: str, kind: str = "other",
               label_a: str = "A", label_b: str = "B",
               mapping: dict | None = None) -> int:
    cur = conn.execute(
        """INSERT INTO recon_runs (name, kind, label_a, label_b, mapping_json)
           VALUES (?,?,?,?,?)""",
        (name, kind, label_a, label_b, json.dumps(mapping or {})),
    )
    conn.commit()
    return cur.lastrowid


def save_dataset(conn, run_id: int, side: str, df, filename: str | None = None) -> int:
    """Preserve the original imported data verbatim (minus _src_row)."""
    cols = [c for c in df.columns if c != "_src_row"]
    rows = df[cols].astype(str).to_dict("records")
    # keep the source row refs alongside
    src_rows = list(df["_src_row"]) if "_src_row" in df.columns else [None] * len(df)
    for rec, sr in zip(rows, src_rows):
        rec["_src_row"] = int(sr) if sr is not None else None
    cur = conn.execute(
        """INSERT INTO recon_datasets
           (run_id, side, filename, columns_json, rows_json, row_count)
           VALUES (?,?,?,?,?,?)""",
        (run_id, side, filename, json.dumps(cols),
         json.dumps(rows, ensure_ascii=False), len(rows)),
    )
    conn.commit()
    return cur.lastrowid


def save_reconcile_result(conn, run_id: int, result: dict) -> int:
    """Flatten a reconcile() result into recon_findings. Returns count."""
    n = 0
    n += _add(conn, run_id, "amount_difference", "error",
              result.get("amount_differences", []),
              lambda d: (f"Amount difference on '{d['id']}': "
                         f"{d.get('difference', d.get('note', ''))}",
                         None, None, d))
    n += _add(conn, run_id, "unmatched", "warning",
              result.get("unmatched_a", []),
              lambda r: (f"Unmatched in {r['label']}: '{r['id']}'", r["row_ref"], None, r))
    n += _add(conn, run_id, "unmatched", "warning",
              result.get("unmatched_b", []),
              lambda r: (f"Unmatched in {r['label']}: '{r['id']}'", r["row_ref"], None, r))
    n += _add(conn, run_id, "ambiguous", "warning",
              result.get("ambiguous", []),
              lambda a: (f"Ambiguous ID '{a['id']}' — manual review required; "
                         "not auto-matched.", None, None, a))
    for side, key in (("a", "duplicates_within_a"), ("b", "duplicates_within_b")):
        n += _add(conn, run_id, "duplicate", "error", result.get(key, []),
                  lambda d, s=side: (
                      f"Duplicate ID '{d['id']}' within side {s.upper()} "
                      f"(rows {d['rows']}).", None, None, d))
    for side, key in (("a", "blank_ids_a"), ("b", "blank_ids_b")):
        n += _add(conn, run_id, "blank_id", "error", result.get(key, []),
                  lambda r, s=side: (
                      f"Blank ID in side {s.upper()} (source row {r['row_ref']}).",
                      r["row_ref"], None, r))
    n += _add(conn, run_id, "suggestion", "info",
              result.get("suggestions", []),
              lambda s: (f"Possible match for '{s['a_id']}' (row {s['a_row']}): "
                         + ", ".join(c["b_id"] for c in s["candidates"])
                         + " — human review required.",
                         s["a_row"], None, s))
    conn.execute("UPDATE recon_runs SET summary_json = ? WHERE id = ?",
                 (json.dumps(result.get("summary", {})), run_id))
    conn.commit()
    return n


def save_findings(conn, run_id: int, findings: list) -> int:
    """Persist workbench Finding objects (validation / duplicates)."""
    n = 0
    for f in findings:
        d = f.as_dict() if hasattr(f, "as_dict") else f
        conn.execute(
            """INSERT INTO recon_findings
               (run_id, kind, severity, message, row_ref, column_name, details_json)
               VALUES (?,?,?,?,?,?,?)""",
            (run_id, d["kind"], d["severity"], d["message"], d.get("row_ref"),
             d.get("column"), json.dumps(d.get("details", {}),
                                        ensure_ascii=False, default=str)),
        )
        n += 1
    conn.commit()
    return n


def _add(conn, run_id, kind, severity, items, fmt) -> int:
    n = 0
    for item in items:
        message, row_ref, column, details = fmt(item)
        conn.execute(
            """INSERT INTO recon_findings
               (run_id, kind, severity, message, row_ref, column_name, details_json)
               VALUES (?,?,?,?,?,?,?)""",
            (run_id, kind, severity, message, row_ref, column,
             json.dumps(details, ensure_ascii=False, default=str)),
        )
        n += 1
    return n


def resolve_finding(conn, finding_id: int, note: str,
                    status: str = "resolved") -> None:
    """Manual resolution with an explanatory note (never automatic)."""
    if status not in ("resolved", "ignored"):
        raise ValueError("status must be 'resolved' or 'ignored'")
    conn.execute(
        """UPDATE recon_findings SET status = ?, resolution_note = ?,
           resolved_at = datetime('now') WHERE id = ?""",
        (status, note, finding_id),
    )
    conn.commit()


def list_runs(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT r.*, COUNT(f.id) AS finding_count,
                  SUM(CASE WHEN f.status='open' THEN 1 ELSE 0 END) AS open_count
           FROM recon_runs r LEFT JOIN recon_findings f ON f.run_id = r.id
           GROUP BY r.id ORDER BY r.id DESC""")]


def get_run(conn, run_id: int) -> dict:
    run = conn.execute(
        "SELECT * FROM recon_runs WHERE id = ?", (run_id,)).fetchone()
    if run is None:
        raise ValueError(f"Unknown run {run_id}")
    out = dict(run)
    out["mapping"] = json.loads(out["mapping_json"] or "{}")
    out["summary"] = json.loads(out["summary_json"] or "{}")
    out["datasets"] = [dict(r) for r in conn.execute(
        "SELECT id, side, filename, columns_json, row_count FROM recon_datasets"
        " WHERE run_id = ? ORDER BY side", (run_id,))]
    out["findings"] = [dict(r) for r in conn.execute(
        "SELECT * FROM recon_findings WHERE run_id = ? ORDER BY id", (run_id,))]
    return out


def export_findings(conn, run_id: int, path: str | Path, fmt: str = "xlsx") -> Path:
    """Export a run's findings via the workbench report writer."""
    findings = [dict(r) for r in conn.execute(
        "SELECT kind, severity, message, row_ref, column_name AS column,"
        " details_json AS details FROM recon_findings WHERE run_id = ?"
        " ORDER BY id", (run_id,))]
    for f in findings:
        raw = f.pop("details")
        try:
            f["details"] = json.loads(raw) if raw else {}
        except (ValueError, TypeError):
            f["details"] = {"note": raw}
    run = conn.execute(
        "SELECT name, kind, summary_json FROM recon_runs WHERE id = ?",
        (run_id,)).fetchone()
    import pandas as pd

    df = pd.DataFrame(findings)
    summary = {"run": run["name"], "kind": run["kind"],
               **json.loads(run["summary_json"] or "{}")}
    return wb.export_report(df, path, fmt=fmt, summary=summary)

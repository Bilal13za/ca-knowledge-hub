"""Workspace management (spec section 4B).

A workspace is a named set of active modules for the task at hand, e.g.
"Audit" or "Audit + Tax". Search and browsing scope to the active
workspace's modules. Workspaces never auto-generate conclusions.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_workspace(conn: sqlite3.Connection, name: str,
                     modules: list[str]) -> int:
    """Create a workspace. Returns its id. Module names are stored as-is;
    unknown names are kept (so workspaces survive uninstalled modules) but
    flagged by validate_workspace()."""
    cur = conn.execute(
        "INSERT INTO workspaces (name, module_list_json) VALUES (?,?)",
        (name.strip(), json.dumps(sorted(set(modules)))),
    )
    return cur.lastrowid


def list_workspaces(conn: sqlite3.Connection) -> list[dict]:
    return [
        dict(r) for r in conn.execute(
            "SELECT * FROM workspaces ORDER BY last_used DESC, name"
        )
    ]


def get_workspace(conn: sqlite3.Connection, workspace_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM workspaces WHERE id = ?", (workspace_id,)
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["modules"] = json.loads(d["module_list_json"])
    return d


def get_workspace_by_name(conn: sqlite3.Connection, name: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM workspaces WHERE name = ?", (name,)
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["modules"] = json.loads(d["module_list_json"])
    return d


def update_workspace(conn: sqlite3.Connection, workspace_id: int, *,
                     name: str | None = None,
                     modules: list[str] | None = None) -> None:
    sets, params = [], []
    if name is not None:
        sets.append("name = ?"); params.append(name.strip())
    if modules is not None:
        sets.append("module_list_json = ?"); params.append(json.dumps(sorted(set(modules))))
    if not sets:
        return
    sets.append("updated_at = ?"); params.append(_utcnow())
    params.append(workspace_id)
    conn.execute(f"UPDATE workspaces SET {', '.join(sets)} WHERE id = ?", params)


def delete_workspace(conn: sqlite3.Connection, workspace_id: int) -> None:
    conn.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))


def touch_workspace(conn: sqlite3.Connection, workspace_id: int) -> None:
    conn.execute(
        "UPDATE workspaces SET last_used = ? WHERE id = ?", (_utcnow(), workspace_id)
    )


def workspace_modules(conn: sqlite3.Connection, workspace_id: int) -> list[str]:
    ws = get_workspace(conn, workspace_id)
    return ws["modules"] if ws else []


def validate_workspace(conn: sqlite3.Connection, workspace_id: int,
                       installed_modules: list[str]) -> dict:
    """Report modules in the workspace that are not installed/enabled."""
    mods = workspace_modules(conn, workspace_id)
    missing = [m for m in mods if m not in installed_modules]
    return {"modules": mods, "missing": missing, "ok": not missing}

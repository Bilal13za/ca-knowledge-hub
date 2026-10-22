"""First-run bootstrap: register discovered modules in the database.

sync_modules() is idempotent: it inserts new manifests, updates changed
ones, and marks modules whose directories vanished as disabled (never
deletes — a missing folder must not silently drop a module's data).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import registry


def sync_modules(conn: sqlite3.Connection, modules_dir: str | Path) -> dict:
    """Sync the modules table with discovered manifests."""
    found, warnings = registry.discover_with_warnings(modules_dir)
    installed: list[str] = []
    with conn:
        for name, mod in found.items():
            conn.execute(
                """INSERT INTO modules (name, title, version, description, enabled, manifest_json)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(name) DO UPDATE SET
                     title=excluded.title, version=excluded.version,
                     description=excluded.description, enabled=excluded.enabled,
                     manifest_json=excluded.manifest_json""",
                (
                    name, mod.title, mod.version, mod.description,
                    int(mod.enabled), json.dumps(mod.manifest),
                ),
            )
            installed.append(name)
        # disable (never delete) modules that are no longer discovered
        if installed:
            placeholders = ",".join("?" for _ in installed)
            conn.execute(
                f"UPDATE modules SET enabled=0 WHERE name NOT IN ({placeholders})",
                installed,
            )
        else:
            conn.execute("UPDATE modules SET enabled=0")
    dep_warnings = registry.check_dependencies(found)
    return {
        "installed": sorted(installed),
        "warnings": warnings + dep_warnings,
    }


def enabled_modules(conn: sqlite3.Connection) -> list[dict]:
    """Modules table rows with enabled=1, ordered by name."""
    return [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM modules WHERE enabled=1 ORDER BY name"
        )
    ]

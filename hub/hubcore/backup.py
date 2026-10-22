"""Backup and restore with verification (Phase 1C, policy in BACKUP_AND_RESTORE.md).

- backup_database(): timestamped copy of the live DB + export package, rotation.
- verify_backup(): restore into a temp dir, PRAGMA integrity_check, table-count
  comparison against the manifest written at backup time. An unverified backup
  is reported as failed — never silently trusted.
- restore_database(): pre-restore backup of the live DB first, then replace.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import db as dbmod
from . import export as exportmod

KEEP_DEFAULT = 10


def _stamp() -> str:
    # microseconds: two backups in the same second must not collide
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def backup_database(db_path: str | Path, backup_dir: str | Path,
                    *, keep: int = KEEP_DEFAULT) -> Path:
    """Create a timestamped backup. Returns the backup directory path."""
    src = Path(db_path)
    if not src.is_file():
        raise ValueError(f"Database not found: {src}")
    dest = Path(backup_dir) / f"hub-backup-{_stamp()}"
    dest.mkdir(parents=True, exist_ok=False)

    # Checkpoint first: the app normally holds the DB open in WAL mode,
    # and a raw file copy would otherwise miss uncheckpointed frames.
    _ckpt = dbmod.get_connection(src)
    try:
        _ckpt.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        _ckpt.commit()
    finally:
        _ckpt.close()

    shutil.copy2(src, dest / "hub.db")
    conn = dbmod.get_connection(src)
    try:
        counts = dbmod.table_counts(conn)
        version = dbmod.migrations.current_version(conn)
        manifest = {
            "backup_of": str(src),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": version,
            "table_counts": counts,
            "integrity": dbmod.integrity_check(conn),
        }
        (dest / "backup-manifest.json").write_text(json.dumps(manifest, indent=2))
        exportmod.export_all(conn, dest / "export")
    finally:
        conn.close()

    # rotation: keep newest `keep`
    siblings = sorted(
        (p for p in Path(backup_dir).glob("hub-backup-*") if p.is_dir()),
        key=lambda p: p.name,
    )
    for old in siblings[:-keep] if len(siblings) > keep else []:
        shutil.rmtree(old, ignore_errors=True)
    return dest


def verify_backup(backup_path: str | Path) -> dict:
    """Verify a backup without touching the live DB.

    Returns {'ok': bool, 'checks': {...}, 'errors': [...]}.
    """
    backup_path = Path(backup_path)
    errors: list[str] = []
    checks: dict = {}
    manifest_path = backup_path / "backup-manifest.json"
    db_file = backup_path / "hub.db"
    if not manifest_path.is_file():
        errors.append("backup-manifest.json missing")
    if not db_file.is_file():
        errors.append("hub.db missing")
    if errors:
        return {"ok": False, "checks": checks, "errors": errors}

    manifest = json.loads(manifest_path.read_text())
    with tempfile.TemporaryDirectory(prefix="hub-verify-") as tmp:
        restored = Path(tmp) / "hub.db"
        shutil.copy2(db_file, restored)
        try:
            conn = dbmod.get_connection(restored)
        except sqlite3.Error as exc:
            errors.append(f"backup database cannot be opened: {exc}")
            return {"ok": False, "checks": checks, "errors": errors}
        try:
            integrity = dbmod.integrity_check(conn)
            checks["integrity"] = integrity
            if integrity != "ok":
                errors.append(f"integrity_check failed: {integrity}")
            counts = dbmod.table_counts(conn)
            checks["table_counts_match"] = counts == manifest["table_counts"]
            if not checks["table_counts_match"]:
                errors.append("table counts differ from backup manifest")
            checks["schema_version"] = dbmod.migrations.current_version(conn)
            if checks["schema_version"] != manifest["schema_version"]:
                errors.append("schema version differs from backup manifest")
        except sqlite3.Error as exc:
            errors.append(f"backup database unreadable: {exc}")
        finally:
            conn.close()
    return {"ok": not errors, "checks": checks, "errors": errors}


def restore_database(backup_path: str | Path, db_path: str | Path,
                     *, backup_dir: str | Path | None = None) -> Path:
    """Restore hub.db from a backup. Takes a pre-restore backup of the live
    DB first (into backup_dir, or alongside). Returns the pre-restore backup
    path. The backup being restored from is verified first."""
    verification = verify_backup(backup_path)
    if not verification["ok"]:
        raise ValueError(
            f"Refusing to restore from unverified backup: {verification['errors']}"
        )
    live = Path(db_path)
    pre_dir = Path(backup_dir) if backup_dir else live.parent / "backups"
    pre_restore = None
    if live.is_file():
        pre_restore = backup_database(live, pre_dir)
    # checkpoint WAL before replacing the file
    src_conn = sqlite3.connect(str(live)) if live.is_file() else None
    try:
        if src_conn:
            src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        if src_conn:
            src_conn.close()
    shutil.copy2(Path(backup_path) / "hub.db", live)
    # remove stale WAL/SHM siblings so the restored DB opens cleanly
    for suffix in ("-wal", "-shm"):
        stale = live.parent / (live.name + suffix)
        if stale.exists():
            stale.unlink()
    return pre_restore

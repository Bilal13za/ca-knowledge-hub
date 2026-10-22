"""Phase 1C acceptance: backup, verified restore, rotation."""
import json
import sqlite3

import pytest

from hubcore import backup as backupmod
from hubcore import db as dbmod
from hubcore import knowledge


def _live_db(tmp_path):
    p = tmp_path / "hub.db"
    conn = dbmod.get_connection(p)
    dbmod.initialise(conn)
    knowledge.create_record(conn, {"module": "audit", "title": "R", "content": "c"})
    conn.commit()
    conn.close()
    return p


def test_backup_and_verify_ok(tmp_path):
    live = _live_db(tmp_path)
    dest = backupmod.backup_database(live, tmp_path / "backups")
    assert (dest / "hub.db").exists()
    assert (dest / "backup-manifest.json").exists()
    assert (dest / "export" / "manifest.json").exists()
    result = backupmod.verify_backup(dest)
    assert result["ok"], result["errors"]
    assert result["checks"]["integrity"] == "ok"
    assert result["checks"]["table_counts_match"]


def test_verify_detects_corruption(tmp_path):
    live = _live_db(tmp_path)
    dest = backupmod.backup_database(live, tmp_path / "backups")
    # corrupt the backup copy
    with open(dest / "hub.db", "r+b") as fh:
        fh.seek(100)
        fh.write(b"\x00" * 200)
    result = backupmod.verify_backup(dest)
    assert not result["ok"]


def test_restore_roundtrip_with_pre_restore_safety(tmp_path):
    live = _live_db(tmp_path)
    dest = backupmod.backup_database(live, tmp_path / "backups")
    # add a record after the backup, then restore
    conn = dbmod.get_connection(live)
    knowledge.create_record(conn, {"module": "tax", "title": "NEWR", "content": "n"})
    conn.commit()
    conn.close()
    pre = backupmod.restore_database(dest, live, backup_dir=tmp_path / "backups")
    assert pre is not None and pre.exists()  # safety copy taken
    conn = dbmod.get_connection(live)
    titles = {r["title"] for r in knowledge.list_records(conn)}
    assert titles == {"R"}  # post-backup record gone; backup state restored
    conn.close()


def test_restore_refuses_unverified(tmp_path):
    live = _live_db(tmp_path)
    dest = backupmod.backup_database(live, tmp_path / "backups")
    with open(dest / "hub.db", "r+b") as fh:
        fh.seek(100)
        fh.write(b"\x00" * 200)
    with pytest.raises(ValueError):
        backupmod.restore_database(dest, live, backup_dir=tmp_path / "backups")


def test_rotation_keeps_n(tmp_path):
    live = _live_db(tmp_path)
    bdir = tmp_path / "backups"
    for _ in range(4):
        backupmod.backup_database(live, bdir, keep=2)
    remaining = sorted(p.name for p in bdir.glob("hub-backup-*"))
    assert len(remaining) == 2


def test_backup_missing_db_raises(tmp_path):
    with pytest.raises(ValueError):
        backupmod.backup_database(tmp_path / "nope.db", tmp_path / "b")

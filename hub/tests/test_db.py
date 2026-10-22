"""Phase 1A acceptance: versioned schema, migrations, rollback, FTS5."""
import sqlite3

import pytest

from hubcore import db as dbmod
from hubcore import migrations


def test_fresh_migrate_reaches_v1(conn):
    assert dbmod.migrations.current_version(conn) == 1
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    }
    for expected in (
        "schema_migrations", "modules", "documents", "doc_chunks", "sources",
        "knowledge_records", "record_relations", "tags", "record_tags",
        "rules", "procedures", "calculations", "calculation_runs",
        "verification_records", "revision_history", "bookmarks",
        "study_progress", "workspaces", "settings",
    ):
        assert expected in tables, f"missing table {expected}"
    # FTS virtual tables exist
    assert "doc_fts" in tables and "record_fts" in tables


def test_migrate_is_idempotent(conn, tmp_path):
    assert dbmod.initialise(conn) == []  # nothing new on second run
    assert dbmod.migrations.current_version(conn) == 1


def test_rollback_and_remigrate(tmp_path):
    c = dbmod.get_connection(tmp_path / "hub2.db")
    dbmod.initialise(c)
    rolled = dbmod.migrations.rollback(c, target_version=0)
    assert rolled == [1]
    assert dbmod.migrations.current_version(c) == 0
    tables = {
        r[0]
        for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
        )
    }
    assert "knowledge_records" not in tables
    # re-migrate works after rollback
    assert dbmod.initialise(c) == [1]
    assert dbmod.migrations.current_version(c) == 1
    c.close()


def test_verification_status_enum_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO knowledge_records (module, title, verification_status) "
            "VALUES ('core','t','bogus')"
        )


def test_fts_search_finds_record(conn):
    conn.execute(
        "INSERT INTO knowledge_records (module, topic, title, content, verification_status) "
        "VALUES ('core','t','Deferred tax','Temporary differences create deferred tax','verified')"
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO record_fts (title, description, keywords, content, record_id, module) "
        "VALUES (?,?,?,?,?,?)",
        ("Deferred tax", "", "", "Temporary differences create deferred tax", rid, "core"),
    )
    conn.commit()
    hits = conn.execute(
        "SELECT record_id FROM record_fts WHERE record_fts MATCH 'deferred'"
    ).fetchall()
    assert [h[0] for h in hits] == [rid]
    # porter stemming: 'differences' matches 'difference'
    hits2 = conn.execute(
        "SELECT record_id FROM record_fts WHERE record_fts MATCH 'difference'"
    ).fetchall()
    assert [h[0] for h in hits2] == [rid]


def test_integrity_check_ok(conn):
    assert dbmod.integrity_check(conn) == "ok"


def test_workspace_crud(conn):
    conn.execute(
        "INSERT INTO workspaces (name, module_list_json) VALUES (?,?)",
        ("Audit + Tax", '["audit","tax"]'),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM workspaces WHERE name='Audit + Tax'").fetchone()
    assert row is not None
    assert '"tax"' in row["module_list_json"]

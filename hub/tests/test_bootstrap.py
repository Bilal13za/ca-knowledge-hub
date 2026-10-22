"""Phase 1C acceptance: module DB registration sync."""
import json

from hubcore import bootstrap


def test_sync_installs_and_updates(conn, modules_dir, tmp_path):
    summary = bootstrap.sync_modules(conn, modules_dir)
    assert summary["installed"] == ["demo"]
    assert any("broken" in w for w in summary["warnings"])
    rows = bootstrap.enabled_modules(conn)
    assert [r["name"] for r in rows] == ["demo"]
    assert json.loads(rows[0]["manifest_json"])["version"] == "1.2.0"
    # idempotent
    summary2 = bootstrap.sync_modules(conn, modules_dir)
    assert summary2["installed"] == ["demo"]
    assert len(bootstrap.enabled_modules(conn)) == 1


def test_vanished_module_disabled_not_deleted(conn, modules_dir):
    bootstrap.sync_modules(conn, modules_dir)
    # remove the module directory -> next sync disables it, keeps the row
    import shutil

    shutil.rmtree(modules_dir / "demo")
    summary = bootstrap.sync_modules(conn, modules_dir)
    assert summary["installed"] == []
    assert bootstrap.enabled_modules(conn) == []
    row = conn.execute("SELECT * FROM modules WHERE name='demo'").fetchone()
    assert row is not None and row["enabled"] == 0

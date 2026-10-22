"""Phase 1A acceptance: export format (JSON+CSV+dump+manifest)."""
import json
import sqlite3

from hubcore import export as exportmod


def _seed(conn):
    conn.execute("INSERT INTO sources (code, title, kind) VALUES ('s1','Src','other')")
    conn.execute(
        "INSERT INTO knowledge_records (module, topic, title, content, verification_status) "
        "VALUES ('audit','risk','Revenue risk','Details here','verified')"
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO knowledge_records (module, topic, title, content, verification_status) "
        "VALUES ('tax','wht','WHT rate','Rate details','extracted_unverified')"
    )
    rid2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO record_relations (source_record_id, target_record_id, rel_type, note) "
        "VALUES (?,?,?,?)",
        (rid, rid2, "has-tax-implication", "revenue tested for WHT"),
    )
    conn.execute(
        "INSERT INTO rules (module, rule_code, title, verification_status) "
        "VALUES ('audit','R-1','Rule one','verified')"
    )
    conn.execute("INSERT INTO modules (name, title, version) VALUES ('audit','Audit','1.0.0')")
    conn.execute("INSERT INTO modules (name, title, version) VALUES ('tax','Tax','1.0.0')")
    conn.commit()
    return rid, rid2


def test_export_module_records(conn, tmp_path):
    _seed(conn)
    counts = exportmod.export_module_records(conn, "audit", tmp_path / "audit")
    assert counts["knowledge_records"] == 1
    assert counts["rules"] == 1
    assert counts["relations"] == 1
    data = json.loads((tmp_path / "audit" / "knowledge_records.json").read_text())
    assert data[0]["title"] == "Revenue risk"
    csv_text = (tmp_path / "audit" / "knowledge_records.csv").read_text()
    assert "Revenue risk" in csv_text


def test_export_all_manifest(conn, tmp_path):
    _seed(conn)
    manifest_path = exportmod.export_all(conn, tmp_path / "exp")
    assert (tmp_path / "exp" / "hub.sqlite.dump").exists()
    assert (tmp_path / "exp" / "modules" / "tax" / "knowledge_records.json").exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["format"] == "ca-knowledge-hub-export"
    assert manifest["schema_version"] == 1
    assert manifest["module_versions"] == {"audit": "1.0.0", "tax": "1.0.0"}
    assert manifest["modules"]["audit"]["knowledge_records"] == 1
    # dump is re-importable SQL
    dump = (tmp_path / "exp" / "hub.sqlite.dump").read_text()
    assert "CREATE TABLE" in dump
    fresh = sqlite3.connect(":memory:")
    fresh.executescript(dump)
    n = fresh.execute("SELECT COUNT(*) FROM knowledge_records").fetchone()[0]
    assert n == 2
    fresh.close()


def test_export_summary(conn):
    _seed(conn)
    s = exportmod.export_summary(conn)
    assert s["schema_version"] == 1
    assert sorted(s["modules"]) == ["audit", "tax"]

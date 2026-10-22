"""Phase 13: full system validation per spec section 13.

Covers: all-module discovery + manifest validity + page loading,
seed idempotency across every module, cross-module FTS search,
stub link integrity (every search stub resolves to a real row),
backup/restore round-trip on a fully seeded DB, offline operation
(no network imports anywhere in app code), module enable/disable,
and migration-framework sanity.
"""
import json
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import backup as backupmod
from hubcore import bootstrap, db as dbmod
from hubcore import registry
from hubcore import search as searchmod

EXPECTED_MODULES = {"audit", "tax", "fr", "recon", "xlanalysis", "biacase",
                     "fsanalysis", "workpapers", "corpfn", "complaw",
                     "research", "study"}

SEEDERS = {  # name -> (module path, function name)
    "audit": ("modules.audit.seed", "seed_audit"),
    "tax": ("modules.tax.seed", "seed_tax"),
    "fr": ("modules.fr.seed", "seed_fr"),
    "recon": ("modules.recon.seed", "seed_recon"),
    "xlanalysis": ("modules.xlanalysis.seed", "seed_xlanalysis"),
    "biacase": ("modules.biacase.seed", "seed_biacase"),
    "fsanalysis": ("modules.fsanalysis.seed", "seed_fsanalysis"),
    "workpapers": ("modules.workpapers.seed", "seed_workpapers"),
    "corpfn": ("modules.corpfn.seed", "seed_corpfn"),
    "complaw": ("modules.complaw.seed", "seed_complaw"),
    "research": ("modules.research.seed", "seed_research"),
    "study": ("modules.study.seed", "seed_study"),
}

# (module, json-key-prefix) -> (table, id-column, id-kind)
LINK_MAP = {
    ("audit", "audit_entity"): {
        "rule": ("audit_rules", "id", str),
        "procedure": ("audit_procedures", "id", str),
        "factor": ("audit_factors", "id", str)},
    ("fr", "fr_entity"): {
        "standard": ("fr_standards", "id", str),
        "treatment": ("fr_treatments", "id", str),
        "example": ("fr_examples", "id", str)},
    ("biacase", "biacase_entity"): {
        "framework": ("case_frameworks", "framework_id", str),
        "rule": ("case_trigger_rules", "rule_id", str),
        "question": ("case_practice_questions", "question_id", str),
        "formula": ("case_formulas", "formula_id", str)},
    ("complaw", None): {"law_provision": ("law_provisions", "id", int)},
    ("workpapers", None): {"wp_template": ("wp_templates", "id", str)},
    ("study", None): {"study_deck": ("study_decks", "id", str)},
}
# tax stubs key rows by code expressions, not PKs
TAX_LINK = {
    "tax_rule": ("tax_rules", "code || ' v' || version"),
    "tax_risk": ("tax_risks", "code"),
    "tax_procedure": ("tax_procedures", "code"),
    "tax_evidence": ("tax_evidence", "code"),
    "tax_calc": ("tax_calc_tables", "code || ' v' || version"),
    "tax_scenario": ("tax_scenarios", "code"),
    "tax_legislation": ("tax_legislation", "code"),
}


def _seed_all(conn):
    import importlib
    import inspect
    counts = {}
    for name, (modpath, func) in SEEDERS.items():
        mod = importlib.import_module(modpath)
        fn = getattr(mod, func)
        if "data_dir" in inspect.signature(fn).parameters:
            counts[name] = fn(conn, HUB / "modules" / name / "data")
        else:
            counts[name] = fn(conn)
    conn.commit()
    return counts


@pytest.fixture(scope="module")
def full_conn(tmp_path_factory):
    p = tmp_path_factory.mktemp("sysval") / "hub.db"
    conn = dbmod.get_connection(str(p))
    dbmod.initialise(conn)
    bootstrap.sync_modules(conn, HUB / "modules")
    _seed_all(conn)
    yield conn, p
    conn.close()


def test_all_modules_discovered_manifests_valid_pages_load():
    found, warnings = registry.discover_with_warnings(HUB / "modules")
    assert EXPECTED_MODULES <= set(found), \
        f"missing: {EXPECTED_MODULES - set(found)}"
    for name in EXPECTED_MODULES:
        mod = found[name]
        registry.validate_manifest(mod.manifest)
        for page in registry.load_ui_pages(mod):
            assert callable(page["render"]), (name, page["id"])
    assert not [w for w in warnings if "ERROR" in str(w).upper()]


def test_seed_idempotent_across_all_modules(conn):
    first = _seed_all(conn)
    second = _seed_all(conn)
    assert first.keys() == second.keys()
    for name in first:
        assert first[name] == second[name], f"not idempotent: {name}"


def test_cross_module_search(full_conn):
    conn, _ = full_conn
    res = searchmod.search_records(conn, "audit")
    mods = {r["module"] for r in res}
    assert len(mods) >= 3, f"cross-module search too narrow: {mods}"
    res = searchmod.search_records(conn, "wacc", modules=["corpfn"])
    assert res and all(r["module"] == "corpfn" for r in res)
    res = searchmod.search_records(conn, "provision")
    mods = {r["module"] for r in res}
    assert {"complaw", "tax"} & mods


def test_fts_covers_every_seeded_module(full_conn):
    conn, _ = full_conn
    rows = conn.execute(
        "SELECT module, COUNT(*) AS n FROM record_fts GROUP BY module"
    ).fetchall()
    covered = {r["module"] for r in rows if r["n"] > 0}
    # every module that registers stubs must be FTS-searchable
    stubbed = {r["module"] for r in conn.execute(
        "SELECT DISTINCT module FROM knowledge_records").fetchall()}
    assert stubbed <= covered, f"missing FTS: {stubbed - covered}"


def test_stub_link_integrity(full_conn):
    """Every search stub must resolve to a real authority row."""
    conn, _ = full_conn
    checked = 0
    orphans = []
    for r in conn.execute(
            "SELECT id, module, extension_json FROM knowledge_records"):
        try:
            ext = json.loads(r["extension_json"] or "{}")
        except json.JSONDecodeError:
            orphans.append((r["id"], "bad json"))
            continue
        if not ext:
            continue  # guide stubs link to nothing
        resolved = False
        mod = r["module"]
        for (m, prefix), entities in LINK_MAP.items():
            if m != mod:
                continue
            if prefix:  # {"audit_entity": e, "audit_id": id}
                ent = ext.get(prefix)
                eid = ext.get(prefix.replace("_entity", "_id"))
                table, col, kind = entities[ent]
                hit = conn.execute(
                    f"SELECT 1 FROM {table} WHERE {col} = ?",
                    (kind(eid),)).fetchone()
            else:  # {"law_provision": id} / {"wp_template": id}
                (ekey, eid), = ext.items()
                table, col, kind = entities[ekey]
                hit = conn.execute(
                    f"SELECT 1 FROM {table} WHERE {col} = ?",
                    (kind(eid),)).fetchone()
            resolved = True
            checked += 1
            if not hit:
                orphans.append((r["id"], f"{table}.{col}={eid}"))
        if mod == "tax":
            ent, eid = ext.get("tax_entity"), ext.get("tax_id")
            table, expr = TAX_LINK[ent]
            hit = conn.execute(
                f"SELECT 1 FROM {table} WHERE {expr} = ?", (eid,)).fetchone()
            resolved = True
            checked += 1
            if not hit:
                orphans.append((r["id"], f"{table} code={eid}"))
        if not resolved:
            orphans.append((r["id"], f"unmapped ext {ext}"))
    assert checked > 100, f"too few links checked: {checked}"
    assert not orphans, f"orphan stubs: {orphans[:5]}"


def test_backup_restore_full_db(full_conn, tmp_path):
    _, live = full_conn
    before = {}
    conn = dbmod.get_connection(str(live))
    for (name,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name NOT LIKE 'sqlite_%'"):
        before[name] = conn.execute(
            f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    conn.close()
    dest = backupmod.backup_database(live, tmp_path / "backups")
    result = backupmod.verify_backup(dest)
    assert result["ok"], result["errors"]
    # mutate live, restore, confirm backup state returns
    conn = dbmod.get_connection(str(live))
    conn.execute("DELETE FROM knowledge_records WHERE module='research'")
    conn.commit()
    conn.close()
    backupmod.restore_database(dest, live, backup_dir=tmp_path / "backups")
    conn = dbmod.get_connection(str(live))
    for name, n in before.items():
        got = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        assert got == n, f"table {name}: {got} != {n}"
    conn.close()


def test_offline_no_network_imports():
    """App code must not import network clients (offline-first)."""
    import ast
    banned = {"socket", "requests", "urllib", "http.client", "httpx",
              "websocket"}
    offenders = []
    roots = [HUB / "hubcore", HUB / "app.py",
             *[HUB / "modules" / m for m in EXPECTED_MODULES]]
    for root in roots:
        files = [root] if root.is_file() else list(root.rglob("*.py"))
        for f in files:
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module.split(".")[0]]
                for m in mods:
                    if m in banned:
                        offenders.append(f"{f.relative_to(HUB)}: {m}")
    assert not offenders, offenders


def test_module_enable_disable(conn):
    bootstrap.sync_modules(conn, HUB / "modules")
    assert len(bootstrap.enabled_modules(conn)) == len(EXPECTED_MODULES)
    conn.execute("UPDATE modules SET enabled=0 WHERE name='research'")
    conn.commit()
    enabled = {m["name"] for m in bootstrap.enabled_modules(conn)}
    assert "research" not in enabled
    assert len(enabled) == len(EXPECTED_MODULES) - 1
    # re-sync restores manifest default (enabled)
    bootstrap.sync_modules(conn, HUB / "modules")
    enabled = {m["name"] for m in bootstrap.enabled_modules(conn)}
    assert enabled == EXPECTED_MODULES


def test_migration_framework_sanity(conn):
    from hubcore import migrations
    assert hasattr(migrations, "apply_migrations") or hasattr(
        migrations, "migrate")
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
        " AND name LIKE '%migr%'").fetchall()
    assert row, "no migration tracking table found"

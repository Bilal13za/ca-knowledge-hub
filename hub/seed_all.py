"""CA Knowledge Hub — first-run seeder.

Runs every module's seeder (all idempotent) against the hub database
and stamps settings.seed_version. Safe to re-run: seeders upsert and
rebuild their search stubs.

Usage:
    python seed_all.py [--db PATH]

The Windows launcher runs this automatically on first launch; app.py
also calls ensure_seeded() on startup as a backstop.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from pathlib import Path

HUB_DIR = Path(__file__).resolve().parent
if str(HUB_DIR) not in sys.path:
    sys.path.insert(0, str(HUB_DIR))

from hubcore import bootstrap, db as dbmod  # noqa: E402

SEED_VERSION = "1.0.0"

SEEDERS = [
    ("audit", "modules.audit.seed", "seed_audit"),
    ("tax", "modules.tax.seed", "seed_tax"),
    ("fr", "modules.fr.seed", "seed_fr"),
    ("recon", "modules.recon.seed", "seed_recon"),
    ("xlanalysis", "modules.xlanalysis.seed", "seed_xlanalysis"),
    ("biacase", "modules.biacase.seed", "seed_biacase"),
    ("fsanalysis", "modules.fsanalysis.seed", "seed_fsanalysis"),
    ("workpapers", "modules.workpapers.seed", "seed_workpapers"),
    ("corpfn", "modules.corpfn.seed", "seed_corpfn"),
    ("complaw", "modules.complaw.seed", "seed_complaw"),
    ("research", "modules.research.seed", "seed_research"),
    ("study", "modules.study.seed", "seed_study"),
]


def get_seed_version(conn) -> str | None:
    row = conn.execute(
        "SELECT value_json FROM settings WHERE key='seed_version'"
    ).fetchone()
    return json.loads(row[0]) if row else None


def set_seed_version(conn, version: str = SEED_VERSION) -> None:
    conn.execute(
        """INSERT INTO settings (key, value_json) VALUES ('seed_version', ?)
           ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json""",
        (json.dumps(version),))
    conn.commit()


def seed_all(conn, modules_dir: Path | None = None,
             verbose: bool = True) -> dict:
    """Run every module seeder. Returns {module: counts}."""
    modules_dir = Path(modules_dir) if modules_dir else HUB_DIR / "modules"
    total = {}
    for name, modpath, funcname in SEEDERS:
        mod = importlib.import_module(modpath)
        fn = getattr(mod, funcname)
        kwargs = {}
        if "data_dir" in inspect.signature(fn).parameters:
            kwargs["data_dir"] = modules_dir / name / "data"
        counts = fn(conn, **kwargs)
        conn.commit()
        total[name] = counts
        if verbose:
            print(f"  {name}: {counts}")
    set_seed_version(conn)
    return total


def ensure_seeded(conn, modules_dir: Path | None = None) -> bool:
    """Seed if the DB was never seeded (or seeded by an older version).

    Returns True when seeding ran.
    """
    if get_seed_version(conn) == SEED_VERSION:
        return False
    seed_all(conn, modules_dir, verbose=False)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed the CA Knowledge Hub DB.")
    ap.add_argument("--db", default=None,
                    help="Path to hub.db (default: data/hub.db next to the app)")
    args = ap.parse_args()

    if args.db:
        db_path = Path(args.db)
    else:
        # Same location as app.py: portable data/ next to the app.
        db_path = HUB_DIR / "data" / "hub.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = dbmod.get_connection(str(db_path))
    try:
        dbmod.initialise(conn)
        bootstrap.sync_modules(conn, HUB_DIR / "modules")
        print("Seeding modules...")
        seed_all(conn)
        print(f"Done. Database: {db_path}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

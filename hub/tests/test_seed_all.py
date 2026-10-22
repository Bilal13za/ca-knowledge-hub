"""Distribution acceptance: seed_all first-run seeder."""
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

import seed_all
from hubcore import bootstrap, db as dbmod


def test_seed_all_runs_and_stamps_version(tmp_path):
    db_path = tmp_path / "hub.db"
    conn = dbmod.get_connection(str(db_path))
    dbmod.initialise(conn)
    bootstrap.sync_modules(conn, HUB / "modules")
    counts = seed_all.seed_all(conn, HUB / "modules", verbose=False)
    assert set(counts) == {"audit", "tax", "fr", "recon", "xlanalysis",
                           "biacase", "fsanalysis", "workpapers", "corpfn",
                           "complaw", "research", "study"}
    assert seed_all.get_seed_version(conn) == seed_all.SEED_VERSION
    n = conn.execute("SELECT COUNT(*) FROM knowledge_records").fetchone()[0]
    assert n > 500, f"suspiciously few records: {n}"
    conn.close()


def test_seed_all_idempotent(tmp_path):
    db_path = tmp_path / "hub.db"
    conn = dbmod.get_connection(str(db_path))
    dbmod.initialise(conn)
    first = seed_all.seed_all(conn, HUB / "modules", verbose=False)
    second = seed_all.seed_all(conn, HUB / "modules", verbose=False)
    assert first == second
    conn.close()


def test_ensure_seeded_only_runs_once(tmp_path):
    db_path = tmp_path / "hub.db"
    conn = dbmod.get_connection(str(db_path))
    dbmod.initialise(conn)
    assert seed_all.ensure_seeded(conn, HUB / "modules") is True
    assert seed_all.ensure_seeded(conn, HUB / "modules") is False
    conn.close()

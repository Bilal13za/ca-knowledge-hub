"""Shared pytest fixtures for the Hub test suite."""
import sqlite3
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hubcore import db as dbmod


@pytest.fixture()
def conn(tmp_path):
    """A fresh, fully migrated in-memory-style Hub database (file-backed temp)."""
    c = dbmod.get_connection(tmp_path / "hub.db")
    dbmod.initialise(c)
    yield c
    c.close()


@pytest.fixture()
def modules_dir(tmp_path):
    """A fake modules/ directory with one valid and two invalid modules."""
    mods = tmp_path / "modules"
    good = mods / "demo"
    good.mkdir(parents=True)
    (good / "module.json").write_text(
        """{
          "name": "demo",
          "title": "Demo Module",
          "version": "1.2.0",
          "description": "Fixture module for registry tests.",
          "search_categories": ["demo"],
          "ui_entry_points": {"pages": "demo_pkg.ui:register_pages"},
          "extension_schema": {"type": "object"},
          "dependencies": []
        }""",
        encoding="utf-8",
    )
    bad = mods / "broken"
    bad.mkdir(parents=True)
    (bad / "module.json").write_text('{"name": "broken"}', encoding="utf-8")
    noname = mods / "nomatch"
    noname.mkdir(parents=True)
    (noname / "module.json").write_text(
        '{"name": "other", "title": "x", "version": "1.0.0", "description": "x"}',
        encoding="utf-8",
    )
    return mods

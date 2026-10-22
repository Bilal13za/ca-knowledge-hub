"""Phase 1A acceptance: module discovery, manifest validation, UI entry points."""
import json

import pytest

from hubcore import registry
from hubcore.registry import ManifestError, validate_manifest


def test_discover_finds_valid_module(modules_dir):
    found, warnings = registry.discover_with_warnings(modules_dir)
    assert "demo" in found
    assert found["demo"].version == "1.2.0"
    assert found["demo"].search_categories == ["demo"]
    # invalid ones are reported, never fatal
    assert any("broken" in w for w in warnings)
    assert any("nomatch" in w for w in warnings)


def test_discover_plain_skips_invalid_silently(modules_dir):
    found = registry.discover(modules_dir)
    assert set(found) == {"demo"}


def test_manifest_validation_rejects():
    with pytest.raises(ManifestError):
        validate_manifest({"name": "x"})
    with pytest.raises(ManifestError):
        validate_manifest(
            {"name": "Bad Name!", "title": "t", "version": "1.0.0", "description": "d"}
        )
    with pytest.raises(ManifestError):
        validate_manifest(
            {"name": "ok", "title": "t", "version": "1.0", "description": "d"}
        )


def test_check_dependencies_flags_missing(modules_dir):
    found, _ = registry.discover_with_warnings(modules_dir)
    found["demo"].manifest["dependencies"] = ["ghost"]
    warnings = registry.check_dependencies(found)
    assert any("ghost" in w for w in warnings)


def test_load_ui_pages_imports_entry_point(tmp_path, monkeypatch):
    # build a tiny importable package exposing register_pages
    pkg = tmp_path / "demo_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "ui.py").write_text(
        "def register_pages():\n"
        "    return [{'id': 'home', 'title': 'Home', "
        "'render': lambda: None, 'modes': ['study']}]",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    mod = registry.ModuleInfo(
        name="demo",
        title="Demo",
        version="1.0.0",
        description="d",
        manifest={"ui_entry_points": {"pages": "demo_pkg.ui:register_pages"}},
    )
    pages = registry.load_ui_pages(mod)
    assert len(pages) == 1 and pages[0]["id"] == "home"
    assert callable(pages[0]["render"])


def test_load_ui_pages_rejects_bad_contract(tmp_path, monkeypatch):
    pkg = tmp_path / "bad_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "ui.py").write_text(
        "def register_pages():\n    return [{'id': 'home'}]", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    mod = registry.ModuleInfo(
        name="bad",
        title="Bad",
        version="1.0.0",
        description="d",
        manifest={"ui_entry_points": {"pages": "bad_pkg.ui:register_pages"}},
    )
    with pytest.raises(ValueError):
        registry.load_ui_pages(mod)


def test_load_ui_pages_empty_without_entry_point():
    mod = registry.ModuleInfo(
        name="plain", title="P", version="1.0.0", description="d", manifest={}
    )
    assert registry.load_ui_pages(mod) == []

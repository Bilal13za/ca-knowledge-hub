"""Phase 1A acceptance: storage-provider interface + LocalFolderProvider."""
from pathlib import Path

import pytest

from hubcore import storage
from hubcore.storage import LocalFolderProvider, get_provider


def _make_source(tmp_path: Path) -> Path:
    src = tmp_path / "terabox_downloads"
    (src / "docs").mkdir(parents=True)
    (src / "notes.txt").write_text("hello", encoding="utf-8")
    (src / "docs" / "ias2.pdf").write_bytes(b"%PDF-1.4 fake")
    (src / ".hidden").write_text("skip me", encoding="utf-8")
    return src


def test_scan_lists_files_not_hidden(tmp_path):
    src = _make_source(tmp_path)
    p = LocalFolderProvider()
    p.configure({"folder": str(src)})
    staged = p.scan()
    names = sorted(s.relative for s in staged)
    assert names == ["docs/ias2.pdf", "notes.txt"]
    assert all(s.size > 0 or s.name == "notes.txt" for s in staged)


def test_fetch_copies_preserving_structure(tmp_path):
    src = _make_source(tmp_path)
    inbox = tmp_path / "inbox"
    p = LocalFolderProvider()
    p.configure({"folder": str(src)})
    staged = {s.relative: s for s in p.scan()}
    dest = p.fetch(staged["docs/ias2.pdf"], inbox)
    assert dest == inbox / "docs" / "ias2.pdf"
    assert dest.read_bytes() == b"%PDF-1.4 fake"


def test_configure_rejects_missing_folder(tmp_path):
    p = LocalFolderProvider()
    with pytest.raises(ValueError):
        p.configure({"folder": str(tmp_path / "nope")})
    with pytest.raises(ValueError):
        p.configure({})


def test_get_provider_factory(tmp_path):
    src = _make_source(tmp_path)
    p = get_provider("local_folder", {"folder": str(src)})
    assert isinstance(p, LocalFolderProvider)
    assert "Local folder" in p.describe()
    with pytest.raises(ValueError):
        get_provider("terabox_api", {})


def test_scan_requires_configuration():
    p = LocalFolderProvider()
    with pytest.raises(ValueError):
        p.scan()

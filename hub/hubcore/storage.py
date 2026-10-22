"""Storage-provider interface.

The Hub never talks to a cloud API directly. A StorageProvider stages files
from a configured location into the application's local inbox folder; the
Refresh Library (Phase 1B) then ingests from the inbox.

The first implementation is LocalFolderProvider: the user downloads files
from TeraBox (or any cloud drive) into a folder of their choice, and the
provider scans/copies from there. Switching providers later means
implementing this interface — a configuration change, not architecture.
"""
from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StagedFile:
    name: str          # file name
    path: Path         # absolute source path
    size: int          # bytes
    modified_at: str   # ISO timestamp (best effort)
    relative: str = ""  # path relative to the provider root


class StorageProvider(ABC):
    """Interface every storage provider must implement."""

    name: str = "base"

    @abstractmethod
    def configure(self, settings: dict) -> None:
        """Apply provider settings (e.g. folder path). Raise ValueError if invalid."""

    @abstractmethod
    def describe(self) -> str:
        """Human-readable description of the current configuration."""

    @abstractmethod
    def scan(self) -> list[StagedFile]:
        """List files available for staging."""

    @abstractmethod
    def fetch(self, staged: StagedFile, dest_dir: str | Path) -> Path:
        """Copy a staged file into dest_dir. Returns the destination path."""


class LocalFolderProvider(StorageProvider):
    """Manual workflow provider: scan a local folder the user fills by hand
    (e.g. downloads from TeraBox). No network, no cloud API."""

    name = "local_folder"

    def __init__(self) -> None:
        self.folder: Path | None = None

    def configure(self, settings: dict) -> None:
        folder = settings.get("folder")
        if not folder:
            raise ValueError("LocalFolderProvider requires settings['folder']")
        path = Path(folder).expanduser()
        if not path.is_dir():
            raise ValueError(f"Configured folder is not a directory: {path}")
        self.folder = path

    def describe(self) -> str:
        return f"Local folder: {self.folder}" if self.folder else "Not configured"

    def _require(self) -> Path:
        if self.folder is None:
            raise ValueError("LocalFolderProvider is not configured")
        return self.folder

    def scan(self) -> list[StagedFile]:
        root = self._require()
        staged: list[StagedFile] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith(".") or path.name.startswith("~"):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            staged.append(
                StagedFile(
                    name=path.name,
                    path=path,
                    size=stat.st_size,
                    modified_at=_iso(stat.st_mtime),
                    relative=str(path.relative_to(root)),
                )
            )
        return staged

    def fetch(self, staged: StagedFile, dest_dir: str | Path) -> Path:
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / staged.relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged.path, target)
        return target


def _iso(ts: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


PROVIDERS: dict[str, type[StorageProvider]] = {
    LocalFolderProvider.name: LocalFolderProvider,
}


def get_provider(name: str, settings: dict) -> StorageProvider:
    """Instantiate and configure a provider by name."""
    cls = PROVIDERS.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown storage provider {name!r}. Available: {sorted(PROVIDERS)}"
        )
    provider = cls()
    provider.configure(settings)
    return provider


def register_provider(cls: type[StorageProvider]) -> None:
    """Allow future providers to plug in without editing this module."""
    PROVIDERS[cls.name] = cls

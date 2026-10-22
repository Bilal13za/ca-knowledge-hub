"""Module registry: discovery, manifest validation, UI entry points.

Each module lives in ``modules/<name>/`` and ships a ``module.json``
manifest (see MODULE_DEVELOPMENT_GUIDE.md). The core discovers modules at
startup; adding a module never requires editing core code.
"""
from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_FIELDS = ("name", "title", "version", "description")
NAME_RE = re.compile(r"^[a-z0-9_]+$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass
class ModuleInfo:
    name: str
    title: str
    version: str
    description: str
    enabled: bool = True
    path: Path | None = None
    manifest: dict = field(default_factory=dict)

    @property
    def search_categories(self) -> list[str]:
        return list(self.manifest.get("search_categories", []))

    @property
    def ui_entry_points(self) -> dict:
        return dict(self.manifest.get("ui_entry_points", {}))

    @property
    def dependencies(self) -> list[str]:
        return list(self.manifest.get("dependencies", []))


class ManifestError(ValueError):
    """Raised when a module.json is invalid."""


def validate_manifest(data: dict, *, source: str = "<manifest>") -> dict:
    """Validate a manifest dict; returns it unchanged. Raises ManifestError."""
    for f in REQUIRED_FIELDS:
        if not data.get(f):
            raise ManifestError(f"{source}: missing required field '{f}'")
    if not NAME_RE.match(data["name"]):
        raise ManifestError(
            f"{source}: 'name' must match {NAME_RE.pattern} (got {data['name']!r})"
        )
    if not VERSION_RE.match(str(data["version"])):
        raise ManifestError(
            f"{source}: 'version' must be MAJOR.MINOR.PATCH (got {data['version']!r})"
        )
    ui_eps = data.get("ui_entry_points", {})
    if not isinstance(ui_eps, dict):
        raise ManifestError(f"{source}: 'ui_entry_points' must be an object")
    ext_schema = data.get("extension_schema")
    if ext_schema is not None and not isinstance(ext_schema, dict):
        raise ManifestError(f"{source}: 'extension_schema' must be an object")
    return data


def discover(modules_dir: str | Path) -> dict[str, ModuleInfo]:
    """Scan modules_dir for valid manifests. Invalid ones are skipped with
    a recorded warning (returned separately)."""
    found: dict[str, ModuleInfo] = {}
    modules_dir = Path(modules_dir)
    if not modules_dir.is_dir():
        return found
    for mod_dir in sorted(p for p in modules_dir.iterdir() if p.is_dir()):
        manifest_path = mod_dir / "module.json"
        if not manifest_path.is_file():
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            validate_manifest(data, source=str(manifest_path))
        except (json.JSONDecodeError, ManifestError, OSError):
            continue  # invalid manifests never break discovery
        if data["name"] != mod_dir.name:
            continue  # manifest name must match directory name
        found[data["name"]] = ModuleInfo(
            name=data["name"],
            title=data["title"],
            version=str(data["version"]),
            description=data["description"],
            enabled=bool(data.get("enabled", True)),
            path=mod_dir,
            manifest=data,
        )
    return found


def discover_with_warnings(
    modules_dir: str | Path,
) -> tuple[dict[str, ModuleInfo], list[str]]:
    """Like discover(), but also returns human-readable warnings for every
    skipped/invalid module directory."""
    found: dict[str, ModuleInfo] = {}
    warnings: list[str] = []
    modules_dir = Path(modules_dir)
    if not modules_dir.is_dir():
        return found, [f"modules directory not found: {modules_dir}"]
    for mod_dir in sorted(p for p in modules_dir.iterdir() if p.is_dir()):
        if mod_dir.name.startswith("_"):
            continue  # _template and other scaffolding are not modules
        manifest_path = mod_dir / "module.json"
        if not manifest_path.is_file():
            warnings.append(f"{mod_dir.name}: no module.json — skipped")
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            validate_manifest(data, source=str(manifest_path))
        except (json.JSONDecodeError, ManifestError, OSError) as exc:
            warnings.append(f"{mod_dir.name}: invalid manifest ({exc}) — skipped")
            continue
        if data["name"] != mod_dir.name:
            warnings.append(
                f"{mod_dir.name}: manifest name {data['name']!r} != directory — skipped"
            )
            continue
        found[data["name"]] = ModuleInfo(
            name=data["name"],
            title=data["title"],
            version=str(data["version"]),
            description=data["description"],
            enabled=bool(data.get("enabled", True)),
            path=mod_dir,
            manifest=data,
        )
    return found, warnings


def check_dependencies(modules: dict[str, ModuleInfo]) -> list[str]:
    """Return warnings for modules whose declared dependencies are missing."""
    warnings: list[str] = []
    for name, mod in modules.items():
        for dep in mod.dependencies:
            if dep not in modules:
                warnings.append(f"{name}: dependency '{dep}' is not installed")
    return warnings


def load_ui_pages(module: ModuleInfo) -> list[dict]:
    """Import a module's UI entry point and call register_pages().

    Expected contract (documented in MODULE_DEVELOPMENT_GUIDE.md):
        def register_pages() -> list[dict]
    where each dict has: id, title, render (callable), modes (list).
    Raises ImportError / AttributeError with a clear message on misuse.
    """
    eps = module.ui_entry_points
    target = eps.get("pages")
    if not target:
        return []
    if ":" not in target:
        raise ImportError(
            f"Module '{module.name}': ui_entry_points.pages must be "
            f"'dotted.path:callable', got {target!r}"
        )
    dotted, func_name = target.rsplit(":", 1)
    try:
        mod = importlib.import_module(dotted)
    except ImportError as exc:
        raise ImportError(
            f"Module '{module.name}': cannot import UI entry point {dotted!r}: {exc}"
        ) from exc
    func = getattr(mod, func_name, None)
    if not callable(func):
        raise AttributeError(
            f"Module '{module.name}': {dotted} has no callable {func_name!r}"
        )
    pages = func()
    for page in pages:
        for key in ("id", "title", "render"):
            if key not in page:
                raise ValueError(
                    f"Module '{module.name}': page is missing required key {key!r}"
                )
        if not callable(page["render"]):
            raise ValueError(
                f"Module '{module.name}': page {page.get('id')!r} 'render' is not callable"
            )
    return pages

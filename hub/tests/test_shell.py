"""Phase 1C acceptance: UI shell's pure helpers (no Streamlit needed).

The full boot is smoke-tested separately with a real headless Streamlit
run (see TESTING_GUIDE.md); these tests cover the navigation logic that
drives module page discovery.
"""
import importlib.util
from pathlib import Path


def _load_app_module():
    # Load app.py's pure helpers without executing Streamlit UI code:
    # we exec only the function defs we need by parsing the source.
    # Simpler and honest: import the module with a stubbed streamlit.
    import sys
    import types

    stub = types.ModuleType("streamlit")
    stub.session_state = {}
    # any attribute access returns a dummy callable
    def _dummy(*a, **k):
        class D:
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return D()
    stub.__getattr__ = lambda name: _dummy  # type: ignore[attr-defined]
    sys.modules["streamlit"] = stub
    # stub hubcore imports resolve via conftest sys.path
    spec = importlib.util.spec_from_file_location(
        "hub_app", str(Path(__file__).resolve().parent.parent / "app.py")
    )
    mod = importlib.util.module_from_spec(spec)
    # don't execute module top-level (it would call st.*); instead pull
    # the pure function source and exec it standalone.
    src = (Path(__file__).resolve().parent.parent / "app.py").read_text()
    start = src.index("def module_page_nav_items")
    end = src.index("def discover_module_pages")
    ns: dict = {}
    ns["MODES"] = ["study", "practice", "professional"]
    exec(src[start:end], ns)
    return ns


def test_module_page_nav_items_filters_by_mode():
    ns = _load_app_module()
    fn = ns["module_page_nav_items"]
    modules_info = [
        {"name": "audit", "title": "Audit", "pages": [
            {"id": "a1", "title": "Risks", "render": lambda c: None,
             "modes": ["study", "practice"]},
            {"id": "a2", "title": "Workpapers", "render": lambda c: None,
             "modes": ["professional"]},
        ]},
        {"name": "tax", "title": "Tax", "pages": []},
    ]
    study_items = fn(modules_info, "study")
    assert len(study_items) == 1
    assert study_items[0]["label"] == "Audit: Risks"
    assert study_items[0]["module"] == "audit"
    prof_items = fn(modules_info, "professional")
    assert len(prof_items) == 1 and prof_items[0]["page_id"] == "a2"
    # pages without explicit modes show in all modes
    modules_info[0]["pages"].append(
        {"id": "a3", "title": "All", "render": lambda c: None})
    assert len(fn(modules_info, "study")) == 2

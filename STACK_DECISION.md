# UI Stack Decision — CA Knowledge Hub

**Date:** 2026-10-21
**Scope:** Choose the UI toolkit for the unified CA Knowledge Hub desktop app (Windows 11, 8 GB RAM, 4th-gen i7, offline-first, SQLite, deterministic, free/open-source only).
**Decision: CONFIRM Streamlit** (with conditions listed below).

This decision was made by measurement where cheap, and documented evidence where measurement was impractical. The full five-app context: `ca-copilot`, `audit-risk-library`, `tax-engine`, `icap-case-engine`, `capt-tax` are all Streamlit apps launched via `run_windows.bat` (winget → venv → pip install → wait-for-server → open browser).

---

## 1. Comparison table

| Criterion | Streamlit | Tkinter (stdlib) | PySide6 | Textual |
|---|---|---|---|---|
| **Idle RAM, hello-world w/ tabs + 200-row table + 10-field form** | **~50 MB** (server process; measured `streamlit run`, v1.32.0) | **~26 MB** (real GUI under Xvfb; measured) | **not measurable in VM** (wheel needs `libEGL.so.1`, absent); QtCore import alone = 28 MB; documented minimal QtWidgets GUI ≈ 80–150 MB | **~38 MB** (terminal UI; measured) |
| **Browser-tab overhead (Streamlit only)** | +~150–300 MB for the Chromium/Edge tab (documented estimate, not measured here) | n/a (native window) | n/a (native window) | n/a |
| **Total estimated footprint on Bilal's 8 GB laptop** | ~200–350 MB (server + one tab) — comfortable | ~30 MB — smallest | ~150–400 MB (Qt libs + process) — acceptable | ~40 MB — smallest, wrong form factor |
| **Install/download size** | **469 MB** installed venv (measured); pip download ~90–120 MB (streamlit + pandas + pyarrow + tornado + …) | **0 MB** (stdlib; Tcl/Tk ships with Windows Python installer) | **688 MB** installed venv (measured); Windows wheel download ~130–150 MB (bundles Qt DLLs) | **37 MB** installed venv (measured) |
| **Startup time** | ~3 s to HTTP 200 on this VM (measured); expect 5–10 s on his 4th-gen i7 — acceptable | 1–2 s (instant) | 2–4 s typical (documented) | 1–2 s |
| **Offline operation** | Works offline **after one-time pip install**, BUT: telemetry is ON by default (`browser.gatherUsageStats=true` phones home to Segment on first run; fails silently offline — doesn't break the app, but must be disabled for his privacy requirement) | Fully offline, zero telemetry | Fully offline, zero telemetry | Fully offline, zero telemetry |
| **Packaging for Windows** | **zip + `run_windows.bat` already proven across all 5 apps** (winget Python, venv, pip install once, launch). PyInstaller+Streamlit is notoriously fragile (custom hooks, 300–500 MB exe, slow boot) — **not recommended** | PyInstaller single-exe works great (~15–25 MB) | PyInstaller works well (~60–120 MB exe) | Nuitka/PyInstaller OK, but irrelevant (wrong UI) |
| **Module plugin support** | **Excellent.** Core shell builds nav from module manifests; `importlib` loads `render(ctx)` page functions. No core edits needed. All 5 existing apps are already page-shaped Streamlit code → migration is mechanical refactoring, not rewriting | Workable, but every Streamlit page becomes hand-written Tk widget code — a **full rewrite** of 5 apps | Clean (`QStackedWidget` pages), but also a **full rewrite** of 5 apps | Clean in principle, but terminal UI is the wrong form factor — discard |
| **Dense data tables** | `st.dataframe` (Arrow-backed): sorting/filtering/10k+ rows out of the box; already used by tax-engine/capt-tax | `ttk.Treeview`: functional (measured with 200 rows) but manual styling, no built-in sort/filter, clunky for wide grids | `QTableView`/`QTableWidget`: best-in-class native grids | `DataTable`: good, but terminal |
| **Forms** | `st.form` + widgets; rerun-model needs `@st.cache_data` discipline | Native, verbose | Native, excellent | Good, terminal |
| **Document reading / rich text** | Markdown + `components.html` — **the existing offline collapsible-HTML mind maps already use this path** | Text widget, manual | QTextBrowser, good | Markdown, terminal |
| **Learning curve / consistency** | **Zero new learning**: Bilal's whole codebase, both launchers, and the coordinator's migration plan are Streamlit | New toolkit for the project | New toolkit; Qt API is large | New toolkit; wrong form factor |
| **License** | Apache-2.0 ✅ | PSF + Tcl/Tk (BSD-style) ✅ | **LGPLv3** ✅ for personal use (dynamic linking; fine) | MIT ✅ |
| (PyQt6 for reference) | — | — | PyQt6 = **GPLv3** — legally OK for personal-only use (obligations trigger on distribution), but PySide6/LGPL is strictly safer; avoid PyQt6 | — |

### Measured evidence log (Linux VM, 2026-10-21)

- **Tkinter:** `python3 tk_hello.py` under Xvfb (ttk.Notebook + Treeview w/ 200 rows + 10-field form): **VmRSS 26,464 kB**.
- **Streamlit 1.32.0:** `streamlit run st_hello.py --server.headless true` (tabs + `st.dataframe` 200 rows + 10 `st.text_input`): **VmRSS 50,100 kB**, 4 threads, HTTP 200 after **~3 s**.
- **Textual:** hello-world (TabbedContent + DataTable 200 rows + form): **VmRSS 38,168 kB**; venv 37 MB.
- **PySide6 6.12.0:** GUI would not start in VM (`ImportError: libEGL.so.1`); `QtCore` import-only baseline **VmRSS 27,896 kB**; venv **688 MB**; Streamlit venv **469 MB** (both installed cleanly once moved off the 512 MB /tmp tmpfs).
- These are Linux approximations; Windows numbers will differ but the ordering (Tkinter < Textual < Streamlit-server < Qt) is stable.

---

## 2. Criterion-by-criterion analysis

**(a) RAM.** Tkinter wins on raw MB, but Streamlit's ~50 MB server + one browser tab (~200–350 MB total) is ~3–4% of 8 GB. Windows 11 idles at ~2.5–3 GB; Bilal will still have >4 GB free. PySide6's 80–150 MB process is also fine, but its 688 MB install footprint and Qt DLL weight buy nothing the project needs. RAM is **not** a reason to overturn Streamlit.

**(b) Offline.** All options work offline. Streamlit has one wart: `browser.gatherUsageStats` defaults to true and the first-run telemetry ping goes to Segment. It fails silently offline and never breaks the app, but Bilal explicitly cares about privacy/offline — so the hub must ship `.streamlit/config.toml` with telemetry disabled (the existing five launchers don't do this; the hub should). This is a one-line fix, not a stack-killer.

**(c) Packaging.** The zip + `run_windows.bat` pattern is **already proven five times** on the target machine class. It keeps app code as plain `.py` files (inspectable, patchable without rebuilding an exe) and deduplicates the venv when the hub shares one environment across modules. PyInstaller would be a step backward for Streamlit specifically. For a hypothetical Qt/Tk rewrite, PyInstaller would be attractive — but that requires the rewrite first.

**(d) Plugin architecture.** The hub spec requires: module declares UI entry points in its manifest → core shell discovers/renders them with no core edits. In Streamlit this is ~20 lines of core code:

```python
# core/ui/shell.py (illustrative)
import importlib, streamlit as st
for page in registry.iter_pages():          # manifests -> [{"id","title","icon","module","render"}]
    st.sidebar.page_link(...)               # or a radio/select nav
mod = importlib.import_module(page["module"])
getattr(mod, page["render"])(ctx)           # ctx: db handle, paths, settings
```

Each existing `app.py` section becomes a `render_* (ctx)` function — mechanical, testable, no behavior change. The equivalent in Tkinter/PySide6 is equally *possible* but every page must be **rewritten** in widget code first. Streamlit is the only option where "plugin support" doesn't imply "rewrite five working apps."

**(e) Consistency.** This is the heaviest-weighted factor. The coordinator's build is already underway with a blanket build authorization; switching stacks now means rewriting ~4,000 lines of working, tested Streamlit UI (tax-engine `app.py` alone is 870 lines; icap-case-engine is 2,205) plus re-validating every test that touches UI boot (`test_app_boot.py` in capt-tax). The migration risk dwarfs any marginal RAM/startup gain.

**(f) License.** All candidates are free/open-source for this personal use. Only note: if Qt were chosen, pick **PySide6 (LGPL)**, never PyQt6 (GPL).

**(g) Dense UI.** `st.dataframe` + `st.form` + Markdown/`components.html` already carry the exact workloads in the existing apps (14-step tax chain, 13-section study app, 210-card flashcard system, collapsible offline mind maps). Native Qt tables are nicer, but "nicer tables" doesn't justify a rewrite.

---

## 3. Honest uncertainties

1. **Windows RAM figures are extrapolated**, not measured on his laptop. The browser-tab estimate (~150–300 MB) is the least certain number here; a heavy page with big dataframes could push higher. Mitigation: `@st.cache_data` on all seed/DB loads (already the pattern in the existing apps), paginate wide tables.
2. **Streamlit's rerun model** re-executes page code on every interaction. For a deterministic knowledge app this is fine, but module authors must keep `render()` functions side-effect-free and cache expensive loads — a convention the core shell should document and ideally lint for.
3. **First-run install still needs internet** (pip, ~100–150 MB download). This was already accepted in the five-app design; unchanged.
4. **Long-term Streamlit version drift**: the apps pin `streamlit>=1.32` while one pins `1.66.0`. The hub should unify on a single pin (recommend `streamlit==1.32.*` — the version measured here and the floor the codebase was written against — or re-verify on 1.66+ before pinning higher).

---

## 4. Recommendation — CONFIRM Streamlit

**Keep Streamlit.** The measured costs (50 MB server, 469 MB one-time venv, ~3 s startup) are all comfortably within the laptop's budget, and the alternatives' advantages (Tkinter's 26 MB, Qt's native tables) do not outweigh a full rewrite of five working, tested apps mid-build.

### Conditions (binding on the UI shell build)

1. **Packaging:** stay with zip + `run_windows.bat` (proven). Do NOT use PyInstaller for Streamlit.
2. **Single shared venv** for hub + all modules (469 MB once, not per-module).
3. **Ship `.streamlit/config.toml`** with `browser.gatherUsageStats = false`, `server.headless = true`, `server.enableXsrfProtection` default, and a fixed port per launcher. Telemetry off = true offline/privacy posture.
4. **Unify the Streamlit pin** across all modules (one version in the hub's `requirements.txt`).
5. **Plugin contract:** each module ships `manifest.py` declaring `PAGES = [{"id", "title", "icon", "module", "render"}]`; core `hubcore/ui/shell.py` discovers via the existing `hubcore/registry.py`, loads with `importlib`, and calls `render(ctx)` with a shared context (db, paths, settings). No core UI edits when adding a module.
6. **Performance convention:** `render()` functions must be side-effect-free; all seed/DB/dataset loads go through `@st.cache_data`; paginate tables wider than a screen.

### What would overturn this

If future profiling on Bilal's actual laptop shows the Streamlit tab persistently exceeding ~600 MB, or if a module needs true native-desktop behavior (system tray, global hotkeys, offline printing pipeline), revisit with PySide6 (LGPL) as the fallback — its plugin story is clean and its tables are best-in-class. Neither condition holds today.

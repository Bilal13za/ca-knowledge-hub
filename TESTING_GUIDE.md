# Testing Guide

**Status:** Phase 1A (v1).

## Stack

`pytest`. Run from `hub/`: `python -m pytest tests/ -q`.
All tests must run offline (no sockets). Deterministic: no randomness,
no wall-clock dependence (freeze dates in fixtures where needed).

## Rules (spec §12)

- Use synthetic data and known expected results.
- Calculations: compare against independently hand-checked examples.
- Search: assert relevant records ARE found and irrelevant ones are NOT
  presented as definitive answers.
- Ingestion: cover new / changed / unchanged / duplicate / missing /
  unsupported / unreadable files.
- Updates: assert existing data is intact after migrations and edits.
- Regression: a new module must not break earlier modules — the full
  suite runs on every phase.
- Never claim a feature works unless implemented and tested. Never claim
  a test passed unless it was executed. Report real numbers.

## Acceptance-test checklist template

Copy this into the phase report (and PROJECT_STATUS.md) at every gate:

```markdown
## Acceptance — Phase <N> (<name>)

| # | Requirement (spec ref) | Test / evidence | Expected | Actual | Pass? |
|---|------------------------|-----------------|----------|--------|-------|
| 1 |                        |                 |          |        |       |
| 2 |                        |                 |          |        |       |

Automated: <n> passed, <n> failed, <n> skipped (`pytest tests/ -q`)
Manual checks: <list>
Known limitations: <list>
Gate decision: PASS / FAIL (+ reasons)
```

## Performance evidence (2026-10-21, this VM)

Synthetic benchmark, 5,000 knowledge records across 3 modules:

| Operation | p95 | Target | Margin |
|---|---|---|---|
| Global FTS search (unscoped) | 47 ms | < 1,000 ms | ~20x |
| Workspace-scoped FTS search | 37 ms | < 1,000 ms | ~25x |
| `due_for_review()` | 0.8 ms | — | — |

This VM is faster than Bilal's laptop, but the margin is comfortable.
Full performance verification in Phase 13.

## Current suite (Phase 1A)

| File | Covers | Tests |
|---|---|---|
| `test_db.py` | schema v1, idempotent migrate, rollback+remigrate, enum enforcement, FTS5 search, integrity, workspaces CRUD | 8 |
| `test_registry.py` | discovery, manifest validation, dependency warnings, UI entry-point contract | 7 |
| `test_storage.py` | LocalFolderProvider scan/fetch, configuration errors, factory | 5 |
| `test_export.py` | per-module JSON+CSV, full dump re-import, manifest, summary | 4 |
| `test_documents.py` | Refresh Library: new/changed/unchanged/missing/unsupported/failed/ocr_needed, stable ids, sheet names, macro safety, report+timestamp | 12 |
| `test_search.py` | global search, workspace scoping, FTS sanitization, snippets | 6 |
| `test_knowledge.py` | record CRUD, versioned revisions, review-due, cross-module relations, extension validation | 8 |
| `test_workspaces.py` | workspace CRUD, last-used ordering, missing-module validation | 3 |
| `test_backup.py` | backup+verify, corruption detection, restore roundtrip + safety, rotation | 6 |
| `test_bootstrap.py` | module DB sync, vanished-module disable | 2 |
| `test_shell.py` | module nav items by mode | 1 |

Total: **60 passed** (2026-10-21).

UI shell verification (beyond pytest): headless `AppTest` boot — 0
exceptions; all 8 core pages render — 0 exceptions each. Recorded here
because AppTest needs Streamlit (not in the offline pytest env).

# CA Knowledge Hub — Project Status

**Updated:** 2026-10-21 (Phase 14 complete — Study Mode; all phases
1A→14 done)

## Current phase

**Phase 14 — COMPLETE. ALL WORK DONE.** Next: deliver the final
per-phase report to the parent agent.

## Completed phases

- **Phase 0 (2026-10-21):** Reuse audit. All five apps inventoried;
  live pytest re-run (audit 13/13, tax 46/46, case 83+1 skip, copilot
  42/43, capt 156/160 — failures are VM-only missing deps, not code
  defects). Decision: ALL FIVE MIGRATE. Seeds staged at `staging/`
  (2.8 MB, copies). See REUSE_AUDIT.md.
- **Phase 1A (2026-10-21):** Versioned SQLite schema v1 (19 tables +
  2 FTS5 indexes); migration framework with tested rollback;
  module registry + manifest spec + UI entry-point contract;
  storage-provider interface with LocalFolderProvider; export format
  (JSON+CSV+dump+manifest); module template; 22/22 pytest pass.
  UI stack decision: Streamlit CONFIRMED (STACK_DECISION.md, measured).
- **Phase 1B (2026-10-21):** Document ingestion + Refresh Library.
  Ported proven extractors from CA Copilot (PDF/DOCX/TXT/MD/CSV/XLSX;
  macros never executed). All 13 spec requirements implemented and
  tested: new/changed/unchanged via SHA-256, missing marked never
  deleted, failed files recorded as rows, failed updates preserve prior
  content, OCR-needed reporting, page-level refs, sheet names preserved,
  8-category processing report, refresh timestamp. **34/34 pytest pass.**
- **Phase 1C (2026-10-21):** UI shell + services. Streamlit app
  (`app.py`): dashboard, global search with module chips, document
  library (storage config + Refresh Library + report), knowledge-record
  browser/CRUD/versioning, workspaces UI, source register, backup/restore
  UI with verification, export UI (ZIP download), settings. Services:
  `search.py`, `knowledge.py`, `workspaces.py`, `backup.py`,
  `bootstrap.py`. `.streamlit/config.toml` (telemetry OFF, port 8506);
  `run_windows.bat` (winget Python, shared venv, waits-for-server).
  **60/60 pytest pass**; headless AppTest boot 0 exceptions; all 8 core
  pages render 0 exceptions; 5k-record FTS benchmark p95 47 ms.
- **Phase 2 (2026-10-21):** Audit Risk and Evidence Library migrated to
  `hub/modules/audit/` (module.json 1.0.0, auto-discovered by the
  registry — no core edits). 15 `audit_`-prefixed tables; 15 assertions
  and 11 cycles ported verbatim from source; 30 rule JSONs + 7 seed
  JSONs copied (not moved) from staging into `modules/audit/data/`;
  idempotent `seed.py` inserts 30 rules / 29 factors / 29 risks /
  99 procedures / 89 evidence / 58 controls and registers 158
  knowledge-record stubs (rules+risks+procedures) for global search.
  `engine.py` ports the source rule engine with identical semantics
  (`matched = not missing and any_ok and not excluded`; rules with no
  outcomes never fire; all/any/exclude conditions; tri-state
  missing-information; Verified-only plans; rule-attributed
  consolidation). UI pages: Risk Explorer, Rule Library, Procedures.
  Review-status → verification_status mapping applied
  (Verified→verified etc.). **8/8 new pytest pass; full suite
  68/68.** Limitation carried from source: no ISA/IFRS paragraph
  numbers (deliberate); Draft items exist in data but never surface in
  plans or search.
- **Phase 3 (2026-10-21):** Pakistan Tax Rules and Evidence Engine
  migrated to `hub/modules/tax/` (module.json 1.0.0, auto-discovered —
  no core edits). Engine ported file-by-file from the standalone app
  (`decision.py` 14-step chain, `calc.py`, `validate.py`, `loader.py`,
  `reconcile.py`, `export.py`; `search.py` rewritten for hub stubs;
  `db.py` replaced by a hub adapter — the source's two-DB split is now
  a **namespaced table split in the one hub database**, final call on
  the deferred Phase 1A decision). 22 `tax_`-prefixed tables; seed
  JSONs copied from staging: 63 rules (37 verified) / 26 calc tables
  (21 verified) / 35 risks / 28 evidence / 11 procedures / 28 scenarios
  / 59 legislation / 38 sources; 250 knowledge-record stubs for global
  search. Engine semantics preserved and re-verified with synthetic
  TEST content: tri-state evaluation (missing facts → needs_info),
  date-scoped calc version selection, verified-preferred selection,
  missing-input → incomplete (never invented), exclusion conditions,
  deterministic 14-step chain. Draft content stays draft — never
  presented as authoritative. UI pages: Tax Analyzer, Rule Library,
  Calculation Tables, Scenarios. **13/13 new pytest pass; full suite
  81/81.** Known content gaps carried from source (documented, not
  hidden): s.165 deadlines + s.152 services provisions draft;
  s.37 capital-vs-revenue draft; s.61 donation credit TY2025 only;
  s.4AB not encoded; Punjab 2025 negative-list needs primary-text
  confirmation.
- **Phase 4 (2026-10-21) — MVP COMPLETE.** Financial Reporting Library
  built greenfield at `hub/modules/fr/` (module.json 1.0.0; no staged
  data existed). 5 `fr_`-prefixed tables: 13 standards (IAS/IFRS,
  titles + study-aid summaries), 8 accounting treatments (transaction
  analysis, recognition, initial/subsequent measurement, journals,
  presentation, disclosure, statement impact, worked-example links,
  common mistakes), 8 worked examples with verified arithmetic,
  treatment↔standard links, defensive treatment↔audit-risk links
  (8 resolved, none dangling). Rule-based Treatment Suggester proposes
  CANDIDATE standards only — never asserts applicability; empty input
  yields no suggestions. UI pages: Treatments, Standards, Worked
  Examples, Suggester. Policy enforced by test: no paragraph numbers
  cited anywhere; all content marked extracted_unverified (study aids
  at CAF level, not verified against official text). **9/9 new pytest
  pass; full suite 90/90.**
- **Phase 5 (2026-10-21):** Accounting Reconciliation Engine at
  `hub/modules/recon/` (module.json 1.0.0). CA Copilot's deterministic
  workbench ported verbatim (`workbench.py`: inspection, duplicate
  detection, two-way reconciliation with tolerances, validation rules,
  report export) — 9 behavioural tests ported with hand-computed
  expectations. New persistence layer (`store.py`): `recon_runs`,
  `recon_datasets` (original imported data preserved verbatim),
  `recon_findings` with manual resolution requiring an explanatory
  note; XLSX/CSV finding exports. UI pages: New Reconciliation
  (upload A/B, column mapping, tolerances), Validate a File,
  Run History (resolve + export). **13/13 new pytest pass; full suite
  103/103.**
- **Phase 6 (2026-10-21):** Data Analysis Workbooks at
  `hub/modules/xlanalysis/` (module.json 1.0.0). Pure-function engine
  (`analyze.py`): cleaning with a full change log (never silent),
  variance analysis with explicit thresholds, group-by summaries, safe
  calculated columns (AST-restricted formulas — injection-tested, never
  eval()), threshold exception reporting; `templates.py` generates
  formatted openpyxl workbooks (variance/summary/exceptions) — no VBA,
  macros never executed. Runs persist reproducible recipes
  (`xla_runs`). UI pages: Analyze Data, Run History. **8/8 new pytest
  pass; full suite 111/111.**
- **Phase 7 (2026-10-21):** Business Case Analysis (BIA/BFD) at
  `hub/modules/biacase/` (module.json 1.0.0). Migrated the full
  case-engine dataset: 49 frameworks (+60 steps), 44 Decimal
  calculations, 30 trigger rules (+78 rule→framework mappings),
  16 case patterns (+97 facts), 28 concepts, 210 flashcards,
  27 mind maps, 24 practice questions (+outlines +rubrics),
  6 calculation examples, 52 LOs / 12 topics / 4 papers (ICAP Scheme
  2025 naming verified: CAF-7 "Business Insights and Analysis",
  CFAP-4 "Strategic Business Finance"; 2021-predecessor LOs honestly
  marked provisional). Engines ported verbatim (trigger rules with
  never-assume-missing-facts semantics, framework recommendations,
  Decimal calculations with MissingInputError, recommendation builder
  from user inputs only). Student tables (attempts, mistake log,
  flashcard progress) protected from seeding — test-verified. Source
  verification vocabulary mapped to the hub enum
  (verified_official→verified etc.). UI pages: Case Analyzer (v1
  chain), Frameworks, Calculations, Practice, Flashcards, Syllabus.
  **12/12 new pytest pass; full suite 123/123.**
- **Phase 8 (2026-10-21):** Financial Statement Analysis at
  `hub/modules/fsanalysis/` (module.json 1.0.0). Decimal ratio engine
  (16 ratios: profitability, liquidity, solvency, efficiency, cash —
  all hand-verified in tests), trend analysis with direction labels,
  common-size statements, working-capital cycle, and rule-based
  red-flag indicators. Rules: ratios with missing inputs are skipped
  (never invented); flags are investigation prompts with explanations
  (never proof of error/fraud); trend-based flags require trend data.
  Runs persist inputs + results for reproducibility (`fs_runs`). UI
  pages: Ratio Analysis, Trends & Common Size, Working Capital,
  History. **8/8 new pytest pass; full suite 131/131.**
- **Phase 9 (2026-10-21):** Audit Working Papers at
  `hub/modules/workpapers/` (module.json 1.0.0). 4 `wp_`-prefixed
  tables; 9 generic templates (planning, risk register, control
  description/test, substantive procedures, evidence register, review
  and completion checklists, exception log) — each carrying the
  disclaimer that it does not satisfy any particular firm's
  methodology. Working-paper instances with draft→completed workflow,
  exception tracking (clearing requires a resolution note), evidence
  register. UI pages: Templates, Working Papers, Exceptions.
  **8/8 new pytest pass; full suite 139/139.**
- **Phase 10 (2026-10-21):** Corporate Finance at
  `hub/modules/corpfn/` (module.json 1.0.0). Decimal engine: NPV
  (with workings), IRR (bisection with zero-check), payback /
  discounted payback, CAPM, WACC (market-value weights, after-tax
  debt), Gordon growth valuation, one-at-a-time sensitivity analysis.
  Assumptions are visible on every result; runs saved with inputs for
  reproducibility (`cf_runs`). 5 study-guide stubs (user_note status).
  UI pages: Investment Appraisal, Cost of Capital, Valuation &
  Sensitivity, Saved Runs. **13/13 new pytest pass (hand-verified
  values: NPV −4.73, CAPM 15.60%, WACC 12.20%, Gordon 50.00,
  payback 2.57 periods); full suite 152/152.**
- **Phase 11 (2026-10-21):** Company Law & Compliance at
  `hub/modules/complaw/` (module.json 1.0.0). 4 `law_`-prefixed
  tables. Honesty-first design: the 8 seeded provision entries are
  *research topics* with section_no NULL and `user_note` status —
  zero section numbers asserted (test-enforced); each carries an
  "UNTRACED — verify against the official Companies Act, 2017 text"
  source note. Tracing workflow lets Bilal add section numbers with
  source refs and verification status. Company profiles, compliance
  calendar (user-entered ISO deadlines; overdue/upcoming computed,
  never stored; done requires a date), filing register. UI pages:
  Provisions, Companies, Calendar, Filings. **7/7 new pytest pass;
  full suite 159/159.**
- **Phase 12 (2026-10-21):** Research Workflows at
  `hub/modules/research/` (module.json 1.0.0). 5 `rs_`-prefixed
  tables: issue register, source library (statute/circular/book/
  website/note/precedent with reliability), per-source findings,
  source comparisons (agree/conflict/unclear), and append-only
  versioned conclusions (history never overwritten; current = latest
  version). 3 methodology guides. UI pages: Issues, Workspace (tabbed:
  Sources / Findings / Comparisons / Conclusions). **6/6 new pytest
  pass; full suite 165/165.**
- **Phase 13 (2026-10-21):** Full system validation at
  `hub/tests/test_system_validation.py` (9 tests, all passing):
  all 11 modules discovered with valid manifests and loadable UI
  pages; seed idempotency across every module; cross-module FTS
  search ("audit" hits ≥3 modules); stub link integrity — every
  search stub's `extension_json` resolves to a real authority row
  (100+ links checked, zero orphans); FTS coverage for every stubbed
  module; backup/restore round-trip on a fully seeded DB (all table
  counts match after restore); offline-first verified by static
  scan (no socket/requests/urllib/http.client imports in app code);
  module enable/disable via `bootstrap.sync_modules`;
  migration-framework sanity. **One real bug found and fixed by the
  validation:** `backup_database()` did a raw file copy while the
  app held the DB open in WAL mode, so the backup could miss
  uncheckpointed frames — it now runs `PRAGMA
  wal_checkpoint(TRUNCATE)` before copying. **Full suite: 174/174
  pytest pass.**
- **Phase 14 (2026-10-21):** Study Mode at `hub/modules/study/`
  (module.json 1.0.0) — the REUSE_AUDIT "MIGRATE" decision for the
  CAPT app, which Phases 1–13 had left unbuilt. 7 `study_`-prefixed
  tables: decks, cards, SM-2 review state, 131-question bank with
  self-marked attempts, plans + plan items. SM-2 engine
  (`sm2.py`) migrated with identical semantics from the CAPT app's
  proven `core/sr.py` (again/hard/good/easy → q 0/3/4/5, EF floor
  1.3, hard-interval 1.2× conservative tweak). Deterministic revision
  planner: day-by-day from tomorrow to the exam date, weak chapters
  first, respects daily hours, identical inputs → identical plan
  (test-verified). Seeded from `staging/capt/content_pack.json`
  (copied to `hub/modules/study/data/`): 15 decks (14 chapters +
  definitions), 14 definition flashcards, all 131 questions with
  solutions. The pack is Bilal's personal study data (Murtaza
  Quaid's textbook) — private to his install, consistent with the
  shipped capt-tax ZIP which also bundles it; never redistributed
  publicly. UI pages: Flashcards, Question Bank, Revision Planner
  (all in the "study" mode). Wired into `seed_all.py` and the
  Phase-13 system-validation suite (12 modules). **11/11 new pytest
  pass; full suite 188/188.**
- **Distribution (2026-10-21):** `ca-knowledge-hub-windows-v1.0.0.zip`
  (193 files, ~853 KB) + `run_windows.bat` (winget Python install,
  venv, waits-for-server browser open, port 8506, first-run
  `seed_all.py`). New `hub/seed_all.py` runs all 12 module seeders
  idempotently and stamps `settings.seed_version`; `app.py`
  `ensure_first_run()` calls it as a backstop, so first launch is
  self-sufficient even without the launcher. Launcher also fixed to
  pass `--server.port 8506` (was defaulting to 8501 while the
  already-running check used 8506).
- **§14 deferral — optional Ollama Study Coach module:** REUSE_AUDIT
  decided Copilot's `ai.py`/Ollama becomes an optional module (spec
  §3D), never core. Not built in this pass: the core is complete
  and verified offline-first without it (Phase-13 static scan), and
  adding a localhost-HTTP client module would need the offline test
  to carve out an exception. Simplest reliable alternative: the hub
  works fully without AI, and the standalone CA Copilot app (with
  its Study Coach) remains available as before. A thin optional
  Ollama module is the natural Phase 15.

## Features implemented

- `hubcore/db.py`, `migrations.py`, `001_initial.sql`
- `hubcore/registry.py`, `hubcore/storage.py`, `hubcore/export.py`
- `hub/modules/_template/` (module.json, ui.py, README)
- `hub/tests/`: test_db (8), test_registry (7), test_storage (5),
  test_export (4) — **22 passed**
- Docs: ARCHITECTURE.md, DATABASE_SCHEMA.md,
  MODULE_DEVELOPMENT_GUIDE.md, SOURCE_VERIFICATION_POLICY.md,
  TESTING_GUIDE.md, BACKUP_AND_RESTORE.md (policy), USER_GUIDE.md
  (stub), CHANGELOG.md, STACK_DECISION.md (pending from researcher)

## Actual test results

`python -m pytest tests/ -q` from `hub/` → **22 passed in 0.16s**
(2026-10-21). One defect found and fixed during the phase:
rollback deleted `schema_migrations` before removing its own row —
fixed by checking table existence first; regression covered by
`test_rollback_and_remigrate`.

## Known defects

None open. (VM-only dependency gaps noted in Phase 0 affect the *source*
apps' suites, not the Hub.)

## Current database version

Schema v1 (`001_initial.sql`). No production database yet (first created
in Phase 1C).

## Outstanding requirements

- UI stack decision with written rationale (researcher running) — must
  land before Phase 1C.
- Tax knowledge/working-data split: two files vs namespaced tables —
  final call during Phase 3 seeding (documented exception candidate).

## Backup status

N/A — no user data yet. Backup policy recorded in BACKUP_AND_RESTORE.md;
implementation in Phase 1C.

## Phase 1C acceptance checklist (spec §8) — ALL PASS ✅

| # | Requirement | Status |
|---|---|---|
| 1 | Dashboard | ✅ renders, 0 exceptions |
| 2 | Global search with module chips | ✅ service + UI |
| 3 | Three mode skeletons (study/practice/professional) | ✅ mode radio; module pages filter by mode |
| 4 | Workspace create/switch (§4B) | ✅ service + UI |
| 5 | Knowledge-record CRUD | ✅ service + UI incl. versioned revisions |
| 6 | Source viewer | ✅ source register UI |
| 7 | Processing history | ✅ documents tab + `last_refresh` in settings |
| 8 | Export (JSON+CSV+dump+manifest) | ✅ service + ZIP download UI |
| 9 | Backup/restore with automated verification | ✅ service + UI, 6 tests |
| 10 | UI stack decision with written rationale | ✅ STACK_DECISION.md — Streamlit CONFIRMED |
| 11 | Performance targets achievable | ✅ benchmarked: 5k-record FTS p95 47ms (target <1s) |

Automated: **60 passed, 0 failed** (`pytest tests/ -q`).
Manual/UI: headless AppTest boot 0 exceptions; all 8 core pages 0 exceptions.

## Exact next action

Done. Deliver the final per-phase report to the parent agent
(features, real test numbers, limitations, next step per phase).

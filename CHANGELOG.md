# Changelog

## [1.0.1] — 2026-10-21 — pandas 3 compatibility (xlanalysis)

### Fixed
- `modules/xlanalysis/analyze.py`: three pandas-3 incompatibilities that broke
  fresh installs (pip now resolves `pandas>=2.0` to pandas 3.x):
  - `clean_frame` whitespace stripping now recognises the pandas 3 `str`
    dtype as well as the pandas 2 `object` dtype.
  - `clean_frame` date normalisation no longer mangles pure-number columns
    ("1000" parses as year 1000 on pandas 3, corrupting Budget-style columns).
  - `variance_analysis` builds the variance-pct series element-wise instead
    of masked assignment into an object-dtype Series (removed pandas 3
    code path). Full suite: 188/188 pass on pandas 3.0.

## [0.3.0] — 2026-10-21 — Phase 1C complete

### Added
- UI shell (`hub/app.py`, Streamlit — stack CONFIRMED by STACK_DECISION.md):
  dashboard, global search with module filter chips, document library
  (storage config + Refresh Library + processing report), knowledge-record
  browser/CRUD/versioning, workspaces UI, source register, backup/restore
  UI with verification, export UI (ZIP download), settings.
- `hubcore/search.py` (workspace-scoped FTS search), `hubcore/knowledge.py`
  (CRUD + versioned revisions + review-due + cross-module relations),
  `hubcore/workspaces.py`, `hubcore/backup.py` (verified backup/restore/
  rotation), `hubcore/bootstrap.py` (module DB sync).
- `.streamlit/config.toml`: telemetry OFF, headless, fixed port 8506.
- `run_windows.bat`: winget Python, shared venv, waits-for-server browser
  open (mirrors proven launcher pattern).
- `test_shell.py`: nav logic unit tests.
- `requirements.txt`: `streamlit==1.32.*` (Apache-2.0) unified pin.

### Verified
- Headless Streamlit boot: HTTP 200, zero exceptions (AppTest).
- All 8 core pages render with zero exceptions (AppTest).
- Synthetic benchmark: 5,000-record FTS search p95 47 ms (target < 1 s).

## [0.2.0] — 2026-10-21 — Phase 1B complete

### Added
- `hubcore/extractors.py`: safe text extraction for PDF, DOCX, TXT,
  Markdown, CSV, XLSX (ported from CA Copilot Local under Phase 0
  MIGRATE decision; macros never executed; scanned PDFs reported).
- `hubcore/documents.py`: Refresh Library implementing all 13 spec
  requirements — new/changed/unchanged detection via SHA-256, missing
  sources marked (never auto-deleted), failed files recorded as rows,
  failed updates preserve previous content, OCR-needed reporting,
  page-level PDF refs, sheet-name preservation, processing report with
  8 categories, refresh timestamp in settings.
- `test_documents.py`: 12 tests covering every file state.
- Runtime deps: pypdf (BSD-3), python-docx (MIT), openpyxl (MIT) —
  licences verified.

### Fixed
- Failed files now leave a `status='failed'` document row (visible,
  retried next refresh) instead of vanishing silently.

## [0.1.0] — 2026-10-21 — Phase 1A complete

### Added
- Versioned SQLite schema (v1): 19 tables + 2 FTS5 indexes covering all
  spec §4 core entities; `verification_status` enum; `review_due_date`
  on technical records.
- Migration framework (`hubcore/migrations.py`): `-- UP --` / `-- DOWN --`
  SQL files, idempotent apply, rollback tested.
- Module registry (`hubcore/registry.py`): manifest discovery + validation,
  dependency warnings, UI entry-point contract (`register_pages()`).
- Storage-provider interface (`hubcore/storage.py`) with
  `LocalFolderProvider` (manual folder → inbox; no cloud API).
- Export format (`hubcore/export.py`): per-module JSON + CSV, full SQLite
  dump, `manifest.json`.
- Module template (`hub/modules/_template/`).
- Test suite: 22 pytest tests, all passing.
- Docs: ARCHITECTURE.md, DATABASE_SCHEMA.md, MODULE_DEVELOPMENT_GUIDE.md,
  SOURCE_VERIFICATION_POLICY.md, TESTING_GUIDE.md, PROJECT_STATUS.md.

### Decisions
- UI stack evaluation delegated; rationale to be recorded in
  STACK_DECISION.md before Phase 1C.
- Tax engine knowledge/working-data split: final form (two files vs
  namespaced tables) deferred to Phase 1A review / Phase 3.

## 2026-10-21 — Phase 2: Audit Risk and Evidence Library migrated

- New module `hub/modules/audit/` (module.json 1.0.0): 15 `audit_`-prefixed
  tables, idempotent seeder, rule engine with source-identical semantics,
  three UI pages (Risk Explorer, Rule Library, Procedures).
- Data migrated from staging (copies): 30 rules, 29 factors, 29 risks,
  99 procedures, 89 evidence, 58 controls, 15 assertions, 11 cycles;
  158 knowledge-record stubs for global search.
- Full suite: 68/68 pytest pass (8 new Phase 2 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.

## 2026-10-21 — Phase 3: Pakistan Tax Rules and Evidence Engine migrated

- New module `hub/modules/tax/` (module.json 1.0.0): 22 `tax_`-prefixed
  tables (knowledge + working-data namespaced split — final call on the
  deferred Phase 1A two-DB decision); engine ported file-by-file
  (decision 14-step chain, calc, validate, loader, reconcile, export).
- Data migrated from staging (copies): 63 rules (37 verified), 26 calc
  tables (21 verified), 35 risks, 28 evidence, 11 procedures,
  28 scenarios, 59 legislation, 38 sources; 250 knowledge-record stubs.
- Behaviour re-verified with synthetic TEST content (tri-state eval,
  date-scoped versions, verified-preferred calcs, never-invented inputs).
- UI pages: Tax Analyzer, Rule Library, Calculation Tables, Scenarios.
- Full suite: 81/81 pytest pass (13 new Phase 3 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.

## 2026-10-21 — Phase 4: Financial Reporting Library built (MVP COMPLETE)

- New greenfield module `hub/modules/fr/` (module.json 1.0.0): 5
  `fr_`-prefixed tables; 13 IAS/IFRS standards, 8 accounting treatments
  (recognition, measurement, journals, presentation, disclosure,
  statement impact, common mistakes), 8 worked examples, 8 audit-risk
  cross-links; rule-based Treatment Suggester (candidates only).
- Content policy: all extracted_unverified study aids; no paragraph
  numbers (test-enforced).
- UI pages: Treatments, Standards, Worked Examples, Suggester.
- Full suite: 90/90 pytest pass (9 new Phase 4 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.
- MVP (Phases 0–4) COMPLETE.

## 2026-10-21 — Phase 5: Accounting Reconciliation Engine

- New module `hub/modules/recon/` (module.json 1.0.0): CA Copilot's
  deterministic workbench ported verbatim + `store.py` persistence
  (recon_runs/datasets/findings); manual resolution with required
  notes; XLSX/CSV exports; original imports preserved verbatim.
- UI pages: New Reconciliation, Validate a File, Run History.
- Full suite: 103/103 pytest pass (13 new Phase 5 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.

## 2026-10-21 — Phase 6: Data Analysis Workbooks

- New module `hub/modules/xlanalysis/` (module.json 1.0.0): cleaning
  (logged), variance analysis (explicit thresholds), group-by summaries,
  safe calculated columns (AST whitelist, injection-tested), exception
  reporting, formatted openpyxl workbooks, reproducible run recipes.
- UI pages: Analyze Data, Run History.
- Full suite: 111/111 pytest pass (8 new Phase 6 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.

## 2026-10-21 — Phase 7: Business Case Analysis (BIA/BFD) migrated

- New module `hub/modules/biacase/` (module.json 1.0.0): 26
  case_-prefixed tables; full case-engine dataset migrated
  (49 frameworks, 44 Decimal calculations, 30 trigger rules,
  210 flashcards, 24 practice questions, 52 LOs); five engine modules
  ported verbatim + `casedb.py` DB adapter; student tables
  seed-protected.
- UI pages: Case Analyzer, Frameworks, Calculations, Practice,
  Flashcards, Syllabus.
- Full suite: 123/123 pytest pass (12 new Phase 7 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.

## 2026-10-21 — Phase 8: Financial Statement Analysis

- New module `hub/modules/fsanalysis/` (module.json 1.0.0): Decimal
  ratio engine (16 ratios), trends, common-size, working-capital
  cycle, red-flag indicators (investigation prompts only); saved runs
  with inputs for reproducibility.
- UI pages: Ratio Analysis, Trends & Common Size, Working Capital,
  History.
- Full suite: 131/131 pytest pass (8 new Phase 8 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.

## 2026-10-21 — Phase 9: Audit Working Papers

- New module `hub/modules/workpapers/` (module.json 1.0.0): 9 generic
  templates (all disclaimed), paper instances with review workflow,
  exception tracking (resolution required), evidence register.
- UI pages: Templates, Working Papers, Exceptions.
- Full suite: 139/139 pytest pass (8 new Phase 9 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.

## 2026-10-21 — Phase 10: Corporate Finance

- New module `hub/modules/corpfn/` (module.json 1.0.0): Decimal
  NPV/IRR/payback/CAPM/WACC/Gordon/sensitivity engine with visible
  assumptions and reproducible saved runs; 5 study-guide stubs.
- UI pages: Investment Appraisal, Cost of Capital, Valuation &
  Sensitivity, Saved Runs.
- Full suite: 152/152 pytest pass (13 new Phase 10 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.

## 2026-10-21 — Phase 11: Company Law & Compliance

- New module `hub/modules/complaw/` (module.json 1.0.0): provision
  notes with verification status (8 starter topics, no section
  numbers asserted — test-enforced), tracing workflow, company
  profiles, compliance calendar (computed overdue/upcoming), filing
  register.
- UI pages: Provisions, Companies, Calendar, Filings.
- Full suite: 159/159 pytest pass (7 new Phase 11 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.

## 2026-10-21 — Phase 12: Research Workflows

- New module `hub/modules/research/` (module.json 1.0.0): issue
  register, source library, findings, comparisons
  (agree/conflict/unclear), append-only versioned conclusions;
  3 methodology guides.
- UI pages: Issues, Workspace (Sources/Findings/Comparisons/
  Conclusions tabs).
- Full suite: 165/165 pytest pass (6 new Phase 12 tests).
- Docs: PROJECT_STATUS, ARCHITECTURE, DATABASE_SCHEMA updated.

## 2026-10-21 — Phase 13: Full System Validation

- New `hub/tests/test_system_validation.py` (9 tests): module
  discovery/manifest/page loading, seed idempotency, cross-module
  search, stub link integrity (100+ links, 0 orphans), FTS coverage,
  backup/restore round-trip on fully seeded DB, offline static scan,
  enable/disable, migration sanity.
- Bug found and fixed: `hubcore/backup.py::backup_database` now
  checkpoints WAL before the file copy (backups were at risk of
  missing uncheckpointed frames while the app held the DB open).
- Full suite: 174/174 pytest pass.
- Docs: PROJECT_STATUS updated (all phases 1A→13 complete).

## 2026-10-21 — Phase 14: Study Mode (+ distribution)

- New module `hub/modules/study/` (module.json 1.0.0): SM-2 engine
  (migrated semantics from the CAPT app), 15 decks / 14 cards /
  131 questions seeded from Bilal's private content pack,
  deterministic revision planner, self-marked question attempts.
- UI pages: Flashcards, Question Bank, Revision Planner.
- New `hub/seed_all.py`: idempotent first-run seeder for all 12
  modules (stamps settings.seed_version); wired into app.py
  ensure_first_run and run_windows.bat.
- Distribution: `ca-knowledge-hub-windows-v1.0.0.zip` (193 files,
  ~853 KB) at ~/workspace/ca-knowledge-hub/.
- Launcher fix: --server.port 8506 now passed explicitly.
- Full suite: 188/188 pytest pass (11 new study tests).
- §14 deferral recorded: optional Ollama Study Coach module
  (natural Phase 15); hub is complete and offline-verified without it.

# REUSE AUDIT — Phase 0

**Date:** 2026-10-21
**Spec:** `master-prompt-v2.md`, Phase 0
**Method:** source-tree inspection, SQLite schema/row-count reads, seed-file
inventory, and live `pytest` runs of all five existing suites in this VM.
No application code was written or modified; all five source apps are
untouched. Seed datasets were **copied** (not moved) to
`~/workspace/ca-knowledge-hub/staging/`.

## Live test verification (2026-10-21, this VM)

| App | Result | Notes |
|---|---|---|
| ca-copilot | 42/43 pass | 1 failure = `ModuleNotFoundError: pypdf` — missing in this Linux VM only; pypdf is a declared dependency installed by `run_windows.bat` on Windows. Not a code defect. |
| audit-risk-library | 13/13 pass | — |
| tax-engine | 46/46 pass | — |
| icap-case-engine | 83 pass, 1 skipped | Skip is the documented one. |
| capt-tax | 156/160 pass | 4 failures = `ModuleNotFoundError: streamlit` in `test_app_boot.py` — missing in this Linux VM only; installed by the launcher on Windows. Not a code defect. |

All failures are environment gaps in this VM, not code defects. Every suite
is green on its target machine (Windows + launcher-installed deps).

## App 1 — CA Copilot Local (`~/workspace/ca-copilot`)

- **Stack:** Streamlit ≥1.32, pandas, openpyxl, pypdf, python-docx. Optional
  Ollama integration (`ai.py`, Study Coach) — never required for core use.
- **Schema** (`src/ca_copilot/migrations/001_initial.sql`, versioned via
  `schema_migrations`): `documents`, `doc_chunks` (+FTS), `chats`,
  `chat_messages`, `subjects`, `topics`, `doc_subjects`, `notes`,
  `practice_attempts`, `revision_tasks`, `analysis_jobs`, `report_files`,
  `settings_kv`, `tax_rule_sources`. 15 tables.
- **Ingestion:** PDF, DOCX, XLSX, CSV, TXT, Markdown — exactly the six
  Phase 1B formats. `extractors.py` + `documents.py`.
- **Services:** `backup.py` (backup/restore), `revision.py` (revision
  tracker), `study.py`, `workbench.py` (inspection / duplicates /
  reconciliation / validation), `config.py` (stdlib JSON, no PyYAML).
- **Data:** runtime DB (not committed); `sample_data/` (CSVs,
  `question_bank.json`, study notes).
- **Tests:** 43 (42 pass here; 1 env-only failure, see above).
- **Launcher:** `run_windows.bat` v3 (winget Python install, venv,
  waits-for-server browser open).
- **Decision: MIGRATE.**
- **Reasons:** proven ingestion for all six Phase-1B formats; working FTS
  search; versioned migration framework; backup/restore service; study
  tracking tables. `workbench.py` pre-seeds Phases 5–6 logic.
  `ai.py`/Ollama becomes the optional-AI module (spec §3D), never core.
- **Hub destination:** Phases 1B (ingestion), 1C (UI shell, search, backup,
  Study Mode tables); `workbench.py` → Phases 5–6.
- **Staged:** `staging/copilot/001_initial.sql` (schema reference).

## App 2 — Audit Risk and Evidence Library (`~/workspace/audit-risk-library`)

- **Stack:** Streamlit ≥1.32, openpyxl.
- **Schema/data** (`library.db`, seeded by `seed.py` from editable JSON):
  30 rules (`data/rules/RULE-*.json`, 13 fields each), 29 business factors,
  29 factor→risk links, 29 risk events, 99 audit procedures, 89 evidence
  items, 58 controls, 15 assertions; link tables `procedure_assertion`
  (135), `procedure_evidence` (164), `risk_assertion` (63),
  `risk_control` (59), `risk_procedure` (102). 6 business cycles
  (revenue, purchases, inventory, payroll, cash, PPE, financial reporting).
  `standards` table intentionally empty — no invented ISA paragraph
  numbers (see `docs/REFERENCES.md`).
- **Services:** `engine.py` (chain traversal), `export.py` (CSV + formatted
  Excel workpapers), `db.py`.
- **Tests:** 13/13 pass (incl. inventory-theft end-to-end).
- **Launcher:** `run_windows.bat` OK.
- **Decision: MIGRATE.**
- **Reasons:** complete, tested risk→assertion→control→procedure→evidence→
  exception→follow-up chain data; the editable rule-JSON workflow
  (`data/rules/*.json` → `seed.py` → `pytest`) is exactly the no-code
  knowledge-update pattern the Hub requires.
- **Hub destination:** Phase 2 (seed content + chain logic).
- **Staged:** `staging/audit/` — 30 rule JSONs, `seed.py`, `data/seed/`
  builders + cycle JSONs.

## App 3 — Pakistan Tax Risk, Rules and Evidence Engine (`~/workspace/tax-engine`)

- **Stack:** Streamlit ≥1.32, openpyxl.
- **Schema/data** (versioned `schema/schema_knowledge.sql`,
  `schema/schema_workdata.sql`; seeded from `seed/*.json`):
  `tax_knowledge.db` — 63 tax rules (37 verified), 26 calc tables,
  24 rule↔calc links, 35 tax risks, 28 evidence types, 11 procedures,
  28 scenarios, 59 legislation rows, 38 sources, 196 FTS documents;
  link tables `rule_evidence` (200), `rule_legislation` (86),
  `rule_procedures` (117), `rule_risks` (129). `tax_workdata.db` —
  runtime working data (empty at rest).
- **Notable design:** deliberate two-database separation — verified law
  library vs mutable working data — as a contamination barrier. Tri-state
  condition evaluation, date-scoped rules, verified-preferred calculations.
  Documented content gaps (unverifiable provisions marked draft).
- **Tests:** 46/46 pass (incl. offline sockets-disabled test).
- **Launcher:** `run_windows.bat` OK.
- **Decision: MIGRATE**, preserving the knowledge/working-data separation.
  Whether it stays two SQLite files (the spec's documented-exception
  clause, §4 Layer 3) or becomes namespaced tables in one file is a
  **Phase 1A decision** — the barrier itself is non-negotiable.
- **Reasons:** the verified/unverified discipline and source register are
  the strongest in the collection; calc tables + engine logic are directly
  reusable.
- **Hub destination:** Phase 3 (seed content + calculation engine).
- **Staged:** `staging/tax/` — seed JSONs + `incoming/` + both schema SQL
  + `SEED_FORMAT.md`.

## App 4 — ICAP Business Case Analysis and Decision Engine (`~/workspace/icap-case-engine`)

- **Stack:** Streamlit ≥1.32, openpyxl.
- **Data** (`data/*.json`, first-run seeded; no committed `.db`):
  585 seed rows — 49 frameworks, 30 trigger rules, 44 Decimal
  calculations, 16 case patterns, 24 practice questions, plus Study Aids
  (210 flashcards, 27 mind maps, 44-formula quick-sheets).
  Syllabus verification done: ICAP Scheme 2025 (CAF-7 Business Insights
  and Analysis; CFAP-4 Strategic Business Finance).
- **Tests:** 83 pass, 1 documented skip.
- **Launcher:** `run_windows.bat` OK (port 8504).
- **Decision: MIGRATE.**
- **Reasons:** rule-based trigger logic and framework library are proven;
  Decimal calculation workbench is reusable service logic.
- **Hub destination:** Phase 7 (seed content + trigger/calc logic).
- **Staged:** `staging/case/` — 11 seed JSONs.

## App 5 — CAPT Taxation Exam Preparation System (`~/workspace/capt-tax`)

- **Stack:** Streamlit 1.66.0 (pinned), python-docx.
- **Data:** `data/content_pack.json` (875 KB) — 14 chapters, 287 pages,
  131 practice questions, 14 definitions, derived from Murtaza Quaid's
  *Taxation: Principles and Compliance* (Bilal's teacher). For Bilal's
  **personal study use**; stays in his private data, never redistributed.
  `data/app.db` in repo is demo-state; the real pack loads on first run.
- **Services** (`core/`): SM-2 flashcards (`sr.py`), revision planner
  (`planner.py`), chapter maps (`studymaps.py`, `mapcards.py`), mock
  exams (`exams.py`), answer approaches (`approaches.py`), pitfalls
  (`pitfalls.py`), backup (`backup.py`), search (`search.py`),
  importer (`importer.py`, `content_pack.py`).
- **Tests:** 160 (156 pass here; 4 env-only failures, see above).
- **Launcher:** `run_windows.bat` OK (port 8505).
- **Decision: MIGRATE.**
- **Reasons:** the SM-2 engine, planner, map-cards, and chapter-importance
  machinery are the Hub's Study Mode accelerator — no equivalent exists
  in the other four apps.
- **Hub destination:** Study Mode content + study services (Phase 1C
  skeleton, populated through Phases 2–4).
- **Staged:** `staging/capt/content_pack.json`.

## Cross-cutting decisions

- **All five: MIGRATE. None: WRAP. None: RETIRE (yet).** Wrapping would
  preserve five silos and contradict the one-platform vision; every app's
  schema is SQLite/JSON and its logic is modular Python, so migration is
  clean. No app is retired outright — each contributes proven,
  tested components.
- **Standalone fallback:** the five shipped ZIPs/launchers are frozen (no
  further feature work) and retained as working fallback until the Hub's
  Phase 1C passes acceptance; full retirement of standalones at MVP
  (Phase 4).
- **Stack precedent:** all five apps are Streamlit + `run_windows.bat` +
  offline-first + deterministic (Ollama is optional-only). Phase 1A's
  required stack rationale should start from this precedent and confirm
  or overturn it with measurements, not default blindly.
- **Staging manifest:** `staging/` (2.8 MB) holds copies only — audit rule
  JSONs + seed builders, tax seed/schema, case seed JSONs, capt content
  pack, copilot initial schema. Sources untouched.

## Acceptance (Phase 0 criteria from v2 §8)

- [x] Every existing application inventoried (schema, data volumes, tests,
      launcher).
- [x] MIGRATE / WRAP / RETIRE recorded with written reasons for all five.
- [x] Seed datasets staged for Phases 2, 3, 7 (+ Study Mode + 1B/1C).
- [x] No new application code written in Phase 0.
- [x] No working, tested component rebuilt or discarded without a
      documented reason.

**Known limitations:** VM-only test gaps (pypdf, streamlit missing here;
both launcher-installed on Windows); capt `app.db` in repo is demo-state;
tax two-DB pattern final form deferred to Phase 1A.

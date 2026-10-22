# CA Knowledge Hub — Architecture

**Status:** Phase 1A complete. This document grows with each phase.

## Layered design (spec §4)

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1 — UI shell (stack decision: see STACK_DECISION.md)│
│  dashboard · global search · modes · workspaces · modules │
│  pages discovered via module manifests (ui_entry_points) │
├─────────────────────────────────────────────────────────┤
│ Layer 2 — Application services (hub/hubcore/)            │
│  db.py (connections, integrity) · migrations.py          │
│  registry.py (module discovery/validation)               │
│  storage.py (StorageProvider + LocalFolderProvider)      │
│  export.py (JSON+CSV+dump+manifest)                      │
│  [1B] documents.py (ingestion) · [1C] search.py,         │
│  backup.py, knowledge.py, workspaces.py                  │
├─────────────────────────────────────────────────────────┤
│ Layer 3 — SQLite (+FTS5)                                 │
│  versioned schema (schema_migrations), single database   │
│  file; modules extend via extension_json or <mod>_ext    │
│  tables; FTS5 virtual tables doc_fts / record_fts        │
├─────────────────────────────────────────────────────────┤
│ Layer 4 — Modules (hub/modules/<name>/)                  │
│  module.json manifest · ui.py register_pages() · seed    │
│  data · tests. Discovered at startup; never edited in     │
│  core.                                                   │
├─────────────────────────────────────────────────────────┤
│ Layer 5 — Storage & distribution                         │
│  StorageProvider interface; LocalFolderProvider first    │
│  (manual download → local folder → Refresh Library).     │
│  No cloud-API dependency. Distribution: versioned ZIP +  │
│  run_windows.bat (winget Python, venv, waits-for-server). │
└─────────────────────────────────────────────────────────┘
```

## Key decisions (with dates)

- **2026-10-21 (1A):** Single SQLite database for all modules; the tax
  engine's knowledge/working-data split is preserved as a *namespaced*
  separation inside the one file OR a documented two-file exception —
  final call in Phase 1A review (deferred: taken in Phase 3 seeding).
  Cross-module links are `record_relations` rows (no-code link records).
- **2026-10-21 (1A):** Migration files are SQL with `-- UP --` /
  `-- DOWN --` sections; rollback is tested (drops are reversed).
- **2026-10-21 (1A):** `verification_status` is a CHECK-constrained enum:
  `verified | extracted_unverified | user_note | interpretation |
  superseded`. Every technical record carries `review_due_date`.
- **2026-10-21 (1A):** Extension mechanism — exactly one pattern:
  shared columns on `knowledge_records` + `extension_json` (validated
  against the module's `extension_schema`) + optional `<module>_ext`
  joined tables declared in the manifest.
- **2026-10-21 (Phase 2):** First migrated module proves the module
  pattern: `modules/audit/` is auto-discovered from its `module.json`
  (no core edits), keeps its own `audit_`-prefixed tables as authority,
  ports the source rule engine with identical semantics, and registers
  search stubs in `knowledge_records` for global FTS. Reference data
  (15 assertions, 11 cycles) is ported verbatim from source `db.py`;
  review-status → verification_status mapping is
  Verified→verified, Draft→user_note, Under review→extracted_unverified,
  Retired→superseded. Deliberate limitation carried over: no ISA/IFRS
  paragraph numbers (per source policy).
- **2026-10-21 (Phase 3):** The tax engine's knowledge/working-data
  split (deferred in Phase 1A) is resolved as a **namespaced table
  split in the single hub database** — all tables `tax_`-prefixed, no
  second SQLite file. The ported engine (`decision`/`calc`/`validate`/
  `loader`/`reconcile`/`export`) is verified by ported synthetic
  behavioural tests, not by re-asserting tax law. The source's
  `kb_fts` table is dropped; tax content is globally searchable via
  `knowledge_records` stubs (module='tax') like every other module.
- **2026-10-21 (Phase 4 — MVP complete):** First greenfield module
  (`modules/fr/`) proves modules can also be authored, not only
  migrated. Content policy: study aids at Bilal's level, all marked
  `extracted_unverified`, no paragraph numbers (test-enforced), and
  the suggester proposes candidates only — the module never asserts a
  standard applies. Cross-module links (`fr_treatment_audit_risk`)
  use soft references validated at seed time, since module seeding
  order is not guaranteed.
- **2026-10-21 (Phase 5):** The reconciliation engine ports CA
  Copilot's `workbench.py` verbatim (pure functions, no hub
  dependencies) and adds a hub-native persistence layer (`store.py`).
  Rule: the engine never auto-resolves — ambiguous matches are
  reported, differences are never auto-classified as errors, and
  resolutions require a human-written note. Original imports are kept
  verbatim so any finding can be traced back to its source row.
- **2026-10-21 (Phase 6):** The data-analysis module is pure functions
  + openpyxl templates with a tiny persistence table for recipes.
  Safety rule: calculated-column formulas go through an AST whitelist
  (arithmetic, abs/min/max/round, column names) — `eval()` is never
  used, and formula injection is a test case. Cleaning is fully
  logged; variance thresholds are explicit parameters, never
  hard-coded materiality.
- **2026-10-21 (Phase 7):** The case-engine migration ports five pure
  engine modules verbatim and adds a thin DB adapter (`casedb.py`).
  Rules: trigger rules never fire on missing facts; the recommendation
  builder only assembles the student's own inputs (options, facts,
  assumptions, KPIs) — it never writes conclusions. Student tables are
  seed-protected by test. The 2025 syllabus mapping is honestly marked
  provisional wherever the 2021 predecessor is the actual source.
- **2026-10-21 (Phase 8):** The FS-analysis engine is Decimal
  throughout; every ratio declares its required inputs and is skipped
  (with a reason) when they are absent — the module would rather show
  fewer ratios than invent one. Red flags evaluate only on computed
  ratios and always link an observation to a why-it-matters note and
  an investigate-next step, per the spec's "prompts, never proof".
- **2026-10-21 (Phase 9):** Workpaper templates are deliberately
  generic and disclaimed — the module helps Bilal *practise* working-
  paper discipline (planning → evidence → review → completion), not
  replicate a firm methodology. Exceptions can only be cleared with a
  written resolution, mirroring the recon module's never-auto-resolve
  rule.
- **2026-10-21 (Phase 10):** Finance functions return assumptions
  alongside answers by construction — no silent defaults. NPV shows
  period-by-period workings; IRR returns its bisection check value;
  sensitivity always anchors on the base case so a what-if can never
  be mistaken for a recommendation.
- **2026-10-21 (Phase 11):** The complaw module encodes the
  no-invention policy structurally: seeded provisions physically
  cannot carry a section number (NULL) and the seed test asserts it.
  Tracing a provision is an explicit, sourced act — the module never
  pre-fills statute content.
- **2026-10-21 (Phase 12):** Research conclusions are append-only by
  schema (UNIQUE(issue_id, version_no)) — the module cannot silently
  rewrite history. Comparisons force an explicit agree/conflict/
  unclear verdict rather than letting contradictory sources sit
  unexamined.
- **2026-10-21 (Phase 14):** Study Mode migrates the CAPT app's
  *algorithm* (SM-2, verbatim semantics) and *content* (Bilal's
  private pack) but not its UI — the hub's module-page contract
  replaces it. The planner is intentionally simpler than CAPT's
  (no mastery-model dependency) but keeps the two properties that
  matter: weak-first ordering and determinism. The content pack is
  data, not code: it ships inside Bilal's personal ZIP only.

## Data flow: documents → knowledge

1. User downloads files from TeraBox (or any drive) into a local folder.
2. `LocalFolderProvider.scan()` lists them; `fetch()` copies to the inbox.
3. Refresh Library (1B) extracts text → `documents` + `doc_chunks` →
   `doc_fts`; hashes detect new/changed/unchanged/missing.
4. Curated records live in `knowledge_records` (+ `record_fts`),
   linked to `sources`, versioned in `revision_history`, related via
   `record_relations`, scoped by `workspaces`.

## Performance targets (initial, spec §8)

5,000 documents indexed · global search p95 < 1s · cold start < 15s ·
workspace switch < 1s · fully offline. Verified in Phase 13.

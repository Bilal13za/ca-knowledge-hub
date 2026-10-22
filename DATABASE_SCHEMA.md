# CA Knowledge Hub — Database Schema

**Schema version:** 1 (`hub/hubcore/migrations/001_initial.sql`)
**Status:** Phase 1A complete.

## Conventions

- All tables use `TEXT` ISO-8601 timestamps (`datetime('now')` UTC).
- JSON columns (`*_json`) store structured data; never queried with
  complex JSON path expressions in hot paths.
- `verification_status` enum everywhere technical:
  `verified | extracted_unverified | user_note | interpretation | superseded`.
- Foreign keys enforced (`PRAGMA foreign_keys = ON`); WAL journal mode.

## Tables

| Table | Purpose | Key columns |
|---|---|---|
| `schema_migrations` | version tracking | `version` PK, `description`, `applied_at` |
| `modules` | installed module registry | `name` PK, `title`, `version`, `enabled`, `manifest_json` |
| `documents` | ingested file catalogue | `path` UNIQUE, `file_hash`, `file_size`, `file_type`, `status` (`indexed\|failed\|unsupported\|ocr_needed`), `meta_json` |
| `doc_chunks` | page/sheet-level text chunks | `document_id` FK, `chunk_index`, `page_no`, `sheet_name`, `text` |
| `doc_fts` | FTS5(porter) over chunks | `text`, `document_id` + `chunk_id` (UNINDEXED) |
| `sources` | source register | `code` UNIQUE, `title`, `kind`, `jurisdiction`, `publisher`, `url`, `accessed_at` |
| `knowledge_records` | core curated records | `module`, `topic`, `subtopic`, `title`, `description`, `keywords`, `content`, `source_id` FK, `source_page`, `jurisdiction`, `effective_date`, `applicable_period`, `verification_status`, `last_reviewed`, **`review_due_date`**, `extension_json` |
| `record_fts` | FTS5(porter) over records | `title, description, keywords, content`, `record_id` + `module` (UNINDEXED) |
| `record_relations` | cross-module links (§4B) | `source_record_id`, `target_record_id`, `rel_type`, `note`; UNIQUE(source,target,rel_type) |
| `tags` / `record_tags` | tagging | `tags.name` UNIQUE |
| `rules` | generic rules (module-specialised tables preferred) | `module`, `rule_code`, `conditions_json`, `action_json`, `verification_status`, `version`, `superseded_by` self-FK; UNIQUE(module,rule_code,version) |
| `procedures` | generic procedures | `module`, `code` UNIQUE per module, `procedure_type`, `verification_status` |
| `calculations` | calculation definitions | `module`, `code` UNIQUE per module, `formula_text`, `parameters_json`, `verification_status` |
| `calculation_runs` | reproducible run log | `calculation_id`, `inputs_json`, `outputs_json`, `workspace` |
| `verification_records` | who verified what, how | `entity_type`, `entity_id`, `verified_by`, `method`, `result`, `notes` |
| `revision_history` | no-silent-overwrite log | `entity_type`, `entity_id`, `version`, previous/revised JSON, `reason`, `source_of_change`, `effective_date` |
| `bookmarks` | user bookmarks | `record_id` FK, `note` |
| `study_progress` | study tracking | `module`, `topic`, `record_id`, `status`, `score`, `attempts` |
| `workspaces` | named module sets (§4B) | `name` UNIQUE, `module_list_json` |
| `settings` | app settings | `key` PK, `value_json` |

### Module: audit (`hub/modules/audit/schema.sql`, applied by `seed.py`)

The audit module uses heavily-queried joined tables (pattern §6.3),
declared in the module manifest's `extension_tables`. Every entity
carries the source library's `review_status` (`Verified | Draft |
Under review | Retired`); the engine only plans/searches Verified
items. The module's authority is its own tables; `knowledge_records`
holds search stubs for global FTS (regenerated on each seed).

| Table | Purpose | Key columns |
|---|---|---|
| `audit_assertions` | 15 assertions (source of truth) | `id` PK, `category`, `name`, `description` |
| `audit_cycles` | 11 business cycles | `id` PK, `name`, `description` |
| `audit_factors` | 29 business factors | `id` PK, `name`, `description`, `cycle_id` FK, `risk_category`, `conditions_relevant`, `warning_signs` |
| `audit_risks` | 29 risks | `id` PK, `title`, `description`, `causes`, `potential_consequences`, `cycle_id` FK, `inherent_risk_notes` |
| `audit_controls` | 58 controls | `id` PK, `description`, `objective`, `preventive_detective`, `manual_automated`, `frequency`, `responsible_role`, `evidence_of_operation`, `limitations` |
| `audit_procedures` | 99 procedures | `id` PK, `title`, `objective`, `steps`, `procedure_type`, `test_type`, `population`, `sampling_notes`, `expected_result`, `exception_criteria`, `follow_up` |
| `audit_evidence` | 89 evidence items | `id` PK, `name`, `description`, `source`, `reliability_notes`, `limitations`, `expected_characteristics`, `contradictory_evidence` |
| `audit_rules` | 30 editable rules | `id`, `name`, `definition` JSON (when/then/all/any/exclude), `rationale`, `version`, `priority`, `status` (`Active\|Deprecated\|Test`), UNIQUE(id,version) |
| `audit_builds` | seeded-at traceability | `id` PK, `seeded_at`, `source_app`, `rule_count` |
| `audit_factor_risk` | factor→risk links | `factor_id`,`risk_id` FKs, `trigger_condition`, `applicability`, `explanation` |
| `audit_risk_assertion` | risk→assertion links | `risk_id`,`assertion_id` FKs, `why_relevant`, `conditions` |
| `audit_risk_control` | risk→control links | `risk_id`,`control_id` FKs, `explanation` |
| `audit_risk_procedure` | risk→procedure links | `risk_id`,`procedure_id` FKs, `reason` |
| `audit_procedure_assertion` | procedure→assertion links | `procedure_id`,`assertion_id` FKs |
| `audit_procedure_evidence` | procedure→evidence links | `procedure_id`,`evidence_id` FKs, `notes` |

Seed counts verified by `tests/test_audit.py::test_seed_counts_match_source`.

Seed counts verified by `tests/test_tax.py::test_seed_counts_match_source`
(real-data) and synthetic TEST-content behavioural tests.

### Module: tax (`hub/modules/tax/schema.sql`, applied by `seed.py`)

The tax module uses heavily-queried joined tables (pattern §6.3),
declared in the manifest's `extension_tables`. Knowledge tables and
working-data tables are namespaced apart — the source engine's strict
two-DB discipline, preserved as a documented namespaced split in the
one hub database (final call on the deferred Phase 1A decision).

| Table | Purpose | Key columns |
|---|---|---|
| `tax_sources` | source register | `code` UNIQUE, `title`, `source_type`, `jurisdiction`, `verified_date` |
| `tax_legislation` | provisions (versioned rows) | `code` UNIQUE, `provision`, `subsection`, `effective_from/to`, `tax_year`, `review_status` |
| `tax_rules` | rule library (versioned) | `code`, `version`, `tax_category`, `jurisdiction`, `applicability_conditions` JSON, `decision_logic` JSON, `verification_status`; UNIQUE(code,version) |
| `tax_risks` | risk library | `code` UNIQUE, `title`, `tax_category`, `review_status` |
| `tax_evidence` | evidence library | `code` UNIQUE, `name`, `review_status` |
| `tax_procedures` | verification procedures | `code` UNIQUE, `category`, `review_status` |
| `tax_calc_tables` | rates/slabs/thresholds (versioned) | `code`, `version`, `kind` (`slab\|flat_rate\|percentage\|fixed_amount\|threshold\|rate_schedule`), `params` JSON, `verification_status`; UNIQUE(code,version) |
| `tax_scenarios` | predefined scenarios | `code` UNIQUE, `category`, `trigger_facts` JSON, `expected_chain` JSON |
| `tax_rule_legislation` / `tax_rule_risks` / `tax_rule_evidence` / `tax_rule_procedures` / `tax_rule_calcs` / `tax_risk_evidence` / `tax_risk_procedures` | link tables | FK pairs |
| `tax_profiles` | taxpayer profiles (working data) | `profile_code` UNIQUE, `taxpayer_type`, `tax_year`, `province` |
| `tax_assessments` / `tax_assessment_steps` | saved 14-step analyses | `profile_id` FK, `facts` JSON; steps 1..14 with `confidence` |
| `tax_evidence_tracker` / `tax_reconciliations` / `tax_calculation_runs` / `tax_export_log` | working data | per source engine |

### Module: fr (`hub/modules/fr/schema.sql`, applied by `seed.py`)

Greenfield study library (no staged source data). All content is
authored study material at CAF level, `extracted_unverified`
throughout; no paragraph numbers anywhere (policy, test-enforced).

| Table | Purpose | Key columns |
|---|---|---|
| `fr_standards` | IAS/IFRS register | `id` PK (e.g. 'IFRS 15'), `title`, `summary`, `effective_from` |
| `fr_treatments` | accounting treatments | `id` PK, `title`, `transaction_analysis`, `recognition`, `initial_measurement`, `subsequent_measurement`, `journals_json`, `presentation`, `disclosure`, `statement_impact`, `common_mistakes_json` |
| `fr_examples` | worked examples | `id` PK, `treatment_id` FK, `facts`, `solution`, `journals_json` |
| `fr_treatment_standard` | treatment↔standard links | `treatment_id`, `standard_id` FKs |
| `fr_treatment_audit_risk` | treatment↔audit-risk links | `treatment_id` FK, `audit_risk_id` (no hard FK — validated at seed) |

### Module: recon (`hub/modules/recon/schema.sql`, applied by `seed.py`)

No seed data — reconciliation data is Bilal's own working data,
imported per run and preserved verbatim.

| Table | Purpose | Key columns |
|---|---|---|
| `recon_runs` | reconciliation runs | `name`, `kind` (bank/supplier/customer/gl/inventory/payroll/tax/other), `label_a/b`, `mapping_json`, `summary_json`, `status` |
| `recon_datasets` | imported datasets (original data preserved) | `run_id` FK, `side` (a/b), `filename`, `columns_json`, `rows_json`, `row_count` |
| `recon_findings` | findings with manual resolutions | `run_id` FK, `kind`, `severity`, `message`, `row_ref`, `details_json`, `status` (open/resolved/ignored), `resolution_note` |

### Module: xlanalysis (`hub/modules/xlanalysis/schema.sql`)

| Table | Purpose | Key columns |
|---|---|---|
| `xla_runs` | analysis runs with reproducible recipes | `name`, `operation` (clean/variance/summary/calculated/exceptions), `recipe_json`, `summary_json`, `output_path` |

### Module: biacase (`hub/modules/biacase/schema.sql`)

26 `case_`-prefixed tables ported from the case-engine schema (source
FTS tables/triggers dropped; hub uses knowledge_records stubs).
Student tables (`case_student_attempts`, `case_mistake_log`,
`case_flashcard_progress`) are never written by the seeder.

Key tables: `case_frameworks` (49) + `case_framework_steps` (60),
`case_trigger_rules` (30) + `case_rule_framework_mappings` (78),
`case_formulas` (44), `case_patterns` (16) + `case_facts` (97),
`case_concepts` (28), `case_flashcards` (210), `case_mindmaps` (27),
`case_practice_questions` (24) + outlines + rubrics,
`case_papers`/`case_topics`/`case_learning_outcomes` (4/12/52),
`case_sources` (3).

### Module: fsanalysis (`hub/modules/fsanalysis/schema.sql`)

| Table | Purpose | Key columns |
|---|---|---|
| `fs_runs` | saved analyses (inputs + results, reproducible) | `name`, `kind` (ratios/trends/common_size/working_capital), `inputs_json`, `result_json` |

### Module: workpapers (`hub/modules/workpapers/schema.sql`)

| Table | Purpose | Key columns |
|---|---|---|
| `wp_templates` | generic template library (9) | `id` PK, `category`, `structure_json`, `disclaimer` |
| `wp_papers` | working-paper instances | `engagement`, `template_id` FK, `status` (draft/in_progress/in_review/completed), `data_json` |
| `wp_exceptions` | exception tracking | `paper_id` FK, `description`, `status` (open/in_follow_up/cleared), `resolution` |
| `wp_evidence` | evidence register | `paper_id` FK, `ref`, `description`, `reliability` |

### Module: corpfn (`hub/modules/corpfn/schema.sql`)

| Table | Purpose | Key columns |
|---|---|---|
| `cf_runs` | saved finance runs (inputs + results) | `name`, `kind` (npv/irr/payback/capm/wacc/gordon/sensitivity), `inputs_json`, `result_json` |

### Module: complaw (`hub/modules/complaw/schema.sql`)

| Table | Purpose | Key columns |
|---|---|---|
| `law_provisions` | source-traced provision notes | `act`, `section_no` (NULL until traced), `verification_status`, `source_ref` |
| `law_companies` | company profiles | `name`, `cuin`, `company_type`, `incorporation_date` |
| `law_deadlines` | compliance calendar | `company_id` FK, `obligation`, `due_date` (user-entered ISO), `done`, `done_date` |
| `law_filings` | filing register | `company_id` FK, `form_name`, `status` (pending/filed/acknowledged), `reference_no` |

### Module: research (`hub/modules/research/schema.sql`)

| Table | Purpose | Key columns |
|---|---|---|
| `rs_issues` | research issues | `title`, `question`, `status` (open/in_progress/concluded) |
| `rs_sources` | source library | `issue_id` FK, `source_type`, `citation`, `reliability` |
| `rs_findings` | per-source findings | `issue_id` FK, `source_id` FK, `point`, `relevance` |
| `rs_comparisons` | source comparisons | `issue_id` FK, `aspect`, `agreement` (agree/conflict/unclear) |
| `rs_conclusions` | append-only conclusions | `issue_id` FK, `version_no` UNIQUE per issue, `conclusion_text`, `basis` |

### Module: study (`hub/modules/study/schema.sql`)

| Table | Purpose | Key columns |
|---|---|---|
| `study_decks` | flashcard/question decks (15) | `id` TEXT PK (`capttax-chNN`), `name`, `source` |
| `study_cards` | flashcards | `deck_id` FK, `front`, `back`, `chapter_ref`, `page_ref` |
| `study_reviews` | SM-2 state, one row per card | `card_id` PK, `ease`, `interval_days`, `reps`, `lapses`, `next_due` |
| `study_questions` | question bank (131) | `id` TEXT PK, `deck_id` FK, `statement`, `solution`, `has_solution` |
| `study_attempts` | self-marked attempts | `question_id` FK, `correct` (0/1), `attempted_at` |
| `study_plans` | revision plans | `name`, `exam_date`, `hours_per_day`, `study_days` |
| `study_plan_items` | day-by-day activities | `plan_id` FK, `activity_date`, `activity_type`, `title`, `minutes`, `done` |

## Extension pattern (§6 — the one specified mechanism)

1. Shared fields → columns on `knowledge_records`.
2. Simple module fields → `extension_json`, validated against the
   module's `extension_schema` (declared in `module.json`).
3. Heavily-queried module fields → joined `<module>_ext` tables with
   `record_id` FK, declared in the manifest (`extension_tables`).
4. No third pattern without a documented reason in ARCHITECTURE.md.

## Migration history

- **001_initial** (2026-10-21): all tables above + FTS5 virtual tables.
  Rollback tested: DOWN drops all Hub tables (verified by
  `test_rollback_and_remigrate`).

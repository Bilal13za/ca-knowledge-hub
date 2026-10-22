# PROJECT: LIFELONG CA KNOWLEDGE AND PROFESSIONAL PRACTICE SYSTEM

## Revision 2 — 2026-10-21

*Supersedes the v1 master prompt supplied by Bilal on 2026-10-21 (filed at
`~/workspace/ca-knowledge-hub/master-prompt.md`). The main idea is unchanged;
this revision folds in review findings and Bilal's workspaces design.*

### REVISION NOTES (v1 → v2)

1. Added **Phase 0: Reuse audit** — inventory the five existing applications,
   decide migrate / wrap / retire for each, and seed Phases 2, 3, 7 from their
   data instead of rebuilding finished work.
2. Split **Phase 1 into 1A / 1B / 1C**, each with its own acceptance gate.
3. Defined the **MVP as Phases 0–4**, mapped to Bilal's current CAF papers;
   Phases 5–12 scheduled after the February 2027 exams. Added indicative
   effort sizing per phase.
4. New **Principle G: Reuse before rebuild**.
5. **UI stack decision** (e.g., Streamlit / Tkinter / PyQt) is now an explicit
   Phase 1A deliverable with written rationale; the module UI-plugin pattern
   is specified (entry-point functions declared in the module manifest).
6. **Knowledge-model extension mechanism** specified: exactly one documented
   pattern (base table + validated extension JSON, with optional joined
   extension tables following a naming convention).
7. **Storage-provider adapter interface** specified; the initial implementation
   remains the manual local-folder workflow — no dependency on undocumented
   TeraBox endpoints or a TeraBox API.
8. **Export format** specified: JSON per module + CSV where tabular + full
   SQLite dump + manifest file.
9. **Distribution** specified: versioned ZIP + Windows launcher
   (`run_windows.bat`), consistent with the existing applications.
10. New section **4B: Workspaces (on-demand module composition)** — Bilal's
    design: selecting "Audit" loads audit resources; "Audit + Tax" loads both
    and surfaces cross-module implication links; relationships are no-code link
    records; workspaces never auto-generate professional conclusions.
11. **Review-due (staleness) tracking** moved into the core schema
    (`review_due_date` on rules/records), not deferred to Phase 12.
12. **Measurable performance targets** added (initial values, adjustable).
13. **Backup acceptance** now requires an automated restore-verification test.
14. **Acceptance-test checklist template** required in TESTING_GUIDE.md.
15. Clarified "Excel automation" = Python-generated workbooks/templates
    (e.g., openpyxl); never VBA/macros; never execute embedded macros.

---

### 1. YOUR ROLE

Act as a senior software architect, Python developer, database engineer,
reuse analyst, quality assurance specialist, and professional
knowledge-system designer.

Your task is to build a reliable, expandable, local-first knowledge and
analysis application for a Chartered Accountancy student in Pakistan.

This is not merely an exam-preparation application. It must be designed to
support the user's progression through:

1. CA studies.
2. Articleship and practical training.
3. Qualification as a Chartered Accountant.
4. Professional practice and continuing development.
5. Potential future work in audit, taxation, financial reporting, finance,
   internal audit, advisory, management, and entrepreneurship.

The application must be useful at every stage without requiring a complete
rebuild.

Build the software foundation once. Allow the user to add, update, extend,
and replace knowledge modules independently.

The application should remain useful even when the user's career direction
changes.

---

### 2. THE CORE VISION

Build one integrated application called:

**CA Knowledge Hub**

The system must combine:

- A searchable document library.
- A structured technical knowledge database.
- Accounting and financial reporting rules.
- Audit risk and evidence relationships.
- Tax legislation and calculation rules.
- Reconciliation and data analysis tools.
- Business case analysis.
- Excel automation resources.
- Professional checklists and templates.
- Technical research and source verification.
- Study and revision features.
- Professional workflow support.

Do not create 12 disconnected applications.

Build one common platform with specialised modules that share the
underlying infrastructure.

The user should be able to add new modules in the future without
redesigning the application.

---

### 3. NON-NEGOTIABLE DESIGN PRINCIPLES

**A. Build once, extend indefinitely**

The architecture must support future expansion without requiring a complete
rebuild. New modules must be installable or addable through documented
procedures. Adding a new library must not require rewriting the core search
engine, database, document manager, interface, backup system, or source
register. Use modular components and documented interfaces. Avoid tightly
coupling specialised accounting or tax logic to the application's main
interface.

**B. Keep the system free**

Assume development is performed without a development fee. Prefer free and
open-source software. Do not introduce mandatory paid subscriptions, paid
database hosting, AI API usage, commercial cloud integrations, or licensed
software that is not necessary for the core functionality. Clearly disclose
optional expenses before introducing a feature that could create recurring
costs. Verify the licences and permitted uses of third-party dependencies.

**C. Local-first architecture**

The system must operate on Windows and remain useful offline. Use a local
database for structured knowledge and search indexes. The application must
not require an internet connection for its core search, browsing,
calculations, and data-processing functions. Online access may be needed to
download documents, check current sources, or access cloud-only files.

**D. No AI dependency**

The core system must not depend on generative AI. Use conventional
programming, structured records, search, explicit rules, calculations, and
user-defined relationships. Do not make AI necessary for retrieving,
calculating, validating, or displaying stored knowledge. The architecture
may allow an optional AI integration in the future, but the core system must
remain fully functional without it.

**E. Source traceability**

Every technical knowledge record must be traceable to its source wherever
applicable. Never invent legal provisions, tax rates, accounting
requirements, auditing requirements, source quotations, page references,
effective dates, or verification status. Distinguish between imported
documents, extracted statements, user-created notes, verified technical
rules, and professional interpretations.

**F. User control**

The user must remain in control of adding and removing material, editing
knowledge records, verifying technical rules, selecting modules, backing up
data, restoring previous versions, changing cloud storage providers, and
exporting and migrating the system. Do not make important data dependent on
a proprietary, inaccessible format.

**G. Reuse before rebuild**

Before writing new code, inventory existing proven components — the user's
five existing applications and their data (see Phase 0). Migrate or wrap
working code and seed data wherever it satisfies this architecture; rebuild
only with a documented reason. Never silently rebuild a working, tested
component from zero.

---
### 4. PERMANENT TECHNICAL ARCHITECTURE

Design the application in clearly separated layers.

**Layer 1: User interface**

A lightweight, desktop-friendly interface providing: dashboard, global
search, module navigation, Study Mode, Practice Mode, Professional Mode,
document library, knowledge-record viewer, Refresh Library, search filters,
processing history, technical source viewer, settings, export and backup
controls, module management, and workspace management (see 4B).

The interface must remain usable on a Windows laptop with 8 GB RAM. Avoid
unnecessary resource-heavy features.

*Stack decision (Phase 1A deliverable):* the UI stack — e.g., Streamlit,
Tkinter, PyQt, or another free option — must be chosen in Phase 1A with a
written rationale covering: RAM footprint on the user's laptop, offline
operation, packaging as a Windows desktop app, and how modules plug UI in.
Do not default to a stack without this rationale.

*Module UI-plugin pattern (one specified mechanism):* each module's manifest
declares UI entry points — named functions returning page/panel definitions
(e.g., `register_pages()`). The core discovers these at startup and renders
them inside the shell (navigation, search, mode layouts). Adding a module's
UI must not require editing core UI code. Document the entry-point contract
in MODULE_DEVELOPMENT_GUIDE.md.

**Layer 2: Application services**

Create reusable services for: document ingestion, text extraction, search,
knowledge-record management, source tracking, calculations, validation,
reconciliation, reporting, export, backup and restoration, database
migration, module registration, and workspace management. These services
must be independent of individual professional modules wherever practical.

**Layer 3: Structured database**

Use SQLite for local structured information. Design a documented, versioned
schema (`schema_version` table; migrations preserve existing data)
supporting: documents, knowledge records, sources, modules, topics, tags,
relationships, rules, procedures, calculations, verification records,
revision history, user bookmarks, study progress, workspaces, application
settings.

Use SQLite FTS5 for local full-text search where supported. Keep the
database schema extensible. Do not create a separate database for every
module unless there is a documented technical reason.

Every rule and technical knowledge record carries `review_due_date` in the
core schema (see section 6). Staleness tracking is a core concern from
Phase 1, not a later addition.

**Layer 4: Module system**

Create a module registry that allows the application to discover and load
specialised libraries. Each module manifest must define its: name,
description, version, data requirements, search categories, UI entry points,
calculation functions (if applicable), validation rules, source
requirements, extension-schema declaration (see section 6), dependencies,
tests, and upgrade/migration procedures.

Adding a module must not break existing modules. Document the process for
creating a new module in MODULE_DEVELOPMENT_GUIDE.md, including a worked
"no-code module" example (documents + records + checklists only, no Python).

**Layer 5: Storage and file access**

Keep the application independent of any single cloud-storage provider. The
initial cloud archive will be TeraBox, but the application must not depend
on undocumented TeraBox endpoints or require a TeraBox API.

*Storage-provider adapter interface (one specified mechanism):* define a
`StorageProvider` interface (configure location; scan/import new files into
the local staging folder). The initial implementation is
`LocalFolderProvider`: the user downloads documents from TeraBox, places
them in a configured local folder, and the application scans that folder on
Refresh Library. Switching cloud providers later means implementing the
interface — a configuration change, not an architectural change. Do not
assume that TeraBox offers a synchronised local folder.

*Distribution:* ship as a versioned ZIP with a Windows launcher
(`run_windows.bat`), consistent with the user's existing applications,
until a better mechanism is approved. The launcher must install or verify
its Python dependencies without manual steps.

*Export format (one specified mechanism):* JSON per module (records, rules,
relationships), CSV where tabular, a full SQLite dump, and a `manifest.json`
recording schema version, module versions, export date, and record counts.
All exports must be human-readable and re-importable.

---

### 4B. WORKSPACES (ON-DEMAND MODULE COMPOSITION)

A workspace is a named, savable set of active modules for the task at hand.
Examples: "Audit" (audit resources only), "Audit + Tax" (both domains, with
their interactions), "FAR + Tax" (financial reporting with tax
implications).

Requirements:

1. The user creates, renames, saves, and deletes workspaces; the last-used
   workspace is restored on startup.
2. Global search, browsing, calculations, and document scope filter to the
   active workspace by default. Module filter chips allow narrowing further
   within a search.
3. Modules load lazily: only active modules consume memory. Switching
   workspaces must re-scope search in under one second on the user's laptop
   (initial target; see performance targets in Phase 1C).
4. Cross-module relationships are first-class, no-code records: (source
   module, source record, target module, target record, relationship type,
   note). Relationship types include `has-tax-implication`,
   `tested-by`, `discloses`, `reconciles-with`, and user-defined types.
   Creating a relationship must take under a minute and require no Python.
5. When a viewed record has relationships into modules outside the active
   workspace, the interface offers one-tap expansion ("This has tax
   implications — load the Tax module into this workspace?").
6. Combined outputs: checklists, workpapers, and exports may pull items from
   all active modules into a single document, each item labeled with its
   source module.
7. A workspace must never auto-generate a professional conclusion from
   combined modules. It presents each domain's material and leaves analysis
   and conclusions to the user (consistent with the honesty requirements in
   section 7, Modes B and C).
8. Cross-module links must resolve cleanly or report clearly when a target
   module is not installed; a missing target must never break the source
   module.

Workspaces operate within the three modes (section 7): for example, Study
Mode combined with the workspace "CAF-2 Tax + CAF-5 FAR" presents deferred
tax (IAS 12) — tax base vs carrying amount, the calculation, and the
disclosure — in one view.

---
### 5. DOCUMENT MANAGEMENT AND REFRESH LIBRARY

This is a critical foundation and must be completed (Phase 1B) before
specialised knowledge libraries are developed.

Initially support: PDF, TXT, Markdown, DOCX, CSV, XLSX. Design the ingestion
system so additional formats can be added later.

**Refresh Library requirements** — the function must:

1. Scan configured folders and permitted subfolders.
2. Detect new documents.
3. Detect modified documents.
4. Identify unchanged documents.
5. Detect missing source files.
6. Extract supported text and metadata.
7. Update search indexes.
8. Preserve document identity where possible.
9. Record processing results.
10. Report failures.
11. Avoid unnecessary duplicate records.
12. Preserve existing valid content when an update fails.
13. Record the refresh date and time.

Use file hashes where appropriate. Do not automatically delete knowledge
records when a source file disappears — mark missing sources and allow the
user to decide what to do. For PDFs, retain page-level references where
available. For scanned documents, report that OCR is needed when text
extraction is inadequate. For spreadsheets, preserve sheet names, column
headers, and relevant tabular structures. Never execute imported macros or
embedded programs.

Provide a processing report showing: new files, updated files, unchanged
files, missing files, successfully indexed files, failed files, unsupported
files, and documents requiring OCR.

---

### 6. THE KNOWLEDGE MODEL

Every specialised library must store structured knowledge rather than
relying entirely on unorganised documents.

A general knowledge record supports:

- Unique ID.
- Module.
- Topic.
- Subtopic.
- Title.
- Description.
- Keywords.
- Content.
- Related records (cross-module relationships per section 4B).
- Source document.
- Source page or section.
- Jurisdiction, if applicable.
- Effective date, if applicable.
- Applicable period, if applicable.
- Verification status: one of `verified`, `extracted_unverified`,
  `user_note`, `interpretation`, `superseded` — never ambiguous, always
  visible in the interface.
- Last reviewed date.
- **Review due date** (core staleness tracking; the interface surfaces
  records due for review).
- Revision history.

Do not force every module into an identical data structure when their
requirements differ. Provide reusable shared fields while allowing
specialised extensions — through exactly one documented mechanism:

*Extension mechanism (one specified pattern):*

- The `knowledge_records` base table holds all shared fields above.
- Simple module-specific fields go in `extension_json` (JSON), validated
  against the module's declared `extension_schema` at write time.
- Heavily-queried module fields use joined extension tables named
  `<module>_ext` with a `record_id` foreign key, following the documented
  pattern; the module manifest declares which approach it uses and why.
- Do not invent a third extension pattern without documenting the reason in
  ARCHITECTURE.md.

For example, an audit record may extend with assertions and procedures,
while a tax record extends with tax year and calculation method.

---
### 7. THREE OPERATING MODES

Implement three modes within the same application. Modes organise and
present information differently without silently changing technical
requirements or calculations. Workspaces (4B) operate within modes.

**MODE A: STUDY MODE** — examination preparation and learning: ICAP
syllabus mapping (user-updatable when syllabuses change), topic notes,
concept summaries, worked examples, practice questions, answer frameworks,
revision checklists, weak-topic tracking, personal notes, mistake logs,
progress tracking, source references. Clearly distinguish examinable
syllabus content from supplementary material; never assume stored
professional material is examinable.

**MODE B: PRACTICE MODE** — preparation for practical accounting, audit,
tax, finance, and analytical tasks: risk identification, procedure
selection, evidence checklists, reconciliation workflows, tax calculations,
journal-entry analysis, financial data processing, internal control
assessment, business process documentation, exception investigation,
workpaper preparation templates. All outputs must be reviewable and
editable. Do not automatically represent a preliminary analysis as a
completed professional conclusion.

**MODE C: PROFESSIONAL MODE** — advanced professional work after
qualification: technical research, financial reporting issue analysis, tax
compliance research, audit planning references, risk and control registers,
reusable reporting templates, financial analysis, management reporting,
valuation models, compliance calendars, professional checklists,
quality-control reviews. Explicit source verification and revision tracking
are mandatory. Never imply that stored rules are current, or that outputs
replace professional judgement, supervision, engagement requirements, or
applicable standards. Do not automatically store confidential client
information in the user's personal cloud archive.

---

### 8. DEVELOPMENT ROADMAP

Build in the following sequence. Complete and validate each phase before
proceeding. Do not attempt to populate every library simultaneously.
Indicative effort sizing (S/M/L) is given per phase for planning; it is an
estimate, not a commitment.

**MVP definition:** Phases 0–4 constitute the minimum useful product,
mapped to Bilal's current CAF papers. Phases 5–12 are scheduled after the
February 2027 examinations unless Bilal explicitly reorders them.

**PHASE 0: REUSE AUDIT (S)**

Inventory the five existing applications and their data:

- CA Copilot Local (`~/workspace/ca-copilot`): document library, FTS
  search, ingestion, backup/restore, revision tracker.
- Audit Risk and Evidence Library (`~/workspace/audit-risk-library`):
  29 scenarios / 29 risks / 99 procedures / 89 evidence items / 58
  controls / 30 rules.
- Pakistan Tax Risk, Rules and Evidence Engine (`~/workspace/tax-engine`):
  63 rules (37 verified), 26 calc tables, 35 risks, 28 evidence types,
  28 scenarios, 38 sources.
- ICAP Business Case Analysis and Decision Engine
  (`~/workspace/icap-case-engine`): 585 seed rows, 44 calculations,
  30 trigger rules, 49 frameworks, 16 case patterns, 24 practice questions.
- CAPT Taxation Exam Preparation System (`~/workspace/capt-tax`): 14-chapter
  content pack (287 pages), 131 practice questions, flashcards, mind maps.

For each application record: schema, seed-data volumes, test suite status,
launcher mechanism. Then decide, with written reasons: **MIGRATE**
(import schema/data into the Hub), **WRAP** (run behind the module
registry as-is), or **RETIRE** (functionality superseded). Stage migrated
seed datasets for Phases 2, 3, and 7.

*Acceptance:* every existing application has a recorded decision with
reasons; no working, tested component is rebuilt without a documented
reason. Write no new application code in Phase 0.
Deliverable: REUSE_AUDIT.md (added to the documentation set in section 13).

**PHASE 1A: DATABASE, SCHEMA, MODULE REGISTRY (M)**

Versioned SQLite schema covering all core entities in section 4 (including
`review_due_date`, verification status enum, workspaces, relationships);
FTS5 search; migration framework with rollback-tested migrations; module
registry + manifest specification (including UI entry points and
extension-schema declarations); storage-provider interface;
export-format implementation; UI stack decision with written rationale
(see Layer 1). Automated tests for schema, migrations, registry, and
manifest validation.

*Acceptance:* migrations apply cleanly on a fresh and a pre-seeded DB;
registry discovers a sample module manifest; stack rationale is recorded.

**PHASE 1B: DOCUMENT INGESTION + REFRESH LIBRARY (L)**

All 13 Refresh Library requirements from section 5; six initial formats;
processing report; OCR-needed detection; macro-safety (never execute).
Tests: new / changed / unchanged / duplicate / missing / unsupported /
unreadable files; failed update preserves existing content.

*Acceptance:* the 13 requirements pass against a synthetic corpus covering
all file states; processing report is accurate.

**PHASE 1C: UI SHELL, SEARCH, BACKUP (M)**

Dashboard; global search with module filter chips; three mode skeletons;
workspace create/switch (section 4B); knowledge-record CRUD; source viewer;
processing history; export (section 4 formats); backup and restoration.

*Backup acceptance (strengthened):* backup, then automated restore into a
temporary database, then `PRAGMA integrity_check`, then record-count
comparison — all passing in the test suite. Document backup encryption
limitations honestly (see section 11).

*Performance targets (initial, adjustable):* 5,000 documents indexed;
global search p95 under 1 second on the user's laptop; cold start under
15 seconds; workspace switching re-scopes search in under 1 second; all
core functions fully offline.

*Acceptance:* the user can import documents, refresh the library, search
extracted content, view source references, create and edit knowledge
records, manage workspaces, export records, back up and verifiably restore
the database, and perform core searches offline.

Do not begin specialised library development until Phases 1A–1C pass.

**PHASE 2: AUDIT RISK AND EVIDENCE LIBRARY (M)**

Seed from the migrated audit-risk dataset (Phase 0), then extend to the
v1 chain: business condition → risk factor → possible risk event →
potential misstatement → account/disclosure → assertion → possible control
weakness → audit response → procedure → evidence → expected result →
exception → follow-up. Fields per v1 spec; distinguish tests of controls
from substantive procedures; never treat a risk factor as proof of
misstatement. Test with synthetic examples across inventory, revenue,
purchases, receivables, payables, cash, payroll, and PPE.

**PHASE 3: PAKISTAN TAX RISK AND EVIDENCE LIBRARY (M)**

Seed from the migrated tax-engine dataset (Phase 0), then extend per the
v1 field list (tax type, jurisdiction, taxpayer category, provision,
effective date, conditions, calculation method, evidence, verification
steps, errors, return impact, verification status, last checked date).
Deterministic, testable calculations; never hard-code a rate, threshold,
exemption, or deadline without source + applicable period; mark unverified
rules clearly; test against independently verified expected results.

**PHASE 4: FINANCIAL REPORTING AND ACCOUNTING TREATMENT LIBRARY (L)**

Per the v1 spec: transaction analysis, applicable standards, recognition,
initial/subsequent measurement, journal entries, presentation, disclosure,
statement impact, worked examples, common mistakes, source references,
applicable periods, verification status. Link treatments to audit risks,
reconciliation workflows, and FS analysis. Never assume a standard applies
from keyword matching alone.

**PHASE 5: ACCOUNTING RECONCILIATION ENGINE (M)**

Per the v1 spec: bank, supplier, customer, GL/subledger, inventory,
payroll, and tax reconciliations; CSV/Excel import; column mapping; exact
and configurable matching; duplicate detection; unmatched records; amount
differences; manual resolution with explanations; exportable reports.
Preserve original imported data; never auto-classify every difference as
an error.

**PHASE 6: EXCEL AND FINANCIAL DATA ANALYSIS (S)**

Per the v1 spec: data cleaning, duplicates, matching, date/amount
validation, variance analysis, summaries, exception reporting,
reproducible calculations, CSV/Excel exports. "Excel automation" means
Python-generated workbooks and templates (e.g., openpyxl) — never
VBA/macros, never execute embedded macros.

**PHASE 7: BIA/BFD BUSINESS CASE ANALYSIS (M)**

First verify the applicable ICAP syllabus (current Scheme 2025: CAF-7 is
"Business Insights and Analysis"; CFAP-4 is "Strategic Business Finance").
Seed from the migrated case-engine dataset (Phase 0), then build the v1
chain: facts → issue → objective → concepts → quantitative/qualitative
analysis → alternatives → evaluation → recommendation → implementation →
risks/KPIs. Distinguish syllabus content from supplementary frameworks; use
manual tagging and transparent rule-based suggestions.

**PHASE 8: FINANCIAL STATEMENT ANALYSIS (S)**

Ratios, trends, common-size, variance, cash-flow, working-capital analysis,
red-flag indicators with explanations and source-linked notes. Indicators
are prompts for investigation, never proof of error or fraud.

**PHASE 9: AUDIT WORKING PAPERS AND INTERNAL CONTROLS (M)**

Configurable templates: planning checklists, risk registers, control
descriptions, control-testing and substantive-procedure templates, evidence
registers, review and completion checklists, exception tracking. Never claim
generic templates satisfy a particular firm's methodology.

**PHASE 10: CORPORATE FINANCE AND DISCLOSURES (M)**

Disclosures, investment appraisal, cost of capital, valuation, financing
decisions, capital budgeting, sensitivity analysis, financial modelling.
Assumptions visible; calculations reproducible.

**PHASE 11: COMPANY LAW AND COMPLIANCE (M)**

Source-traceable compliance library per the v1 field list (jurisdiction,
entity type, requirement, legal source, effective date, deadline,
applicability, documents, verification status, last checked). Never present
an outdated deadline as current.

**PHASE 12: PROFESSIONAL RESEARCH AND CONTINUOUS IMPROVEMENT (S)**

Technical issue registration, research questions, source comparison,
analysis, conclusions, outstanding uncertainties, review notes, version
history — plus the review-due scheduler already in the core schema.
Support expansion into additional disciplines.

**PHASE 13: FULL SYSTEM VALIDATION (M)**

Test all modules together: search across modules and workspaces,
cross-module link integrity, source traceability, database migrations,
verified backup restoration, offline operation, calculation accuracy,
duplicate handling, data integrity, the Phase 1C performance targets,
module compatibility, and existing feature stability. Resolve critical
defects before declaring the system complete.

---
### 9. FUTURE EXPANSION WITHOUT REBUILDING

The user must be able to add new material independently of software
development wherever practical. Support at least the following operations:

1. Import new documents.
2. Add structured knowledge records.
3. Edit existing records.
4. Create new topics and categories.
5. Add new calculation templates.
6. Add new checklists.
7. Add new source references.
8. Add new professional modules through documented extension points.
9. Update rules without deleting historical versions.
10. Export data for migration to another application.
11. Create cross-module relationships as no-code link records (section 4B).

Separate technical software changes from ordinary knowledge updates. For
example: adding a new audit procedure means adding or editing a record, not
modifying the core application; updating a tax rate means a dated,
source-linked rule change plus calculation tests; adding a document means
import and indexing; adding a new professional discipline follows the
documented module-development process.

Provide sample templates and instructions so the user can maintain the
knowledge base without editing Python source code for routine updates.
Where new functionality genuinely requires programming, explain this
limitation clearly.

---

### 10. VERSION CONTROL AND HISTORICAL RECORDS

Do not silently overwrite technical knowledge. For important rules,
preserve: original record ID, version, previous content, revised content,
reason for change, source of change, effective date, date reviewed,
verification status. When a tax rule, accounting requirement, or
professional standard changes, mark the previous version as superseded
where appropriate. Do not erase historical records needed to understand
earlier transactions or reporting periods. Support database migrations so
future software updates preserve existing data.

---

### 11. SECURITY AND PROFESSIONAL CONFIDENTIALITY

The application is initially a personal tool. Do not assume that personal
cloud storage is suitable for confidential professional records.

- Do not upload client files without explicit authorisation.
- Do not bypass firm security policies.
- Keep credentials out of source code.
- Do not transmit user data without permission.
- Use synthetic datasets for development and testing.
- Provide a clear way to separate personal study material from professional
  records.
- Keep imported files isolated from executable application code.
- Do not execute imported scripts or macros.
- Explain backup and encryption limitations honestly: local SQLite files
  and ZIP backups are not encrypted by default; operating-system-level
  file protection applies. Optional SQLCipher-based encryption may be
  added as a future module — do not promise it now.

If multi-user functionality is added in the future, assess
authentication, access controls, audit trails, encryption, and data
protection as separate requirements.

---

### 12. TESTING AND ACCEPTANCE

Every phase must include tests. Use synthetic data and known expected
results. For calculations, compare outputs against independently checked
examples. For search, test that relevant records are found and irrelevant
matches are not presented as definitive answers. For document ingestion,
test new, changed, unchanged, duplicate, missing, unsupported, and
unreadable files. For updates, test that existing data remains intact.
Maintain automated regression tests so that a new module cannot silently
break an earlier one.

TESTING_GUIDE.md must include a reusable acceptance-test checklist
template — feature, data used, expected vs actual result, pass/fail,
tester, date — applied at every phase gate.

Never claim a feature works unless it has been implemented and tested.
Never claim that a test passed if it was not executed.

---

### 13. PROJECT DOCUMENTATION

Maintain these files throughout development:

- PROJECT_STATUS.md
- ARCHITECTURE.md
- DATABASE_SCHEMA.md
- MODULE_DEVELOPMENT_GUIDE.md
- SOURCE_VERIFICATION_POLICY.md
- BACKUP_AND_RESTORE.md
- CHANGELOG.md
- TESTING_GUIDE.md
- USER_GUIDE.md
- REUSE_AUDIT.md (produced in Phase 0)

PROJECT_STATUS.md must record: current phase, completed phases, features
implemented, actual test results, known defects, current database version,
outstanding requirements, backup status, and the exact next action. Update
these files whenever the project changes. Do not rely solely on
conversational memory to preserve development progress.

---

### 14. REQUIRED COMPLETION REPORT

At the end of each phase, report:

1. Features implemented.
2. Files and components changed.
3. Tests actually executed.
4. Passed tests.
5. Failed tests.
6. Known limitations.
7. Data migration status.
8. Backup status.
9. Acceptance criteria status.
10. Remaining tasks.
11. Recommended next action.

Stop at each phase boundary and request approval before beginning the next
phase. Do not mark a phase complete until its acceptance criteria pass. If
a requirement cannot be implemented, explain why and propose the simplest
reliable alternative.

---

### 15. INITIAL EXECUTION INSTRUCTIONS

Begin with **Phase 0 only**: inventory the existing applications, record
migrate / wrap / retire decisions with reasons, and stage seed datasets.
Write no new application code in Phase 0.

Then proceed to Phase 1A, then 1B, then 1C — stopping at each gate for
approval. Do not start specialised library development until Phases
1A–1C pass their acceptance criteria.

Continue through subsequent phases in order, respecting the MVP boundary
(Phases 0–4) and the post-February-2027 scheduling of Phases 5–12 unless
Bilal explicitly reorders them.

The final product must be a dependable, source-traceable, and expandable
CA Knowledge Hub that supports the user's education, articleship, and
professional career without requiring a complete rebuild when new needs
arise.

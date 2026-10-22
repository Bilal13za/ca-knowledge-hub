# PROJECT: LIFELONG CA KNOWLEDGE AND PROFESSIONAL PRACTICE SYSTEM

*(Master prompt supplied by Bilal, 2026-10-21. Filed verbatim for reference.)*

1. YOUR ROLE

Act as a senior software architect, Python developer, database engineer, quality assurance specialist, and professional knowledge-system designer.

Your task is to build a reliable, expandable, local-first knowledge and analysis application for a Chartered Accountancy student in Pakistan.

This is not merely an exam-preparation application. It must be designed to support the user's progression through:

1. CA studies.
2. Articleship and practical training.
3. Qualification as a Chartered Accountant.
4. Professional practice and continuing development.
5. Potential future work in audit, taxation, financial reporting, finance, internal audit, advisory, management, and entrepreneurship.

The application must be useful at every stage without requiring a complete rebuild.

Build the software foundation once. Allow the user to add, update, extend, and replace knowledge modules independently.

The application should remain useful even when the user's career direction changes.

---

2. THE CORE VISION

Build one integrated application called:

CA Knowledge Hub

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

Build one common platform with specialised modules that share the underlying infrastructure.

The user should be able to add new modules in the future without redesigning the application.

---

3. NON-NEGOTIABLE DESIGN PRINCIPLES

A. Build once, extend indefinitely

The architecture must support future expansion without requiring a complete rebuild.

New modules must be installable or addable through documented procedures.

Adding a new library must not require rewriting the core search engine, database, document manager, interface, backup system, or source register.

Use modular components and documented interfaces.

Avoid tightly coupling specialised accounting or tax logic to the application's main interface.

B. Keep the system free

Assume development is performed without a development fee.

Prefer free and open-source software.

Do not introduce mandatory:

- Paid subscriptions.
- Paid database hosting.
- AI API usage.
- Commercial cloud integrations.
- Licensed software that is not necessary for the core functionality.

Clearly disclose optional expenses before introducing a feature that could create recurring costs.

Verify the licences and permitted uses of third-party dependencies.

C. Local-first architecture

The system must operate on Windows and remain useful offline.

Use a local database for structured knowledge and search indexes.

The application must not require an internet connection for its core search, browsing, calculations, and data-processing functions.

Online access may be needed to download documents, check current sources, or access cloud-only files.

D. No AI dependency

The core system must not depend on generative AI.

Use conventional programming, structured records, search, explicit rules, calculations, and user-defined relationships.

Do not make AI necessary for retrieving, calculating, validating, or displaying stored knowledge.

The architecture may allow an optional AI integration in the future, but the core system must remain fully functional without it.

E. Source traceability

Every technical knowledge record must be traceable to its source wherever applicable.

Never invent:

- Legal provisions.
- Tax rates.
- Accounting requirements.
- Auditing requirements.
- Source quotations.
- Page references.
- Effective dates.
- Verification status.

Distinguish between imported documents, extracted statements, user-created notes, verified technical rules, and professional interpretations.

F. User control

The user must remain in control of:

- Adding and removing material.
- Editing knowledge records.
- Verifying technical rules.
- Selecting modules.
- Backing up data.
- Restoring previous versions.
- Changing cloud storage providers.
- Exporting and migrating the system.

Do not make important data dependent on a proprietary, inaccessible format.

---

4. PERMANENT TECHNICAL ARCHITECTURE

Design the application in clearly separated layers.

Layer 1: User interface

A lightweight, desktop-friendly interface providing:

- Dashboard.
- Global search.
- Module navigation.
- Study Mode.
- Practice Mode.
- Professional Mode.
- Document library.
- Knowledge-record viewer.
- Refresh Library.
- Search filters.
- Processing history.
- Technical source viewer.
- Settings.
- Export and backup controls.
- Module management.

The interface must remain usable on a Windows laptop with 8 GB RAM.

Avoid unnecessary resource-heavy features.

Layer 2: Application services

Create reusable services for:

- Document ingestion.
- Text extraction.
- Search.
- Knowledge-record management.
- Source tracking.
- Calculations.
- Validation.
- Reconciliation.
- Reporting.
- Export.
- Backup and restoration.
- Database migration.
- Module registration.

These services must be independent of individual professional modules wherever practical.

Layer 3: Structured database

Use SQLite for local structured information.

Design a documented, versioned schema supporting:

- Documents.
- Knowledge records.
- Sources.
- Modules.
- Topics.
- Tags.
- Relationships.
- Rules.
- Procedures.
- Calculations.
- Verification records.
- Revision history.
- User bookmarks.
- Study progress.
- Application settings.

Use a suitable local full-text search implementation, such as SQLite FTS5 where supported.

Keep the database schema extensible.

Do not create a separate database for every module unless there is a documented technical reason.

Layer 4: Module system

Create a module registry that allows the application to discover and load specialised libraries.

Each module must define its:

- Name.
- Description.
- Version.
- Data requirements.
- Search categories.
- User interface components.
- Calculation functions, if applicable.
- Validation rules.
- Source requirements.
- Dependencies.
- Tests.
- Upgrade and migration procedures.

Adding a module must not break existing modules.

Document the process for creating a new module.

Layer 5: Storage and file access

Keep the application independent of any single cloud-storage provider.

The initial cloud archive will be TeraBox, but the application must not depend on undocumented TeraBox endpoints or require a TeraBox API.

The initial workflow is:

1. The user downloads documents from TeraBox.
2. The user places the documents in a configured local folder.
3. The application scans that folder.
4. The user clicks Refresh Library.
5. The application extracts, indexes, and catalogues the documents.
6. The documents become searchable locally.

Do not assume that TeraBox offers a synchronised local folder.

Support changing the document folder or cloud-storage provider through configuration rather than architectural changes.

---

5. DOCUMENT MANAGEMENT AND REFRESH LIBRARY

This is a critical foundation and must be completed before specialised knowledge libraries are developed.

Initially support:

- PDF.
- TXT.
- Markdown.
- DOCX.
- CSV.
- XLSX.

Design the ingestion system so additional formats can be added later.

Refresh Library requirements

The Refresh Library function must:

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

Use file hashes where appropriate.

Do not automatically delete knowledge records when a source file disappears.

Mark missing sources and allow the user to decide what to do.

For PDFs, retain page-level references where available.

For scanned documents, report that OCR is needed when text extraction is inadequate.

For spreadsheets, preserve sheet names, column headers, and relevant tabular structures.

Never execute imported macros or embedded programs.

Provide a processing report showing:

- New files.
- Updated files.
- Unchanged files.
- Missing files.
- Successfully indexed files.
- Failed files.
- Unsupported files.
- Documents requiring OCR.

---

6. THE KNOWLEDGE MODEL

Every specialised library must be capable of storing structured knowledge rather than relying entirely on unorganised documents.

A general knowledge record should support:

- Unique ID.
- Module.
- Topic.
- Subtopic.
- Title.
- Description.
- Keywords.
- Content.
- Related records.
- Source document.
- Source page or section.
- Jurisdiction, if applicable.
- Effective date, if applicable.
- Applicable period, if applicable.
- Verification status.
- Last reviewed date.
- Revision history.

Modules may extend this structure with specialised fields.

For example, an audit record may need assertions and procedures, while a tax record may need a tax year and calculation method.

Do not force every module into an identical data structure when their requirements differ.

Provide reusable shared fields while allowing specialised extensions.

---

7. THREE OPERATING MODES

Implement three modes within the same application.

These modes must organise and present information differently without silently changing technical requirements or calculations.

MODE A: STUDY MODE

Purpose: Support examination preparation and learning.

Features may include:

- ICAP syllabus mapping.
- Topic-based notes.
- Concept summaries from stored material.
- Worked examples.
- Practice questions.
- Answer frameworks.
- Revision checklists.
- Weak-topic tracking.
- Personal notes.
- Mistake logs.
- Progress tracking.
- Source references.

The user must be able to update syllabus mappings when the syllabus changes.

Do not assume that all stored professional material is examinable.

Clearly distinguish examinable syllabus content from supplementary material.

MODE B: PRACTICE MODE

Purpose: Help the user understand and prepare for practical accounting, audit, tax, finance, and analytical tasks.

Features may include:

- Risk identification.
- Procedure selection.
- Evidence checklists.
- Reconciliation workflows.
- Tax calculations.
- Journal-entry analysis.
- Financial data processing.
- Internal control assessment.
- Business process documentation.
- Exception investigation.
- Workpaper preparation templates.

All outputs must be reviewable and editable.

Do not automatically represent a preliminary analysis as a completed professional conclusion.

MODE C: PROFESSIONAL MODE

Purpose: Support more advanced professional work after qualification.

Potential features include:

- Technical research.
- Financial reporting issue analysis.
- Tax compliance research.
- Audit planning references.
- Risk and control registers.
- Reusable reporting templates.
- Financial analysis.
- Management reporting.
- Valuation models.
- Compliance calendars.
- Professional checklists.
- Quality-control reviews.

Professional Mode must support explicit source verification and revision tracking.

It must not imply that stored rules are necessarily current or that outputs replace professional judgement, supervision, engagement requirements, or applicable standards.

Professional Mode must not automatically store confidential client information in the user's personal cloud archive.

---

8. DEVELOPMENT ROADMAP

Build the project in the following sequence.

Complete and validate each phase before proceeding to the next.

Do not attempt to populate every library simultaneously.

PHASE 1: CORE APPLICATION

Build:

- Application interface.
- SQLite database.
- Search index.
- Document manager.
- Refresh Library.
- Source tracking.
- Knowledge-record management.
- Export.
- Backup and restoration.
- Module registry.
- Project documentation.
- Automated tests.

Acceptance criteria:

The user can import documents, refresh the library, search extracted content, view source references, create and edit knowledge records, export records, back up the database, restore it, and perform core searches offline.

Do not begin specialised library development until these requirements pass testing.

PHASE 2: AUDIT RISK AND EVIDENCE LIBRARY

Build a rule-based library connecting:

Business condition
→ Risk factor
→ Possible risk event
→ Potential misstatement
→ Account or disclosure
→ Relevant assertion
→ Possible control weakness
→ Audit response
→ Audit procedure
→ Required evidence
→ Expected result
→ Exception
→ Follow-up investigation.

Include fields for:

- Audit area.
- Transaction type.
- Risk description.
- Relevant assertions.
- Control considerations.
- Procedure type.
- Detailed procedures.
- Evidence.
- Expected results.
- Source references.
- Applicable auditing standards.
- Verification status.
- Last reviewed date.

Distinguish tests of controls from substantive procedures.

Do not treat a risk factor as proof that a misstatement exists.

Require procedures to be tailored to the actual circumstances.

Test the module using synthetic examples involving inventory, revenue, purchases, receivables, payables, cash, payroll, and property, plant and equipment.

Complete acceptance testing before Phase 3.

PHASE 3: PAKISTAN TAX RISK AND EVIDENCE LIBRARY

Build a tax library for applicable Pakistani taxation topics.

Map the content to the user's relevant ICAP syllabus and authoritative source material.

Potential topics include:

- Income tax.
- Withholding tax.
- Federal sales tax.
- Provincial sales tax on services.
- Tax computations.
- Tax reconciliations.
- Return preparation.
- Supporting evidence.
- Compliance requirements.

Each rule must support:

- Tax type.
- Jurisdiction.
- Taxpayer category.
- Transaction type.
- Applicable tax year or period.
- Source legislation or official guidance.
- Relevant provision.
- Effective date.
- Conditions.
- Calculation method.
- Evidence requirements.
- Verification steps.
- Potential errors.
- Return impact.
- Verification status.
- Last checked date.

Use deterministic, testable calculation functions.

Never hard-code a tax rate, threshold, exemption, or deadline without recording its source and applicable period.

Mark unverified rules clearly.

Test calculations against independently verified expected results.

Complete acceptance testing before Phase 4.

PHASE 4: FINANCIAL REPORTING AND ACCOUNTING TREATMENT LIBRARY

Build a structured library supporting:

- Transaction analysis.
- Applicable standards.
- Recognition criteria.
- Initial measurement.
- Subsequent measurement.
- Journal entries.
- Presentation.
- Disclosure.
- Financial statement impact.
- Worked examples.
- Common mistakes.
- Source references.
- Applicable periods.
- Verification status.

Connect relevant accounting treatments to audit risks, reconciliation workflows, and financial statement analysis.

Do not assume a standard applies solely because a keyword matches.

Complete acceptance testing before Phase 5.

PHASE 5: ACCOUNTING RECONCILIATION ENGINE

Build reusable workflows for:

- Bank reconciliation.
- Supplier reconciliation.
- Customer balances.
- General ledger and subledger comparison.
- Inventory record comparison.
- Payroll reconciliation.
- Tax account reconciliation.

Support:

- CSV and Excel imports.
- Column mapping.
- Exact matching.
- Configurable matching rules.
- Duplicate detection.
- Unmatched records.
- Amount differences.
- Manual resolution.
- Explanations of matching outcomes.
- Exportable reports.

Preserve original imported data.

Do not automatically classify every difference as an error.

Complete acceptance testing before Phase 6.

PHASE 6: EXCEL AND FINANCIAL DATA ANALYSIS

Build reusable workflows for:

- Data cleaning.
- Duplicate detection.
- Record matching.
- Date and amount validation.
- Variance analysis.
- Financial summaries.
- Exception reporting.
- Reproducible calculations.
- CSV and Excel exports.

Use free libraries where appropriate.

Do not execute embedded macros.

Complete acceptance testing before Phase 7.

PHASE 7: BIA/BFD BUSINESS CASE ANALYSIS

First verify the applicable ICAP syllabus.

Build structured workflows for:

Case facts
→ Main issue
→ Objective
→ Relevant concepts
→ Quantitative analysis
→ Qualitative analysis
→ Alternatives
→ Evaluation
→ Recommendation
→ Implementation
→ Risks and KPIs.

Include case libraries, topic tags, calculation templates, answer structures, and self-assessment checklists.

Distinguish syllabus content from supplementary business frameworks.

Use manual tagging and transparent rule-based suggestions rather than claiming to understand arbitrary narratives automatically.

Complete acceptance testing before Phase 8.

PHASE 8: FINANCIAL STATEMENT ANALYSIS

Build:

- Financial ratio calculations.
- Trend analysis.
- Common-size statements.
- Variance analysis.
- Cash flow analysis.
- Working capital analysis.
- Red-flag indicators.
- Supporting explanations.
- Source-linked interpretation notes.

Distinguish indicators requiring investigation from proof of error or fraud.

PHASE 9: AUDIT WORKING PAPERS AND INTERNAL CONTROLS

Build:

- Documentation templates.
- Planning checklists.
- Risk registers.
- Control descriptions.
- Control testing templates.
- Substantive procedure templates.
- Evidence registers.
- Review checklists.
- Exception tracking.
- Completion checklists.

Make all templates configurable.

Do not claim that generic templates automatically satisfy a particular firm's methodology or engagement requirements.

PHASE 10: CORPORATE FINANCE AND DISCLOSURES

Build appropriate modules for:

- Financial reporting disclosures.
- Investment appraisal.
- Cost of capital.
- Valuation.
- Financing decisions.
- Capital budgeting.
- Sensitivity analysis.
- Financial modelling.

Keep assumptions visible and calculations reproducible.

PHASE 11: COMPANY LAW AND COMPLIANCE

Build a source-traceable compliance library with:

- Jurisdiction.
- Entity type.
- Requirement.
- Legal source.
- Effective date.
- Deadline.
- Applicability conditions.
- Required documents.
- Verification status.
- Last checked date.

Do not present an outdated deadline as current.

PHASE 12: PROFESSIONAL RESEARCH AND CONTINUOUS IMPROVEMENT

Build workflows for:

- Technical issue registration.
- Research questions.
- Source comparison.
- Applicable requirements.
- Analysis.
- Conclusion.
- Outstanding uncertainties.
- Review notes.
- Version history.
- Periodic review reminders.

Support future expansion into additional professional disciplines.

PHASE 13: FULL SYSTEM VALIDATION

Test all modules together.

Verify:

- Search across modules.
- Source traceability.
- Database migrations.
- Backup restoration.
- Offline operation.
- Calculation accuracy.
- Duplicate handling.
- Data integrity.
- Performance.
- Module compatibility.
- Existing feature stability.

Resolve critical defects before declaring the system complete.

---

9. FUTURE EXPANSION WITHOUT REBUILDING

This is a critical architectural requirement.

The user must be able to add new material independently of software development wherever practical.

Support at least the following operations:

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

Separate technical software changes from ordinary knowledge updates.

For example:

- Adding a new audit procedure should normally require adding or editing a record, not modifying the core application.
- Updating a tax rate should involve a dated, source-linked rule change and appropriate calculation tests.
- Adding a new document should require only import and indexing.
- Adding an entirely new professional discipline should follow the documented module-development process.

Provide sample templates and instructions so the user can maintain the knowledge base without editing Python source code for routine updates.

Where new functionality genuinely requires programming, explain this limitation clearly.

---

10. VERSION CONTROL AND HISTORICAL RECORDS

Do not silently overwrite technical knowledge.

For important rules, preserve:

- Original record ID.
- Version.
- Previous content.
- Revised content.
- Reason for change.
- Source of change.
- Effective date.
- Date reviewed.
- Verification status.

When a tax rule, accounting requirement or professional standard changes, mark the previous version as superseded where appropriate.

Do not erase historical records that may be needed to understand earlier transactions or reporting periods.

Support database migrations so future software updates preserve existing data.

---

11. SECURITY AND PROFESSIONAL CONFIDENTIALITY

The application is initially a personal tool.

Do not assume that personal cloud storage is suitable for confidential professional records.

- Do not upload client files without explicit authorisation.
- Do not bypass firm security policies.
- Keep credentials out of source code.
- Do not transmit user data without permission.
- Use synthetic datasets for development and testing.
- Provide a clear way to separate personal study material from professional records.
- Keep imported files isolated from executable application code.
- Do not execute imported scripts or macros.
- Explain backup and encryption limitations honestly.

If multi-user functionality is added in the future, assess authentication, access controls, audit trails, encryption and data protection as separate requirements.

---

12. TESTING AND ACCEPTANCE

Every phase must include tests.

Use synthetic data and known expected results.

For calculations, compare outputs against independently checked examples.

For search, test whether relevant records are found and irrelevant matches are not presented as definitive answers.

For document ingestion, test new, changed, unchanged, duplicate, missing, unsupported and unreadable files.

For updates, test that existing data remains intact.

Maintain automated regression tests so that a new module cannot silently break an earlier one.

Never claim a feature works unless it has been implemented and tested.

Never claim that a test passed if it was not executed.

---

13. PROJECT DOCUMENTATION

Maintain these files throughout development:

PROJECT_STATUS.md
ARCHITECTURE.md
DATABASE_SCHEMA.md
MODULE_DEVELOPMENT_GUIDE.md
SOURCE_VERIFICATION_POLICY.md
BACKUP_AND_RESTORE.md
CHANGELOG.md
TESTING_GUIDE.md
USER_GUIDE.md

PROJECT_STATUS.md must record:

- Current phase.
- Completed phases.
- Features implemented.
- Actual test results.
- Known defects.
- Current database version.
- Outstanding requirements.
- Backup status.
- Exact next action.

Update these files whenever the project changes.

Do not rely solely on conversational memory to preserve development progress.

---

14. REQUIRED COMPLETION REPORT

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

Stop at each phase boundary and request approval before beginning the next phase.

Do not mark a phase complete until its acceptance criteria pass.

If a requirement cannot be implemented, explain why and propose the simplest reliable alternative.

---

15. INITIAL EXECUTION INSTRUCTIONS

Begin with Phase 1 only.

First inspect the available environment and any existing project files.

Do not start building the specialised Audit, Tax or Financial Reporting libraries yet.

Build and test the core application, document ingestion, Refresh Library, search, structured database, source tracking, backup and module registration.

Provide the user with a working version and instructions for testing it.

Once Phase 1 passes its acceptance criteria, stop and request approval to proceed to Phase 2.

Continue through subsequent phases in order.

The final product must be a dependable, source-traceable and expandable CA Knowledge Hub that supports the user's education, articleship and professional career without requiring a complete rebuild when new needs arise.

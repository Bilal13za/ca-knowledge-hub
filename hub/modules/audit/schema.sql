-- Audit module schema (ported from Audit Risk and Evidence Library, Phase 0 MIGRATE).
-- All tables prefixed audit_ to live in the Hub's single database.

CREATE TABLE IF NOT EXISTS audit_assertions (
    id            TEXT PRIMARY KEY,      -- e.g. TRN-OCC, BAL-EXI, DIS-COM
    category      TEXT NOT NULL,         -- Transactions and events / Account balances / Presentation and disclosure
    name          TEXT NOT NULL,
    description   TEXT NOT NULL,
    framework_note TEXT
);
CREATE TABLE IF NOT EXISTS audit_procedures (
    id                TEXT PRIMARY KEY,  -- e.g. P-INV-001
    title             TEXT NOT NULL,
    objective         TEXT NOT NULL,
    steps             TEXT NOT NULL,     -- numbered steps, newline separated
    procedure_type    TEXT NOT NULL,     -- Inspection / Observation / Inquiry / External confirmation /
                                        -- Recalculation / Reperformance / Analytical procedures /
                                        -- Vouching / Tracing / Cut-off testing / Physical verification
    test_type         TEXT NOT NULL,     -- Test of audit_controls / Substantive procedure / Dual-purpose
    population        TEXT,
    sampling_notes    TEXT,
    expected_result   TEXT NOT NULL,
    exception_criteria TEXT NOT NULL,
    follow_up         TEXT NOT NULL,
    source_reference  TEXT,
    review_status     TEXT NOT NULL DEFAULT 'Draft'
);
CREATE TABLE IF NOT EXISTS audit_cycles (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'Verified'
);
CREATE TABLE IF NOT EXISTS audit_factors (
    id                 TEXT PRIMARY KEY,  -- e.g. F-INV-001
    name               TEXT NOT NULL,
    description        TEXT NOT NULL,
    cycle_id           TEXT NOT NULL REFERENCES audit_cycles(id),
    risk_category      TEXT NOT NULL,     -- Inherent risk / Fraud risk / Control risk / ...
    conditions_relevant TEXT,            -- conditions under which the factor is relevant
    warning_signs      TEXT,
    source_reference   TEXT,
    review_status      TEXT NOT NULL DEFAULT 'Draft'
);
CREATE TABLE IF NOT EXISTS audit_controls (
    id                  TEXT PRIMARY KEY,  -- e.g. C-INV-001
    description         TEXT NOT NULL,
    objective           TEXT,
    preventive_detective TEXT,  -- Preventive / Detective / Both
    manual_automated    TEXT,    -- Manual / Automated / IT-dependent manual
    frequency           TEXT,
    responsible_role    TEXT,
    evidence_of_operation TEXT,
    limitations         TEXT,
    source_reference    TEXT,
    review_status       TEXT NOT NULL DEFAULT 'Draft'
);
CREATE TABLE IF NOT EXISTS audit_evidence (
    id                       TEXT PRIMARY KEY,  -- e.g. E-INV-001
    name                     TEXT NOT NULL,
    description              TEXT NOT NULL,
    source                   TEXT,   -- Internal / External / Auditor-generated
    reliability_notes        TEXT NOT NULL,
    limitations              TEXT,
    expected_characteristics TEXT,
    contradictory_evidence   TEXT,
    source_reference         TEXT,
    review_status            TEXT NOT NULL DEFAULT 'Draft'
);
CREATE TABLE IF NOT EXISTS audit_factor_risk (
    factor_id            TEXT NOT NULL REFERENCES audit_factors(id),
    risk_id              TEXT NOT NULL REFERENCES audit_risks(id),
    trigger_condition    TEXT,
    applicability        TEXT,   -- conditions that make the mapping applicable
    explanation          TEXT NOT NULL,
    additional_info_needed TEXT,
    confidence_basis     TEXT,   -- why the reviewer believes the link holds
    source_reference     TEXT,
    reviewer             TEXT,
    review_status        TEXT NOT NULL DEFAULT 'Draft',
    PRIMARY KEY (factor_id, risk_id)
);
CREATE TABLE IF NOT EXISTS audit_builds (
    build_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    built_at     TEXT NOT NULL,
    note         TEXT
);
CREATE TABLE IF NOT EXISTS audit_procedure_assertion (
    procedure_id TEXT NOT NULL REFERENCES audit_procedures(id),
    assertion_id TEXT NOT NULL REFERENCES audit_assertions(id),
    PRIMARY KEY (procedure_id, assertion_id)
);
CREATE TABLE IF NOT EXISTS audit_procedure_evidence (
    procedure_id TEXT NOT NULL REFERENCES audit_procedures(id),
    evidence_id  TEXT NOT NULL REFERENCES audit_evidence(id),
    notes        TEXT,
    PRIMARY KEY (procedure_id, evidence_id)
);
CREATE TABLE IF NOT EXISTS audit_risk_assertion (
    risk_id       TEXT NOT NULL REFERENCES audit_risks(id),
    assertion_id  TEXT NOT NULL REFERENCES audit_assertions(id),
    why_relevant  TEXT NOT NULL,  -- why THIS assertion for THIS risk
    conditions    TEXT,           -- under what conditions the assertion is relevant
    PRIMARY KEY (risk_id, assertion_id)
);
CREATE TABLE IF NOT EXISTS audit_risk_control (
    risk_id    TEXT NOT NULL REFERENCES audit_risks(id),
    control_id TEXT NOT NULL REFERENCES audit_controls(id),
    explanation TEXT,
    PRIMARY KEY (risk_id, control_id)
);
CREATE TABLE IF NOT EXISTS audit_risks (
    id                      TEXT PRIMARY KEY,  -- e.g. R-INV-001
    title                   TEXT NOT NULL,
    description             TEXT NOT NULL,
    causes                  TEXT,
    potential_consequences  TEXT,
    cycle_id                TEXT NOT NULL REFERENCES audit_cycles(id),
    inherent_risk_notes     TEXT,
    source_reference        TEXT,
    review_status           TEXT NOT NULL DEFAULT 'Draft'
);
CREATE TABLE IF NOT EXISTS audit_risk_procedure (
    risk_id      TEXT NOT NULL REFERENCES audit_risks(id),
    procedure_id TEXT NOT NULL REFERENCES audit_procedures(id),
    reason       TEXT,   -- why this procedure addresses this risk
    PRIMARY KEY (risk_id, procedure_id)
);
CREATE TABLE IF NOT EXISTS audit_rules (
    id             TEXT PRIMARY KEY,  -- e.g. RULE-INV-001
    name           TEXT NOT NULL,
    version        INTEGER NOT NULL DEFAULT 1,
    priority       INTEGER NOT NULL DEFAULT 100,  -- lower runs first
    effective_date TEXT,
    status         TEXT NOT NULL DEFAULT 'Active',  -- Active / Superseded / Retired
    definition     TEXT NOT NULL,     -- canonical JSON (see RULE_ENGINE.md)
    rationale      TEXT,
    source_reference TEXT,
    reviewed_by    TEXT,
    review_status  TEXT NOT NULL DEFAULT 'Draft',
    UNIQUE (id, version)
);

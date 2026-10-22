-- CA Knowledge Hub — financial reporting module schema (Phase 4).
-- All tables fr_-prefixed. Treatments link to standards, worked examples,
-- and (defensively) audit risks. No paragraph numbers are stored anywhere:
-- standard-level identification only; Bilal verifies detail against the
-- official text / his textbooks.

CREATE TABLE IF NOT EXISTS fr_standards (
    id                  TEXT PRIMARY KEY,   -- e.g. 'IFRS 15'
    title               TEXT NOT NULL,      -- e.g. 'Revenue from Contracts with Customers'
    summary             TEXT,               -- scope in plain words (study aid, not the standard)
    effective_from      TEXT,               -- YYYY-MM-DD where widely known
    jurisdiction        TEXT NOT NULL DEFAULT 'international',
    verification_status TEXT NOT NULL DEFAULT 'extracted_unverified',
    source_note         TEXT
);

CREATE TABLE IF NOT EXISTS fr_treatments (
    id                      TEXT PRIMARY KEY,   -- e.g. 'FR-TREAT-001'
    title                   TEXT NOT NULL,
    transaction_analysis    TEXT NOT NULL,
    recognition             TEXT,
    initial_measurement     TEXT,
    subsequent_measurement  TEXT,
    journals_json           TEXT NOT NULL DEFAULT '[]',
    presentation            TEXT,
    disclosure              TEXT,
    statement_impact        TEXT,
    common_mistakes_json    TEXT NOT NULL DEFAULT '[]',
    applicable_period       TEXT,
    verification_status     TEXT NOT NULL DEFAULT 'extracted_unverified',
    source_note             TEXT
);

CREATE TABLE IF NOT EXISTS fr_examples (
    id                  TEXT PRIMARY KEY,   -- e.g. 'FR-EX-001'
    treatment_id        TEXT NOT NULL REFERENCES fr_treatments(id),
    title               TEXT NOT NULL,
    facts               TEXT NOT NULL,
    solution            TEXT NOT NULL,
    journals_json       TEXT NOT NULL DEFAULT '[]',
    verification_status TEXT NOT NULL DEFAULT 'extracted_unverified'
);

CREATE TABLE IF NOT EXISTS fr_treatment_standard (
    treatment_id TEXT NOT NULL REFERENCES fr_treatments(id),
    standard_id  TEXT NOT NULL REFERENCES fr_standards(id),
    note         TEXT,
    PRIMARY KEY (treatment_id, standard_id)
);

-- No hard FK to audit_risks: module seeding order is not guaranteed.
-- Seed validates the link target exists before inserting.
CREATE TABLE IF NOT EXISTS fr_treatment_audit_risk (
    treatment_id  TEXT NOT NULL REFERENCES fr_treatments(id),
    audit_risk_id TEXT NOT NULL,
    note          TEXT,
    PRIMARY KEY (treatment_id, audit_risk_id)
);

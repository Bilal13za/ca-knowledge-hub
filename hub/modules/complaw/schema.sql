-- CA Knowledge Hub — complaw module schema (Phase 11).
-- Policy: never invent provisions or deadlines. Provision notes are
-- source-traced and verification-marked; deadlines are user-entered.

CREATE TABLE IF NOT EXISTS law_provisions (
    id                  INTEGER PRIMARY KEY,
    act                 TEXT NOT NULL DEFAULT 'Companies Act, 2017',
    section_no          TEXT,           -- NULL until traced to the statute
    title               TEXT NOT NULL,
    summary             TEXT,
    source_ref          TEXT,           -- where this was traced from
    verification_status TEXT NOT NULL DEFAULT 'user_note'
                        CHECK (verification_status IN ('verified',
                        'extracted_unverified','user_note','interpretation',
                        'superseded')),
    effective_date      TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS law_companies (
    id               INTEGER PRIMARY KEY,
    name             TEXT NOT NULL,
    cuin             TEXT,              -- company registration number
    company_type     TEXT,
    incorporation_date TEXT,
    registered_office TEXT,
    status           TEXT NOT NULL DEFAULT 'active',
    notes            TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS law_deadlines (
    id            INTEGER PRIMARY KEY,
    company_id    INTEGER REFERENCES law_companies(id) ON DELETE CASCADE,
    obligation    TEXT NOT NULL,
    provision_ref TEXT,                 -- free text link to a provision
    due_date      TEXT NOT NULL,        -- ISO date, user-entered
    frequency     TEXT,                 -- annual | quarterly | one-off ...
    done          INTEGER NOT NULL DEFAULT 0,
    done_date     TEXT,
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_law_deadlines_due ON law_deadlines(due_date);

CREATE TABLE IF NOT EXISTS law_filings (
    id           INTEGER PRIMARY KEY,
    company_id   INTEGER REFERENCES law_companies(id) ON DELETE CASCADE,
    form_name    TEXT NOT NULL,
    period_ended TEXT,
    filed_on     TEXT,
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','filed','acknowledged')),
    reference_no TEXT,
    notes        TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

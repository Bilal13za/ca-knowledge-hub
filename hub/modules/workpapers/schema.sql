-- CA Knowledge Hub — workpapers module schema (Phase 9).
-- Generic, configurable templates. These templates are study/practice
-- aids and do NOT claim to satisfy any particular firm's methodology.

CREATE TABLE IF NOT EXISTS wp_templates (
    id                  TEXT PRIMARY KEY,   -- e.g. 'WP-T-PLANNING'
    category            TEXT NOT NULL       -- planning | risk_register |
                        CHECK (category IN ('planning','risk_register',
                        'control_description','control_test',
                        'substantive_procedure','evidence_register',
                        'review_checklist','completion_checklist',
                        'exception_log')),
    title               TEXT NOT NULL,
    purpose             TEXT,
    structure_json      TEXT NOT NULL DEFAULT '[]',
    guidance            TEXT,
    verification_status TEXT NOT NULL DEFAULT 'user_note',
    disclaimer          TEXT NOT NULL DEFAULT
        'Generic template for study and practice. Does not satisfy any particular firm''s audit methodology.'
);

CREATE TABLE IF NOT EXISTS wp_papers (
    id            INTEGER PRIMARY KEY,
    engagement    TEXT NOT NULL,
    template_id   TEXT NOT NULL REFERENCES wp_templates(id),
    title         TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft','in_progress','in_review',
                                    'completed')),
    data_json     TEXT NOT NULL DEFAULT '{}',
    prepared_by   TEXT,
    prepared_at   TEXT,
    reviewed_by   TEXT,
    reviewed_at   TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wp_exceptions (
    id              INTEGER PRIMARY KEY,
    paper_id        INTEGER REFERENCES wp_papers(id) ON DELETE CASCADE,
    engagement      TEXT NOT NULL DEFAULT '',
    description     TEXT NOT NULL,
    assertion       TEXT,
    potential_impact TEXT,
    follow_up       TEXT,
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','in_follow_up','cleared')),
    resolution      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wp_evidence (
    id             INTEGER PRIMARY KEY,
    paper_id       INTEGER REFERENCES wp_papers(id) ON DELETE CASCADE,
    ref            TEXT NOT NULL,
    description    TEXT NOT NULL,
    source         TEXT,
    date_obtained  TEXT,
    reliability    TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_wp_papers_eng ON wp_papers(engagement, status);
CREATE INDEX IF NOT EXISTS idx_wp_exc_status ON wp_exceptions(status);

-- CA Knowledge Hub — research module schema (Phase 12).
-- Professional research workflow: issues, sources, findings,
-- source comparisons, and versioned conclusions. Conclusions are
-- append-only history — never overwritten.

CREATE TABLE IF NOT EXISTS rs_issues (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    question    TEXT NOT NULL,
    background  TEXT,
    status      TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','in_progress','concluded')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rs_sources (
    id          INTEGER PRIMARY KEY,
    issue_id    INTEGER NOT NULL REFERENCES rs_issues(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL DEFAULT 'note'
                CHECK (source_type IN ('statute','circular','book',
                        'website','note','precedent')),
    citation    TEXT NOT NULL,
    url_or_ref  TEXT,
    reliability TEXT,              -- primary | secondary | commentary
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rs_sources_issue ON rs_sources(issue_id);

CREATE TABLE IF NOT EXISTS rs_findings (
    id         INTEGER PRIMARY KEY,
    issue_id   INTEGER NOT NULL REFERENCES rs_issues(id) ON DELETE CASCADE,
    source_id  INTEGER REFERENCES rs_sources(id) ON DELETE SET NULL,
    point      TEXT NOT NULL,       -- what the source says (paraphrased)
    relevance  TEXT,                -- how it bears on the question
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rs_comparisons (
    id         INTEGER PRIMARY KEY,
    issue_id   INTEGER NOT NULL REFERENCES rs_issues(id) ON DELETE CASCADE,
    aspect     TEXT NOT NULL,       -- what is being compared
    source_a_id INTEGER REFERENCES rs_sources(id) ON DELETE SET NULL,
    source_b_id INTEGER REFERENCES rs_sources(id) ON DELETE SET NULL,
    agreement  TEXT NOT NULL
               CHECK (agreement IN ('agree','conflict','unclear')),
    note       TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rs_conclusions (
    id             INTEGER PRIMARY KEY,
    issue_id       INTEGER NOT NULL REFERENCES rs_issues(id) ON DELETE CASCADE,
    version_no     INTEGER NOT NULL,
    conclusion_text TEXT NOT NULL,
    basis          TEXT,            -- which sources/findings support it
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (issue_id, version_no)
);
CREATE INDEX IF NOT EXISTS idx_rs_concl_issue ON rs_conclusions(issue_id);

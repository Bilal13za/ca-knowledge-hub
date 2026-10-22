-- Migration 001: initial core schema
-- UP --

CREATE TABLE IF NOT EXISTS schema_migrations (
    version      INTEGER PRIMARY KEY,
    description  TEXT NOT NULL,
    applied_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS modules (
    name          TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    version       TEXT NOT NULL DEFAULT '1.0.0',
    description   TEXT NOT NULL DEFAULT '',
    enabled       INTEGER NOT NULL DEFAULT 1,
    manifest_json TEXT NOT NULL DEFAULT '{}',
    installed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT NOT NULL UNIQUE,
    filename    TEXT NOT NULL,
    folder      TEXT NOT NULL DEFAULT '',
    file_hash   TEXT NOT NULL DEFAULT '',
    file_size   INTEGER NOT NULL DEFAULT 0,
    file_type   TEXT NOT NULL DEFAULT '',
    title       TEXT DEFAULT '',
    page_count  INTEGER,
    modified_at TEXT,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
    status      TEXT NOT NULL DEFAULT 'indexed',
    error_text  TEXT DEFAULT '',
    meta_json   TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

CREATE TABLE IF NOT EXISTS doc_chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    page_no     INTEGER,
    sheet_name  TEXT NOT NULL DEFAULT '',
    text        TEXT NOT NULL,
    UNIQUE (document_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_doc ON doc_chunks(document_id);

CREATE VIRTUAL TABLE IF NOT EXISTS doc_fts USING fts5(
    text, document_id UNINDEXED, chunk_id UNINDEXED,
    tokenize = 'porter'
);

CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'other',
    jurisdiction TEXT NOT NULL DEFAULT '',
    publisher   TEXT DEFAULT '',
    url         TEXT DEFAULT '',
    accessed_at TEXT DEFAULT '',
    notes       TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS knowledge_records (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    module              TEXT NOT NULL DEFAULT 'core',
    topic               TEXT NOT NULL DEFAULT '',
    subtopic            TEXT NOT NULL DEFAULT '',
    title               TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    keywords            TEXT NOT NULL DEFAULT '',
    content             TEXT NOT NULL DEFAULT '',
    source_id           INTEGER REFERENCES sources(id),
    source_page         TEXT NOT NULL DEFAULT '',
    jurisdiction        TEXT NOT NULL DEFAULT '',
    effective_date      TEXT NOT NULL DEFAULT '',
    applicable_period   TEXT NOT NULL DEFAULT '',
    verification_status TEXT NOT NULL DEFAULT 'user_note'
        CHECK (verification_status IN
               ('verified','extracted_unverified','user_note',
                'interpretation','superseded')),
    last_reviewed       TEXT NOT NULL DEFAULT '',
    review_due_date     TEXT NOT NULL DEFAULT '',
    extension_json      TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_kr_module ON knowledge_records(module);
CREATE INDEX IF NOT EXISTS idx_kr_topic ON knowledge_records(module, topic);
CREATE INDEX IF NOT EXISTS idx_kr_verif ON knowledge_records(verification_status);
CREATE INDEX IF NOT EXISTS idx_kr_reviewdue ON knowledge_records(review_due_date);

CREATE VIRTUAL TABLE IF NOT EXISTS record_fts USING fts5(
    title, description, keywords, content,
    record_id UNINDEXED, module UNINDEXED,
    tokenize = 'porter'
);

CREATE TABLE IF NOT EXISTS record_relations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_record_id INTEGER NOT NULL REFERENCES knowledge_records(id) ON DELETE CASCADE,
    target_record_id INTEGER NOT NULL REFERENCES knowledge_records(id) ON DELETE CASCADE,
    rel_type         TEXT NOT NULL DEFAULT 'related',
    note             TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source_record_id, target_record_id, rel_type)
);
CREATE INDEX IF NOT EXISTS idx_rel_source ON record_relations(source_record_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON record_relations(target_record_id);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS record_tags (
    record_id INTEGER NOT NULL REFERENCES knowledge_records(id) ON DELETE CASCADE,
    tag_id    INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (record_id, tag_id)
);

CREATE TABLE IF NOT EXISTS rules (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    module              TEXT NOT NULL DEFAULT 'core',
    rule_code           TEXT NOT NULL,
    title               TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    conditions_json     TEXT NOT NULL DEFAULT '{}',
    action_json         TEXT NOT NULL DEFAULT '{}',
    verification_status TEXT NOT NULL DEFAULT 'user_note'
        CHECK (verification_status IN
               ('verified','extracted_unverified','user_note',
                'interpretation','superseded')),
    source_id           INTEGER REFERENCES sources(id),
    effective_date      TEXT NOT NULL DEFAULT '',
    review_due_date     TEXT NOT NULL DEFAULT '',
    version             INTEGER NOT NULL DEFAULT 1,
    superseded_by       INTEGER REFERENCES rules(id),
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (module, rule_code, version)
);
CREATE INDEX IF NOT EXISTS idx_rules_module ON rules(module);

CREATE TABLE IF NOT EXISTS procedures (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    module              TEXT NOT NULL DEFAULT 'core',
    code                TEXT NOT NULL,
    title               TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    procedure_type      TEXT NOT NULL DEFAULT '',
    verification_status TEXT NOT NULL DEFAULT 'user_note'
        CHECK (verification_status IN
               ('verified','extracted_unverified','user_note',
                'interpretation','superseded')),
    source_id           INTEGER REFERENCES sources(id),
    review_due_date     TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (module, code)
);

CREATE TABLE IF NOT EXISTS calculations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    module              TEXT NOT NULL DEFAULT 'core',
    code                TEXT NOT NULL,
    title               TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    formula_text        TEXT NOT NULL DEFAULT '',
    parameters_json     TEXT NOT NULL DEFAULT '[]',
    verification_status TEXT NOT NULL DEFAULT 'user_note'
        CHECK (verification_status IN
               ('verified','extracted_unverified','user_note',
                'interpretation','superseded')),
    source_id           INTEGER REFERENCES sources(id),
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (module, code)
);

CREATE TABLE IF NOT EXISTS calculation_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    calculation_id INTEGER REFERENCES calculations(id),
    module         TEXT NOT NULL DEFAULT 'core',
    inputs_json    TEXT NOT NULL DEFAULT '{}',
    outputs_json   TEXT NOT NULL DEFAULT '{}',
    workspace      TEXT NOT NULL DEFAULT '',
    run_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS verification_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    verified_by TEXT NOT NULL DEFAULT '',
    verified_at TEXT NOT NULL DEFAULT (datetime('now')),
    method      TEXT NOT NULL DEFAULT '',
    result      TEXT NOT NULL DEFAULT 'verified',
    notes       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_verif_entity
    ON verification_records(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS revision_history (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type          TEXT NOT NULL,
    entity_id            INTEGER NOT NULL,
    version              INTEGER NOT NULL,
    previous_content_json TEXT NOT NULL DEFAULT '',
    revised_content_json  TEXT NOT NULL DEFAULT '',
    reason               TEXT NOT NULL DEFAULT '',
    source_of_change     TEXT NOT NULL DEFAULT '',
    effective_date       TEXT NOT NULL DEFAULT '',
    reviewed_at          TEXT NOT NULL DEFAULT '',
    verification_status  TEXT NOT NULL DEFAULT '',
    changed_at           TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rev_entity
    ON revision_history(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS bookmarks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id  INTEGER NOT NULL REFERENCES knowledge_records(id) ON DELETE CASCADE,
    note       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS study_progress (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    module       TEXT NOT NULL DEFAULT 'core',
    topic        TEXT NOT NULL DEFAULT '',
    record_id    INTEGER REFERENCES knowledge_records(id) ON DELETE SET NULL,
    status       TEXT NOT NULL DEFAULT 'not_started',
    score        REAL,
    attempts     INTEGER NOT NULL DEFAULT 0,
    last_studied TEXT NOT NULL DEFAULT '',
    UNIQUE (module, topic, record_id)
);

CREATE TABLE IF NOT EXISTS workspaces (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL UNIQUE,
    module_list_json TEXT NOT NULL DEFAULT '[]',
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
    last_used        TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value_json TEXT NOT NULL DEFAULT 'null',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- DOWN --

DROP TABLE IF EXISTS settings;
DROP TABLE IF EXISTS workspaces;
DROP TABLE IF EXISTS study_progress;
DROP TABLE IF EXISTS bookmarks;
DROP TABLE IF EXISTS revision_history;
DROP TABLE IF EXISTS verification_records;
DROP TABLE IF EXISTS calculation_runs;
DROP TABLE IF EXISTS calculations;
DROP TABLE IF EXISTS procedures;
DROP TABLE IF EXISTS rules;
DROP TABLE IF EXISTS record_tags;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS record_relations;
DROP TABLE IF EXISTS record_fts;
DROP TABLE IF EXISTS knowledge_records;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS doc_fts;
DROP TABLE IF EXISTS doc_chunks;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS modules;
DROP TABLE IF EXISTS schema_migrations;

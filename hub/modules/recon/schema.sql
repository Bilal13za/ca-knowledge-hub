-- CA Knowledge Hub — reconciliation module schema (Phase 5).
-- All tables recon_-prefixed. Original imported data is preserved
-- verbatim in recon_datasets.rows_json; findings carry resolutions.

CREATE TABLE IF NOT EXISTS recon_runs (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'other'
                 CHECK (kind IN ('bank','supplier','customer','gl',
                                 'inventory','payroll','tax','other')),
    label_a      TEXT NOT NULL DEFAULT 'A',
    label_b      TEXT NOT NULL DEFAULT 'B',
    mapping_json TEXT NOT NULL DEFAULT '{}',
    summary_json TEXT NOT NULL DEFAULT '{}',
    status       TEXT NOT NULL DEFAULT 'open'
                 CHECK (status IN ('open','reviewed','closed')),
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recon_datasets (
    id           INTEGER PRIMARY KEY,
    run_id       INTEGER NOT NULL REFERENCES recon_runs(id) ON DELETE CASCADE,
    side         TEXT NOT NULL CHECK (side IN ('a','b')),
    filename     TEXT,
    columns_json TEXT NOT NULL DEFAULT '[]',
    rows_json    TEXT NOT NULL DEFAULT '[]',
    row_count    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recon_findings (
    id              INTEGER PRIMARY KEY,
    run_id          INTEGER NOT NULL REFERENCES recon_runs(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK (severity IN ('error','warning','info')),
    message         TEXT NOT NULL,
    row_ref         INTEGER,
    column_name     TEXT,
    details_json    TEXT NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','resolved','ignored')),
    resolution_note TEXT,
    resolved_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_recon_findings_run ON recon_findings(run_id, status);

-- CA Knowledge Hub — FS analysis module schema (Phase 8).
-- Saved analyses with their inputs (reproducible); findings are derived,
-- never stored as conclusions.

CREATE TABLE IF NOT EXISTS fs_runs (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'ratios'
                CHECK (kind IN ('ratios','trends','common_size','working_capital')),
    inputs_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

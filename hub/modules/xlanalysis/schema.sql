-- CA Knowledge Hub — data-analysis module schema (Phase 6).
-- Stores analysis recipes (for reproducibility) and result summaries.
-- Source datasets are Bilal's own files, re-imported per run.

CREATE TABLE IF NOT EXISTS xla_runs (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    operation    TEXT NOT NULL
                 CHECK (operation IN ('clean','variance','summary',
                                     'calculated','exceptions')),
    recipe_json  TEXT NOT NULL DEFAULT '{}',
    summary_json TEXT NOT NULL DEFAULT '{}',
    output_path  TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

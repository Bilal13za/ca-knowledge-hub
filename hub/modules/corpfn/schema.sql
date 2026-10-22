-- CA Knowledge Hub — corpfn module schema (Phase 10).

CREATE TABLE IF NOT EXISTS cf_runs (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    kind       TEXT NOT NULL      -- npv | irr | payback | capm | wacc |
                                  -- gordon | sensitivity
               CHECK (kind IN ('npv','irr','payback','capm','wacc',
                               'gordon','sensitivity')),
    inputs_json  TEXT NOT NULL,
    result_json  TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cf_runs_kind ON cf_runs(kind, id);

-- CA Knowledge Hub — study module schema (Phase 14).
-- Study Mode: SM-2 flashcards, question bank, revision planner.
-- Content pack (Bilal's personal study data) is seeded from
-- modules/study/data/content_pack.json — private to his install.

CREATE TABLE IF NOT EXISTS study_decks (
    id          TEXT PRIMARY KEY,   -- e.g. 'capttax-ch02'
    name        TEXT NOT NULL,
    source      TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS study_cards (
    id          INTEGER PRIMARY KEY,
    deck_id     TEXT NOT NULL REFERENCES study_decks(id),
    front       TEXT NOT NULL,
    back        TEXT NOT NULL,
    chapter_ref TEXT,
    page_ref    TEXT,
    source_ref  TEXT
);
CREATE INDEX IF NOT EXISTS idx_study_cards_deck ON study_cards(deck_id);

-- SM-2 review state, one row per card (created on first review).
CREATE TABLE IF NOT EXISTS study_reviews (
    card_id       INTEGER PRIMARY KEY REFERENCES study_cards(id),
    ease          REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    reps          INTEGER NOT NULL DEFAULT 0,
    lapses        INTEGER NOT NULL DEFAULT 0,
    next_due      TEXT,              -- ISO date
    last_reviewed TEXT,
    last_rating   TEXT
);
CREATE INDEX IF NOT EXISTS idx_study_reviews_due ON study_reviews(next_due);

CREATE TABLE IF NOT EXISTS study_questions (
    id           TEXT PRIMARY KEY,
    deck_id      TEXT REFERENCES study_decks(id),
    number       TEXT,
    statement    TEXT NOT NULL,
    solution     TEXT,
    has_solution INTEGER NOT NULL DEFAULT 0,
    page_ref     TEXT,
    source_ref   TEXT
);

CREATE TABLE IF NOT EXISTS study_attempts (
    id          INTEGER PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES study_questions(id),
    correct     INTEGER NOT NULL DEFAULT 0,  -- self-marked 0/1
    notes       TEXT,
    attempted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS study_plans (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    exam_date     TEXT NOT NULL,     -- ISO date
    hours_per_day REAL NOT NULL DEFAULT 1.0,
    study_days    TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS study_plan_items (
    id            INTEGER PRIMARY KEY,
    plan_id       INTEGER NOT NULL REFERENCES study_plans(id)
                  ON DELETE CASCADE,
    activity_date TEXT NOT NULL,     -- ISO date
    activity_type TEXT NOT NULL,     -- read | flashcards | questions | review
    title         TEXT NOT NULL,
    minutes       INTEGER NOT NULL DEFAULT 30,
    done          INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_study_plan_items ON
    study_plan_items(plan_id, activity_date);

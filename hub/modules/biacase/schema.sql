-- CA Knowledge Hub — BIA/BFD case analysis module schema (Phase 7).
-- Ported from the standalone case engine; all tables case_-prefixed.
-- Source FTS tables/triggers dropped: global search uses
-- knowledge_records stubs like every other module.

-- ============================================================================
-- ICAP Business Case Analysis and Decision Engine — database schema
-- SQLite + FTS5. Schema version 1.
-- Conventions: stdlib JSON only (no YAML); Decimal-safe app layer; seed data is
-- upserted with INSERT OR REPLACE and MUST never touch student tables
-- (StudentAttempts, MistakeLog).
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- Papers ---
CREATE TABLE IF NOT EXISTS case_papers (
    paper_id            TEXT PRIMARY KEY,
    code                TEXT,
    title               TEXT,
    scheme              TEXT,
    competency          TEXT,
    teaching_hours      TEXT,
    verification_status TEXT,
    official_source     TEXT,
    effective_date      TEXT,
    notes               TEXT
);

-- ------------------------------------------------------- SyllabusVersions ---
CREATE TABLE IF NOT EXISTS case_syllabus_versions (
    version_id          TEXT PRIMARY KEY,
    paper_id            TEXT REFERENCES case_papers(paper_id),
    scheme              TEXT,
    version_label       TEXT,
    effective_date      TEXT,
    source_url          TEXT,
    verification_status TEXT,
    notes               TEXT
);

-- ------------------------------------------------------ LearningOutcomes ---
CREATE TABLE IF NOT EXISTS case_learning_outcomes (
    lo_id               TEXT PRIMARY KEY,
    paper_id            TEXT REFERENCES case_papers(paper_id),
    syllabus_ref        TEXT,
    description         TEXT,
    proficiency_level   TEXT,
    testing_level       TEXT,
    verification_status TEXT,
    official_source     TEXT,
    effective_date      TEXT,
    review_status       TEXT
);

-- --------------------------------------------------------------- Topics ---
CREATE TABLE IF NOT EXISTS case_topics (
    topic_id            TEXT PRIMARY KEY,
    paper_id            TEXT REFERENCES case_papers(paper_id),
    syllabus_ref        TEXT,
    title               TEXT,
    weightage           TEXT,
    parent_topic_id     TEXT REFERENCES case_topics(topic_id),
    verification_status TEXT,
    official_source     TEXT,
    effective_date      TEXT
);

-- -------------------------------------------------------------- Concepts ---
CREATE TABLE IF NOT EXISTS case_concepts (
    concept_id          TEXT PRIMARY KEY,
    name                TEXT,
    definition          TEXT,
    paper_id            TEXT REFERENCES case_papers(paper_id),
    topic_ref           TEXT,
    verification_status TEXT,
    source_ref          TEXT,
    review_status       TEXT
);

-- ------------------------------------------------------------ Frameworks ---
CREATE TABLE IF NOT EXISTS case_frameworks (
    framework_id          TEXT PRIMARY KEY,
    name                  TEXT,
    definition            TEXT,
    purpose               TEXT,
    appropriate_situations TEXT,
    required_inputs       TEXT,
    limitations           TEXT,
    common_mistakes       TEXT,
    example               TEXT,
    related_topics        TEXT,
    verification_status   TEXT,
    source_ref            TEXT,
    review_status         TEXT
);

CREATE TABLE IF NOT EXISTS case_framework_steps (
    step_id      TEXT PRIMARY KEY,
    framework_id TEXT REFERENCES case_frameworks(framework_id),
    step_no      INTEGER,
    title        TEXT,
    description  TEXT,
    formula      TEXT
);

-- ---------------------------------------------------------- CasePatterns ---
CREATE TABLE IF NOT EXISTS case_patterns (
    case_id            TEXT PRIMARY KEY,
    title              TEXT,
    paper_code         TEXT,
    topic_ref          TEXT,
    business_context   TEXT,
    industry           TEXT,
    company_size       TEXT,
    case_facts         TEXT,
    main_issue         TEXT,
    secondary_issues   TEXT,
    decision_to_make   TEXT,
    relevant_concepts  TEXT,
    possible_frameworks TEXT,
    quantitative_info  TEXT,
    qualitative_info   TEXT,
    missing_info       TEXT,
    constraints        TEXT,
    stakeholders       TEXT,
    alternatives       TEXT,
    evaluation_criteria TEXT,
    source_basis       TEXT,
    review_status      TEXT,
    verification_status TEXT
);

CREATE TABLE IF NOT EXISTS case_facts (
    fact_id           TEXT PRIMARY KEY,
    case_id           TEXT REFERENCES case_patterns(case_id),
    wording           TEXT,
    normalised        TEXT,
    source_location   TEXT,
    classification    TEXT,
    related_issue     TEXT,
    related_framework TEXT,
    verified_or_assumed TEXT
);

-- ------------------------------------------------------- ProblemPatterns ---
CREATE TABLE IF NOT EXISTS case_problem_patterns (
    pattern_id  TEXT PRIMARY KEY,
    name        TEXT,
    description TEXT,
    indicators  TEXT
);

CREATE TABLE IF NOT EXISTS case_trigger_rules (
    rule_id                TEXT PRIMARY KEY,
    pattern_id             TEXT REFERENCES case_problem_patterns(pattern_id),
    title                  TEXT,
    triggers_json          TEXT,
    required_conditions    TEXT,
    interpretation         TEXT,
    alternative_explanations TEXT,
    info_needed            TEXT,
    relevant_concepts      TEXT,
    recommended_analysis   TEXT,
    rule_source            TEXT,
    review_status          TEXT
);

CREATE TABLE IF NOT EXISTS case_rule_framework_mappings (
    map_id       TEXT PRIMARY KEY,
    rule_id      TEXT REFERENCES case_trigger_rules(rule_id),
    framework_id TEXT REFERENCES case_frameworks(framework_id),
    rationale    TEXT
);

-- --------------------------------------------------------------- Formulas ---
CREATE TABLE IF NOT EXISTS case_formulas (
    formula_id          TEXT PRIMARY KEY,
    calc_id             TEXT,
    name                TEXT,
    formula_text        TEXT,
    inputs_json         TEXT,
    units_json          TEXT,
    assumptions         TEXT,
    limitations         TEXT,
    verification_status TEXT,
    validation_status   TEXT,
    review_status       TEXT
);

CREATE TABLE IF NOT EXISTS case_calculation_examples (
    example_id   TEXT PRIMARY KEY,
    formula_id   TEXT REFERENCES case_formulas(formula_id),
    inputs_json  TEXT,
    steps_json   TEXT,
    result_text  TEXT,
    interpretation TEXT
);

-- -------------------------------------------------------- DecisionOptions ---
CREATE TABLE IF NOT EXISTS case_decision_options (
    option_id             TEXT PRIMARY KEY,
    case_id               TEXT REFERENCES case_patterns(case_id),
    description           TEXT,
    financial_impact      TEXT,
    nonfinancial_benefits TEXT,
    costs                 TEXT,
    risks                 TEXT,
    time_requirements     TEXT,
    resource_requirements TEXT,
    stakeholder_effects   TEXT,
    strategic_alignment   TEXT,
    legal_constraints     TEXT,
    assumptions           TEXT,
    evidence              TEXT
);

CREATE TABLE IF NOT EXISTS case_evaluation_criteria (
    criterion_id   TEXT PRIMARY KEY,
    case_id        TEXT REFERENCES case_patterns(case_id),
    name           TEXT,
    description    TEXT,
    weight         REAL,
    criterion_type TEXT
);

-- ------------------------------------------------------ PracticeQuestions ---
CREATE TABLE IF NOT EXISTS case_practice_questions (
    question_id            TEXT PRIMARY KEY,
    paper_code             TEXT,
    topic_ref              TEXT,
    syllabus_ref           TEXT,
    question_text          TEXT,
    difficulty             TEXT,
    marks                  INTEGER,
    suggested_minutes      INTEGER,
    required_skills        TEXT,
    expected_answer_elements TEXT,
    calculation_requirements TEXT,
    common_mistakes        TEXT,
    source_verified        INTEGER,
    source_note            TEXT,
    verification_status    TEXT
);

CREATE TABLE IF NOT EXISTS case_answer_outlines (
    outline_id   TEXT PRIMARY KEY,
    question_id  TEXT REFERENCES case_practice_questions(question_id),
    outline_text TEXT,
    note         TEXT
);

CREATE TABLE IF NOT EXISTS case_marking_rubrics (
    rubric_id   TEXT PRIMARY KEY,
    question_id TEXT REFERENCES case_practice_questions(question_id),
    rubric_json TEXT,
    note        TEXT
);

-- ---------------------------------------------------------------- Sources ---
CREATE TABLE IF NOT EXISTS case_sources (
    source_id     TEXT PRIMARY KEY,
    citation      TEXT,
    url           TEXT,
    accessed_date TEXT,
    kind          TEXT
);

-- ---------------------------------------------------------- ReviewRecords ---
CREATE TABLE IF NOT EXISTS case_review_records (
    review_id   TEXT PRIMARY KEY,
    entity_type TEXT,
    entity_id   TEXT,
    reviewer    TEXT,
    review_date TEXT,
    status      TEXT,
    notes       TEXT
);

-- ============================================================ STUDENT TABLES
-- Seed code MUST NEVER insert into, update, or delete from these tables.
-- ============================================================
CREATE TABLE IF NOT EXISTS case_student_attempts (
    attempt_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id    TEXT,
    attempted_at   TEXT,
    time_taken_min REAL,
    marks_self     REAL,
    checklist_json TEXT,
    answer_text    TEXT,
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS case_mistake_log (
    mistake_id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER REFERENCES case_student_attempts(attempt_id),
    topic      TEXT,
    description TEXT,
    created_at TEXT,
    resolved   INTEGER DEFAULT 0
);

-- ---------------------------------------------------------- SchemaVersion ---

-- ================================================================== INDEXES
CREATE INDEX IF NOT EXISTS idx_lo_paper      ON case_learning_outcomes(paper_id);
CREATE INDEX IF NOT EXISTS idx_topics_paper  ON case_topics(paper_id);
CREATE INDEX IF NOT EXISTS idx_concepts_paper ON case_concepts(paper_id);
CREATE INDEX IF NOT EXISTS idx_steps_fw      ON case_framework_steps(framework_id);
CREATE INDEX IF NOT EXISTS idx_facts_case     ON case_facts(case_id);
CREATE INDEX IF NOT EXISTS idx_rules_pattern  ON case_trigger_rules(pattern_id);
CREATE INDEX IF NOT EXISTS idx_map_rule       ON case_rule_framework_mappings(rule_id);
CREATE INDEX IF NOT EXISTS idx_map_fw         ON case_rule_framework_mappings(framework_id);
CREATE INDEX IF NOT EXISTS idx_examples_formula ON case_calculation_examples(formula_id);
CREATE INDEX IF NOT EXISTS idx_options_case   ON case_decision_options(case_id);
CREATE INDEX IF NOT EXISTS idx_criteria_case  ON case_evaluation_criteria(case_id);
CREATE INDEX IF NOT EXISTS idx_q_paper        ON case_practice_questions(paper_code);

-- ============================================================ FTS5 TABLES
-- Kept in sync by triggers below; seed.py also performs a full rebuild.



-- ------------------------------------------------- FTS sync triggers ---









-- ------------------------------------------------------------- Study aids --
-- Flashcards are generated deterministically from Frameworks, Formulas and
-- TriggerRules (tools/gen_study_aids.py); each card inherits its source
-- row's verification_status. FlashcardProgress is a STUDENT table: seed.py
-- and init_db() must never write to it.
CREATE TABLE IF NOT EXISTS case_flashcards (
    card_id            TEXT PRIMARY KEY,
    deck               TEXT,
    front              TEXT NOT NULL,
    back               TEXT NOT NULL,
    framework_id       TEXT REFERENCES case_frameworks(framework_id),
    formula_id         TEXT REFERENCES case_formulas(formula_id),
    rule_id            TEXT REFERENCES case_trigger_rules(rule_id),
    topic              TEXT,
    paper_code         TEXT,
    card_type          TEXT,
    verification_status TEXT,
    official_source    TEXT
);
CREATE INDEX IF NOT EXISTS idx_cards_deck ON case_flashcards(deck);
CREATE INDEX IF NOT EXISTS idx_cards_fw   ON case_flashcards(framework_id);

CREATE TABLE IF NOT EXISTS case_flashcard_progress (
    card_id    TEXT PRIMARY KEY REFERENCES case_flashcards(card_id),
    status     TEXT,   -- 'known' | 'unsure'
    reps       INTEGER NOT NULL DEFAULT 0,
    last_seen  TEXT
);

-- Mind-map catalogue: one row per map; leaf text is resolved from the
-- Frameworks/FrameworkSteps rows at render time (single source of truth).
CREATE TABLE IF NOT EXISTS case_mindmaps (
    map_id              TEXT PRIMARY KEY,
    framework_id        TEXT REFERENCES case_frameworks(framework_id),
    title               TEXT,
    branch_order_json   TEXT,
    verification_status TEXT,
    source_ref          TEXT
);

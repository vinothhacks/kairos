PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL DEFAULT (datetime('now')),
    task         TEXT NOT NULL,
    technique    TEXT NOT NULL,
    selected_by  TEXT NOT NULL,
    selector_score REAL,
    status       TEXT NOT NULL,
    duration_ms  INTEGER,
    cost_tokens  INTEGER,
    answer_path  TEXT,
    trace_path   TEXT,
    error_msg    TEXT
);

CREATE INDEX IF NOT EXISTS runs_ts_idx ON runs(ts);
CREATE INDEX IF NOT EXISTS runs_technique_idx ON runs(technique);

CREATE TABLE IF NOT EXISTS feedback (
    run_id   INTEGER NOT NULL,
    rating   INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    note     TEXT,
    ts       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (run_id, ts),
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS wiki_index (
    slug      TEXT PRIMARY KEY,
    type      TEXT NOT NULL,
    file      TEXT NOT NULL,
    title     TEXT NOT NULL,
    has_runner INTEGER NOT NULL DEFAULT 0,
    confidence TEXT NOT NULL,
    updated   TEXT NOT NULL,
    word_count INTEGER NOT NULL DEFAULT 0,
    last_seen_ts TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS wiki_index_type_idx ON wiki_index(type);

CREATE TABLE IF NOT EXISTS wiki_relations (
    from_slug TEXT NOT NULL,
    to_slug   TEXT NOT NULL,
    kind      TEXT NOT NULL,
    PRIMARY KEY (from_slug, to_slug, kind),
    FOREIGN KEY (from_slug) REFERENCES wiki_index(slug) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS wiki_relations_to_idx ON wiki_relations(to_slug);

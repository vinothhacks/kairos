# 0002 — Data model

> Status: Accepted. Decision date: 2026-05-10.

## Context

Kairos has three storage layers:

1. **`raw/`** — immutable user files. We never modify these.
2. **`wiki/`** — markdown the LLM owns. The source of truth for knowledge.
3. **`kairos.db`** — local SQLite for state (runs, feedback, derived indices, relations).

This document specifies the SQLite schema for v0.1. Postgres bridge mirrors the same shape with `bigserial` instead of `integer pk autoincrement`.

## Schema (v0.1)

```sql
-- src/kairos/memory/schema.sql

PRAGMA foreign_keys = ON;

-- one row per `kairos run` invocation
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL DEFAULT (datetime('now')),
    task         TEXT NOT NULL,
    technique    TEXT NOT NULL,         -- 'rag' | 'react' | 'reflexion' | 'auto'
    selected_by  TEXT NOT NULL,         -- 'user' | 'selector'
    selector_score REAL,                -- 0..1, null if user-selected
    status       TEXT NOT NULL,         -- 'ok' | 'timeout' | 'error'
    duration_ms  INTEGER,
    cost_tokens  INTEGER,               -- cumulative across all llm-mcp calls (estimate)
    answer_path  TEXT,                  -- relative path to outputs/run-<id>/answer.md
    trace_path   TEXT,                  -- relative path to outputs/run-<id>/trace.jsonl
    error_msg    TEXT
);

CREATE INDEX IF NOT EXISTS runs_ts_idx ON runs(ts);
CREATE INDEX IF NOT EXISTS runs_technique_idx ON runs(technique);

-- user feedback per run (1..5 + optional note)
CREATE TABLE IF NOT EXISTS feedback (
    run_id   INTEGER NOT NULL,
    rating   INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    note     TEXT,
    ts       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (run_id, ts),
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

-- derived from wiki/index.md, refreshed on every ingest/lint
CREATE TABLE IF NOT EXISTS wiki_index (
    slug      TEXT PRIMARY KEY,            -- 'rag', 'react', 'rag-vs-reflexion'
    type      TEXT NOT NULL,               -- 'concept' | 'source' | 'comparison'
    file      TEXT NOT NULL,               -- relative path: 'wiki/concepts/rag.md'
    title     TEXT NOT NULL,
    has_runner INTEGER NOT NULL DEFAULT 0, -- 0 = doc-only, 1 = built-in runner
    confidence TEXT NOT NULL,              -- 'high' | 'medium' | 'low' (frontmatter)
    updated   TEXT NOT NULL,               -- ISO date from frontmatter
    word_count INTEGER NOT NULL DEFAULT 0,
    last_seen_ts TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS wiki_index_type_idx ON wiki_index(type);

-- inferred from [[wikilinks]] across pages, used by lint and selector
CREATE TABLE IF NOT EXISTS wiki_relations (
    from_slug TEXT NOT NULL,
    to_slug   TEXT NOT NULL,
    kind      TEXT NOT NULL,           -- 'related' | 'depends_on' | 'contradicts' | 'supersedes'
    PRIMARY KEY (from_slug, to_slug, kind),
    FOREIGN KEY (from_slug) REFERENCES wiki_index(slug) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS wiki_relations_to_idx ON wiki_relations(to_slug);
```

## Pydantic models that wrap the schema

```python
# src/kairos/memory/models.py
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class Run(BaseModel):
    id: int | None = None
    ts: datetime
    task: str
    technique: Literal["rag", "react", "reflexion", "auto"]
    selected_by: Literal["user", "selector"]
    selector_score: float | None = None
    status: Literal["ok", "timeout", "error"]
    duration_ms: int | None = None
    cost_tokens: int | None = None
    answer_path: str | None = None
    trace_path: str | None = None
    error_msg: str | None = None


class Feedback(BaseModel):
    run_id: int
    rating: int = Field(ge=1, le=5)
    note: str | None = None
    ts: datetime


class WikiIndexEntry(BaseModel):
    slug: str
    type: Literal["concept", "source", "comparison"]
    file: str
    title: str
    has_runner: bool = False
    confidence: Literal["high", "medium", "low"]
    updated: datetime
    word_count: int = 0
    last_seen_ts: datetime


class WikiRelation(BaseModel):
    from_slug: str
    to_slug: str
    kind: Literal["related", "depends_on", "contradicts", "supersedes"]
```

## Migration strategy

- v0.1 has no migrations — `kairos.db` is created from `schema.sql` on first run.
- Schema version stored in `pragma user_version`.
- Future migrations live at `src/kairos/memory/migrations/NNNN_<name>.sql` and are applied in order.

## Why not embed-store?

Karpathy's gist explicitly says "the index file is enough at moderate scale (~100 sources, hundreds of pages)" before you need a search engine. v0.1 stays at index lookup. v0.2 may add an optional `qmd` integration or a local sqlite-vec table.

## Privacy

- `kairos.db` lives in the project directory by default (`./.kairos/kairos.db`).
- A global mode (`kairos --global`) puts it at `~/.kairos/kairos.db`.
- No telemetry. No phone-home. No API keys to leak (we have none — `llm-mcp` does the auth).

# Upgrading kairos

This page covers in-place upgrades between minor releases. The TL;DR for v0.1.x → v0.2.0: nothing breaks. New behaviour activates on first run.

---

## v0.1.x -> v0.2.0

**No migration required.** All v0.1 CLI args, env vars, and on-disk formats still work. The first `kairos run` (or `kairos lint`) after upgrading will:

- Backfill `wiki_index` and `wiki_relations` from your existing `wiki/` tree.
- Apply `journal_mode=WAL` + `busy_timeout=5000` PRAGMAs to your existing `kairos.db`.
- Start writing to the new `feedback` table when you call `kairos feedback`.

You can keep using your v0.1 wiki, your v0.1 source files, and your v0.1 `outputs/run-*` folders. Nothing is rewritten.

### What's new (worth knowing)

| Feature | How to use it |
|---|---|
| **`.kairos/config.toml`** (KAI-004) | `[llm] backend = "stub"`, `[wiki] stale_after_days = 90`, `[selector] default_technique = "rag"`. CLI env vars still win over file values. |
| **`KAIROS_DB_HOME`** (KAI-018) | Set the env var to a folder; `kairos.db` lives there instead of `<project>/.kairos/`. Useful for shared wikis. |
| **`kairos doctor`** (KAI-011) | Now actually pings `llm-mcp` with a 2-second timeout. Surfaces red/yellow/green status per backend. |
| **`kairos feedback <run-id> --rating 1-5`** (KAI-035) | New subcommand. Records to `feedback` table. Shows up in `kairos doctor` once we wire that in. |
| **`kairos run --json`** (KAI-034) | Emits the run + trace as a single JSON document for tooling. Replaces the in-memory `RunResult.trace` field. |
| **`kairos run --llm-rerank`** (KAI-020) | Optional flag. When the top-3 candidates are within 0.05 of each other, asks Claude to break the tie. Off by default. |
| **`Runner` ABC + entry-points** (KAI-006) | Third-party packages can register a runner under the `kairos.runners` entry-point group. No fork required. |
| **Retries + backoff** (KAI-017) | `MCPLLMClient` now retries 5xx/connect errors 3 times with exponential backoff. 4xx is never retried. |

### Breaking changes

None. We deliberately kept the v0.1 surface intact. The two changes that *could* break a custom integration are:

1. **`RunResult.trace` field removed** (KAI-034). Read the JSONL trace from `result.trace_path` instead, or pass `kairos run --json` and read the `trace` array. Internal callers do this automatically; the only places that broke would be third-party scripts importing `kairos.runners.base.RunResult` and reading `.trace` directly.
2. **`runs.duration_ms` is now `REAL`, not `INTEGER`** (KAI-042). SQLite is happy to read either; Python sees a `float` instead of an `int`. If you cast it manually somewhere, drop the cast.

### What was retired

- The **`postgres` extra** in `pyproject.toml` (KAI-036). It was never wired through. We'll bring proper Postgres support back in v0.3 when we ship the multi-tenant wiki.
- The **`pytest-asyncio`** dev dependency (KAI-040). No async tests today.
- The internal **`fallback_slug` parameter** on `_parse_plan_json` (KAI-039). Always was unused.

### If something breaks

1. `git stash` your wiki, run `kairos init --force <path>` to lay down a fresh schema. KAI-001 ensures your old `AGENTS.md`, `index.md`, and `log.md` are saved as `.bak.<timestamp>` siblings before being overwritten.
2. File a bug at https://github.com/vinothhacks/kairos/issues with the `kairos doctor` output and a one-line repro.

---

## Earlier upgrades

- **v0.1.0 -> v0.1.1**: bug-fix release; no migration.

# Changelog

All notable changes to `kairos` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-11

The audit-fix release. We ran a full internal audit of v0.1.1 against the README, architecture doc, and runtime behavior, opened 45 findings, and closed every single one. v0.2.0 also implements seven features that v0.1 documented but didn't actually deliver. **Zero breaking changes.** See [`docs/UPGRADING.md`](docs/UPGRADING.md) for the migration walkthrough.

### Added (the 7 promised-but-missing features)
- **`.kairos/config.toml` parser** (KAI-004). Project-local config for backend, mcp_url, stale_after_days, default_technique, and arbitrary `[sources]` entries. Resolution order: env > file > defaults. Surfaced in `kairos doctor`.
- **Real `wiki_index` + `wiki_relations` write paths** (KAI-005). `WikiIndexer` upserts page metadata + outgoing links on every ingest / lint / save-to-wiki query. Selector + query consume the cache (KAI-021), falling back to a filesystem walk only when the cache is empty or stale.
- **`Runner` ABC + plugin discovery** (KAI-006). `class Runner(ABC)` with `applicable(task)` and `run(...)` contract; `runners.dispatch` discovers third-party runners via `entry_points(group="kairos.runners")`. `pip install kairos-runner-tot` lands without forking.
- **`kairos feedback <run-id> --rating 1..5 --note "..."`** (KAI-035). Inserts into the previously-dead `feedback` table.
- **`MCPLLMClient` retries + exponential backoff** (KAI-017). 3 attempts, 0.5s base + jitter; classifies 5xx + connect errors as transient, 4xx as permanent.
- **Real `kairos doctor` MCP probe** (KAI-011). Fires a `ping` tool call with a 2-second timeout instead of hard-coding "ok".
- **Optional `kairos run --llm-rerank`** (KAI-020). When set AND the top-3 candidates are within 0.05 of the leader, asks Claude to break the tie. Off by default; pure rule-based selector remains the offline-friendly path.

### Added (other v0.2 surfaces)
- **`KAIROS_DB_HOME` env var** (KAI-018). Relocate `kairos.db` outside the repo. Default stays `<project>/.kairos/kairos.db`.
- **`kairos run --json`** (KAI-034). Structured output with run metadata + inlined trace events for tool integration.
- **`kairos init --force` backups** (KAI-001). `AGENTS.md`, `index.md`, `log.md` are saved as `*.bak.<UTC-timestamp>` siblings before being overwritten. Reported in CLI output and exposed on `InitResult.backups`.
- **WAL + busy_timeout SQLite pragmas** (KAI-022). Multi-process safe; concurrent runs no longer trample.
- **Hash-aware re-ingest** (KAI-002). Same-bytes input is a no-op; different-bytes input writes `<name>_2.md` instead of clobbering `raw/articles/<name>.md`.
- **Slug-collision counter for sources** (KAI-003). Two distinct raw files with the same fallback slug get `slug.md`, `slug-2.md`, `slug-3.md` ... no overwrite.
- **Preserve `created` date on re-ingest** (KAI-024). Existing source pages keep their original `created` value when their summary is regenerated.
- **5MB per-file guard in RAG** (KAI-044). Skips pathologically large markdown dumps with a yellow stderr warning.
- **Top-N selector tie-break** (KAI-029). Promotes the safe default (`rag`) when any of the top-3 candidates is within 0.05 of the leader.
- **Segment-match slug scoring** (KAI-028). `"rag"` no longer accidentally hits inside slugs like `imagery-tools` or `garage`.
- **Stub-leak fix** (KAI-026). `StubLLMClient` default reply is generic; tests can no longer leak prompt content via the stub path.
- **Lint LLM provenance** (KAI-010). Findings tagged `local` vs `llm`; LLM findings naming non-existent pages are dropped; report renders separate sections for the two.
- **CI: pip-audit step** (KAI-013), **pytest-cov reports** (Phase 6), **README demo drift check** (KAI-014), **mypy on `tests/`** (KAI-041).
- 7 new test files, 88 tests total (was 48). 6 critical-flag regressions caught. New integration suite uses `httpx.MockTransport` with no network.

### Changed
- `RunResult.duration_ms` is now `float` (KAI-042); SQLite column is `REAL`.
- `RunResult.trace` field removed (KAI-034); read the JSONL trace from `result.trace_path` or use `kairos run --json`.
- `kairos query` writes `[[wikilinks]]` to stdout untouched (KAI-007); Rich's bracket parser is bypassed via `markup=False`.
- `kairos run "auto"` records the *real* selector telemetry (KAI-008) so `runs.selected_by="selector"` and `runs.selector_score IS NOT NULL` for auto-routed runs.
- `kairos query --save-to-wiki` filenames now include the date and a counter (KAI-012). Two queries on the same day no longer clobber each other.
- `MCPLLMClient` errors raise `LLMError` (or its subclass `MCPUnreachable`); CLI catches the parent class for consistent UX (KAI-009).
- YAML frontmatter parsing coerces booleans like `no` and `off` back to lowercase strings in `sources` and `related` lists (KAI-016).
- Frontmatter regex tolerates files without a trailing newline (KAI-025).
- Lint pipeline split into four helpers (KAI-027): `_collect_pages_and_links`, `_local_findings`, `_llm_findings`, `_render_report`. Each is unit-testable in isolation.
- Selector + query warn on stderr when a malformed page is skipped (KAI-033) instead of failing silent.
- README install URLs pinned to `v0.2.0` (KAI-043) for reproducible scripts.
- Architecture doc rewritten to match v0.2 reality; aspirational items moved under `## v0.3+ surfaces` (KAI-019, KAI-037).
- Em-dashes removed from CLI help text and module docstrings (KAI-038).

### Removed
- The `[postgres]` extra in `pyproject.toml` (KAI-036). Postgres support deferred to v0.3 when the multi-tenant wiki design lands.
- The `pytest-asyncio` dev dependency (KAI-040). No async tests today.
- The internal `fallback_slug` parameter on `_parse_plan_json` (KAI-039). Always was unused.

### Audit numbers
- 45 findings closed (6 Critical, 14 High, 16 Medium, 7 Low, 2 Info)
- 88 tests pass (was 48). 1 integration test (`test_concurrent_runs`) opt-out'd from the autouse stub fixture.
- ruff + mypy strict clean across `src/` AND `tests/`. 77% line coverage.
- `kairos lint` against own seed wiki returns 0 findings.
- All 5 e2e scripts pass on Windows + Git for Windows bash.

## [0.1.1] - 2026-05-10

Polish pass driven by dogfood ingest of 13 real-world markdown sources and a side-by-side review against `jcode`'s README.

### Added
- Quick-link nav row under the README hero (Install / Demo / Why / Quickstart / How it works / Commands / Roadmap) for one-click jumping in long-scroll viewers.
- `docs/launch/linkedin.md` launch kit (drafts only, never auto-posted): single-image launch post, 8-slide carousel script, 5-connection + 3-comment engagement plan, posting cadence, "what if it flops" recovery plan.

### Changed
- Removed broken `assets/demo.gif` reference from README. The 30-second demo block already serves as the visual demo. A real asciinema-recorded GIF will land in v0.2 once `scripts/record-demo.sh` is run end-to-end with the live MCP backend.
- Replaced one inline em-dash with a colon in the `30-second demo` follow-up sentence to keep the README consistent with the project's "no em-dashes in marketing copy" rule (em-dashes in code/log/lint output remain unchanged).

### Validated (no code changes; recorded for the v0.2 baseline)
- Dogfood: 13 real-world markdown sources from this monorepo (llm-mcp README, EXTENSIONS_NEEDED, karpathy-guidelines, skills/_inventory, runtime/runner, runtime/schema, 3 agent personas, 2 input style guides, kairos PRD, kairos architecture) ingested cleanly via `kairos ingest` with `KAIROS_LLM_BACKEND=stub`. 13 / 13 pass; 0 crashes; 0 frontmatter validation errors.
- `kairos lint` after dogfood: 0 findings on 34 pages (21 seed + 13 ingested source summaries).
- 48 unit tests still green; 5 e2e shell scripts still green.

## [0.1.0] - 2026-05-10

The first release. The minimum surface that proves the wedge: an LLM Wiki that picks the right technique and runs it.

### Added
- `kairos init` — bootstraps `AGENTS.md`, `raw/`, `wiki/`, `outputs/`, and copies a 21-page seed wiki into `wiki/concepts/`.
- `kairos ingest <source>` — reads a raw file, asks the LLM to propose new + updated wiki pages, applies the diff, and logs the operation.
- `kairos query "<question>"` — lexical search over the wiki, LLM synthesis with `[[wikilink]]` citations.
- `kairos lint` — local pass (orphans, missing concepts, stale pages, dominant sources) + LLM pass (contradictions, drift, gaps). Writes a dated report to `outputs/`.
- `kairos run "<task>"` — rule-based technique selector (keyword boost + lexical overlap) picks one of `rag`, `react`, `reflexion`, then dispatches to the runner. Logs every run to `.kairos/kairos.db`.
- `kairos doctor` — env diagnostics: paths, llm-mcp reachability, schema validity, version.
- 21 seed concept pages: rag, react, reflexion, chain-of-thought, tree-of-thoughts, self-consistency, self-refine, constitutional-ai, plan-and-execute, few-shot-prompting, zero-shot-prompting, function-calling, tool-use, prompt-injection, embedding-search, hybrid-search, hyde, rerank, router-agent, memory-buffer, llm-wiki.
- 3 runner-backed techniques: RAG (lexical chunking + ChatGPT synthesis), ReAct (Thought/Action/Observation loop with `search_web` and `read_file` tools), Reflexion (3-stage handoff: ChatGPT draft → Claude critique → ChatGPT revise).
- SQLite-backed run + feedback persistence (`.kairos/kairos.db`).
- Stub LLM client for deterministic, offline unit tests.
- 48 unit tests covering schema, init, ingest, query, lint, runners, selector, MCP client, and DB.
- Hatchling-based wheel build with `kairos/_seed/` bundled.
- Install scripts (`install.sh`, `install.ps1`) and PyPI publish under `kairos-agent`.

### Notes
- Every model call routes through [llm-mcp](https://github.com/vinothhacks/llm-mcp). No API keys required at any point.
- The `--fix` flag on `lint` is a v0.2 placeholder; v0.1 is report-only.
- Postgres backend is optional and off by default; v0.1 is SQLite-only in practice.

[0.2.0]: https://github.com/vinothhacks/kairos/releases/tag/v0.2.0
[0.1.1]: https://github.com/vinothhacks/kairos/releases/tag/v0.1.1
[0.1.0]: https://github.com/vinothhacks/kairos/releases/tag/v0.1.0

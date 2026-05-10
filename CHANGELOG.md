# Changelog

All notable changes to `kairos` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/vinothhacks/kairos/releases/tag/v0.1.0

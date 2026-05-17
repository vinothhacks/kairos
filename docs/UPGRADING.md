# Upgrading kairos

This page covers in-place upgrades between minor releases. The TL;DR for v0.3.x -> v0.4.0: replace `KAIROS_LLM_BACKEND=mcp` with a direct backend (`ollama`, `openai`, `anthropic`, `openai_compat`, or `stub`).

---

## v0.3.x -> v0.4.0

### Breaking change

`KAIROS_LLM_BACKEND=mcp` was removed. Kairos no longer talks to a separate `llm-mcp` HTTP shim. Use one of:

| Backend | Required env | Optional env |
|---|---|---|
| `stub` | none | `KAIROS_STUB_PATH` |
| `ollama` | local Ollama server | `KAIROS_OLLAMA_URL`, `KAIROS_OLLAMA_MODEL` |
| `openai` | `OPENAI_API_KEY` | `KAIROS_OPENAI_MODEL` |
| `anthropic` | `ANTHROPIC_API_KEY` | `KAIROS_ANTHROPIC_MODEL` |
| `openai_compat` | `KAIROS_LLM_BASE_URL` | `KAIROS_LLM_API_KEY`, `KAIROS_LLM_MODEL` |

Examples:

```bash
export KAIROS_LLM_BACKEND=ollama
export KAIROS_OLLAMA_MODEL=llama3.1

export KAIROS_LLM_BACKEND=openai
export OPENAI_API_KEY=sk-...
```

### MCP clients

Install the optional extra and add `kairos mcp serve` to Cursor, Claude Desktop, or any stdio MCP client:

```bash
pip install "kairos-agent[mcp-server]"
kairos mcp serve
```

See [`MCP.md`](MCP.md) for ready-to-paste client config.

### Worth knowing

| Change | Impact |
|---|---|
| **Default backend is `stub`** | New installs run safely without a network or API key. |
| **Provider retry helper** | HTTP providers share bounded retry/backoff for transient provider errors. |
| **Audit gates are required** | Ruff, mypy, Bandit, `pip-audit`, Radon, Semgrep, MCP smoke, live Ollama, and KAI2 regression reports run in CI. |
| **Installers pin v0.4.0** | `install.ps1` and `install.sh` default to `kairos-agent==0.4.0`. |

---

## v0.2.x -> v0.3.0

**No manual migration required.** Existing wikis keep working. The first `kairos init`, `kairos run`, or `kairos lint` after upgrading may refresh `wiki_index` rows and create a project-specific database subfolder when `KAIROS_DB_HOME` is set.

### Worth knowing

| Change | Impact |
|---|---|
| **Pinned installers** | `install.ps1` and `install.sh` default to `kairos-agent==0.3.0`. Override with `-Version` on PowerShell or `KAIROS_VERSION=...` on sh. |
| **GitHub release hardening** | Release actions are SHA-pinned, publish permissions are job-scoped, and tags must match package versions before build. |
| **Config parser matches docs** | `[wiki] stale_after_days`, `auto_save_query_answers`, `[selector] default_technique`, `require_runner`, and `[sources]` now load. UTF-8 BOM config files are parsed. |
| **Plugin runners are opt-in** | Third-party `kairos.runners` entry points are not imported unless `KAIROS_ENABLE_PLUGINS=1` or `KAIROS_RUNNER_PLUGINS=name1,name2` is set. |
| **JSON output is clean** | `kairos run --json` and `kairos run --json --dry` write JSON only, with no Rich banners. |
| **Read surfaces** | `kairos history` lists recent runs and `kairos feedback-list` lists stored feedback. |
| **Shared DB homes** | `KAIROS_DB_HOME` now stores each project under a short project hash to avoid mixing runs from unrelated wikis. |

### Compatibility notes

- If you intentionally relied on automatic third-party runner imports, set `KAIROS_ENABLE_PLUGINS=1` or allow-list the entry point names.
- If external scripts assumed `KAIROS_DB_HOME/kairos.db`, update them to discover the path through `WikiPaths(root).db` or run `kairos doctor`.

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

# 0001 — Tech stack

> Status: Accepted. Decision date: 2026-05-10. Deciders: vinothhacks (with ChatGPT + Claude consultation).

## Context

Kairos v0.1 ships a Python CLI that:

- reads + writes markdown (the wiki)
- talks to a running `llm-mcp` server (HTTP / MCP / stdio)
- persists run state in a small local DB
- ships pretty Rich output, `--help` text, an install one-liner
- runs on macOS, Linux, Windows

We need to pick the foundational packages **once** and stop re-litigating them.

## Decision

| Concern | Choice | Why |
|---|---|---|
| Language | **Python 3.11+** | Wide install base, best LLM SDK ecosystem, plays well with `llm-mcp` (also Python). 3.11 is the floor — pattern-matching, exception groups, faster startup. |
| Package manager | **`uv`** | 10x faster than pip; we already use uv across the workspace. PyPI install via pip still works; uv is preferred for dev. |
| CLI framework | **Typer** | Type-hint-driven, auto `--help`, plays cleanly with Rich, used by major modern CLIs (FastAPI's family). Click is fine but Typer is friendlier for this scope. |
| Output styling | **Rich** | Color tables, syntax-highlighted markdown, progress bars. Pairs with Typer natively. |
| Schema/validation | **Pydantic v2** | Wiki frontmatter, config files, run records all use Pydantic models. Fast (rust core) and the right ergonomics. |
| Local DB | **SQLite** (stdlib `sqlite3`) | Zero install. Runs everywhere. Good enough for v0.1's per-project state. |
| Optional DB | Postgres via `psycopg[binary]` | Bridge for users who want shared state. Off by default. |
| Test framework | **pytest** | Project standard; integrates with `pytest-asyncio`, fixtures, parameterization. |
| Lint/format | **ruff** + **mypy --strict** (lib code only) | Single fast linter, zero config drift; mypy on `src/kairos/` only, not on tests. |
| Build/packaging | **`hatchling`** via `pyproject.toml` | Modern PEP 621 `[project]` table; works with `uv build` and `pip`. |
| Distribution | **PyPI as `kairos-agent`** | `kairos` is taken (v0.10.1). Console script entry point still `kairos`. |
| Install one-liners | curl/sh + irm/iex shell scripts that wrap `uv tool install kairos-agent` (with `pip install --user` fallback) | Mirrors jcode's pattern. |

## Versions pinned

```toml
# pyproject.toml [project] requires-python and [tool.uv] etc.
python = ">=3.11,<3.14"

typer = ">=0.12,<1.0"
rich = ">=13.7,<14.0"
pydantic = ">=2.7,<3.0"
httpx = ">=0.27,<1.0"          # llm-mcp HTTP transport
mcp = ">=1.0,<2.0"             # MCP stdio transport
tomli = ">=2.0; python_version < '3.11'"   # config.toml parsing
platformdirs = ">=4.2,<5.0"    # ~/.kairos/* path resolution

# dev
pytest = ">=8.2,<9.0"
pytest-asyncio = ">=0.23,<1.0"
ruff = ">=0.5,<1.0"
mypy = ">=1.10,<2.0"
```

## Considered and rejected

- **Click** instead of Typer — works fine, but type-hint-driven Typer is less ceremony for the same surface.
- **Poetry** instead of uv — slower, heavier; we already standardized on uv.
- **DuckDB / TinyDB** — overkill or under-powered. SQLite is the boring correct answer.
- **Async-first CLI** — adds complexity; only the `llm-mcp` calls need async. We use `httpx.AsyncClient` inside a small sync facade so the CLI itself stays sync.
- **Pluggy / setuptools-entry-points for runners** — premature abstraction. v0.1 has 3 runners, all in `src/kairos/runners/`. We add a plugin spec when there's a real third-party runner asking for it.

## Consequences

- Code is import-light: no LangChain, no LlamaIndex, no CrewAI. We wire RAG / ReAct / Reflexion ourselves so users can read the source.
- Cross-platform CI matrix: macOS-latest, ubuntu-latest, windows-latest x Python 3.11, 3.12, 3.13.
- Binary size of the install: < 30 MB (rich + typer + pydantic + httpx + sqlite + click). No native deps unless user opts into Postgres bridge.

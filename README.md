<div align="center">
  <img src="assets/hero.png" alt="kairos" width="600" />
  <h1>kairos</h1>
  <p><strong>Stop guessing. Run the right pattern.</strong></p>
  <p>A CLI for executable agent knowledge.</p>
  <p>
    <a href="https://pypi.org/project/kairos-agent/"><img alt="PyPI" src="https://img.shields.io/pypi/v/kairos-agent.svg?color=5eead4&labelColor=0a0a0f"></a>
    <a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/kairos-agent.svg?color=5eead4&labelColor=0a0a0f"></a>
    <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-5eead4?labelColor=0a0a0f"></a>
    <a href="https://github.com/vinothhacks/kairos/actions"><img alt="CI" src="https://github.com/vinothhacks/kairos/workflows/ci/badge.svg"></a>
  </p>
  <p>
    <a href="#install">Install</a> · <a href="#30-second-demo">Demo</a> · <a href="#whats-new-in-v04">What's new in v0.4</a> · <a href="#why-kairos">Why kairos</a> · <a href="#quickstart">Quickstart</a> · <a href="#how-it-works">How it works</a> · <a href="#commands">Commands</a> · <a href="#configuration">Configuration</a>
  </p>
</div>

---

## What's new in v0.4

**v0.4.0 replaces the single llm-mcp shim with direct backends and makes kairos an MCP server.** Highlights:

- **Direct model backends** - `stub`, `ollama`, `openai`, `anthropic`, and `openai_compat`.
- **MCP server mode** - `kairos mcp serve` exposes seven tools to Cursor, Claude Desktop, and custom MCP clients.
- **Safer default** - `KAIROS_LLM_BACKEND` defaults to `stub`; `mcp` is removed with a clear migration error.
- **Audit gates closed** - Ruff, mypy, Bandit, strict `pip-audit`, Radon, Semgrep, MCP smoke, live Ollama, and KAI2 regression report are required CI checks.

Full migration notes: [`docs/UPGRADING.md`](docs/UPGRADING.md). MCP setup: [`docs/MCP.md`](docs/MCP.md).

## Install

```bash
pip install kairos-agent
```

That's it. By default kairos uses the deterministic `stub` backend. Point it at Ollama, OpenAI, Anthropic, or any OpenAI-compatible server when you want live model calls.

```bash
# or, with uv
uv tool install kairos-agent
```

```powershell
# Windows
irm https://raw.githubusercontent.com/vinothhacks/kairos/v0.4.0/install.ps1 | iex
```

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/vinothhacks/kairos/v0.4.0/install.sh | sh
```

## 30-second demo

```bash
$ kairos init my-wiki && cd my-wiki

$ kairos run "Search the docs for caching and summarize" --dry
   top-3 techniques for: Search the docs for caching...
   ┌──────┬───────────┬───────┬──────────────────────────────────┐
   │ rank │ technique │ score │ rationale                        │
   ├──────┼───────────┼───────┼──────────────────────────────────┤
   │ 1    │ rag       │ 0.70  │ keyword boost 0.50, overlap x4   │
   │ 2    │ react     │ 0.65  │ keyword boost 0.50, overlap x3   │
   │ 3    │ reflexion │ 0.05  │ overlap x1                       │
   └──────┴───────────┴───────┴──────────────────────────────────┘
```

`kairos` looks at your task, queries its wiki of agent techniques, and tells you which pattern to run: RAG, ReAct, or Reflexion. Then it actually runs it.

## Why kairos

You've read the LLM techniques. CoT, ReAct, Reflexion, ToT, HyDE, rerank — twenty patterns each with a paper, each with a use case, each easy to forget the morning you're three coffees into a real problem.

Most "LLM wikis" turn this into a static reading list. **kairos turns it into a runtime decision.** The wiki *is* the agent's playbook:

- **Ingest** raw sources (papers, transcripts, your own notes) → LLM-curated wiki pages.
- **Query** the wiki with natural language; answers cite real pages with `[[wikilinks]]`.
- **Lint** for contradictions, stale claims, and gaps. The wiki gets smarter with every run.
- **Run** any task — kairos picks the right technique by reading its own wiki, then executes it.

Three patterns ship with working runners (RAG, ReAct, Reflexion). The other 18 are documented and ready to be promoted from doc-only to runnable. **You can extend it.**

## Quickstart

```bash
# 1. Bootstrap a project. Copies 21 seed concept pages.
kairos init my-wiki && cd my-wiki

# 2. Ingest a source.
kairos ingest research/karpathy-llm-wiki-gist.md

# 3. Ask a grounded question.
kairos query "When should I use ReAct over RAG?"

# 4. Lint the wiki.
kairos lint

# 5. Run a task — kairos auto-selects the technique.
kairos run "Search the docs for caching, then summarize"

# 6. Or pick the technique manually.
kairos run "Iteratively refine this paragraph" --technique reflexion
```

Every run logs to `.kairos/kairos.db` (SQLite). Every page lives in plain markdown. Every wikilink survives `git diff`.

## How it works

```mermaid
flowchart LR
    User([User]) --> CLI["typer CLI<br/>cli.py"]
    CLI --> Cfg["config.load_config()<br/>env > .kairos/config.toml > defaults"]
    Cfg --> RunCmd["cli run/query/lint/ingest"]

    RunCmd -->|technique=auto| Selector["select_technique"]
    Selector --> Idx["wiki_index<br/>(SQLite cache)"]
    Idx -.cache miss.-> FS["wiki/ filesystem walk"]
    Selector -->|optional --llm-rerank| Rerank["claude_send tie-break"]
    Selector --> Rank["TechniqueChoice ranking"]

    Rank --> Disp["runners.dispatch<br/>+ entry_points discovery"]
    Disp --> ABC["Runner ABC"]
    ABC --> RAG["RagRunner"]
    ABC --> ReA["ReactRunner"]
    ABC --> Refl["ReflexionRunner"]
    ABC -.plugins.-> Plug["kairos-runner-*"]

    RAG --> Rec["RunRecorder.finish<br/>selected_by + score"]
    ReA --> Rec
    Refl --> Rec

    Rec --> DB[("kairos.db<br/>WAL + busy_timeout 5s")]
    DB --> Runs["runs"]
    DB --> FB["feedback (KAI-035)"]
    DB --> WI["wiki_index"]
    DB --> WR["wiki_relations"]

    CLI --> Providers["LLM providers<br/>stub / ollama / openai / anthropic / compat"]
    Providers --> LLM["model runtime"]
    CLI --> MCPServer["kairos mcp serve<br/>stdio MCP tools"]
    CLI --> Doc["kairos doctor<br/>provider probe"] --> Providers
    CLI --> FBcmd["kairos feedback"] --> FB
```

Three layers, mirroring [Karpathy's LLM Wiki gist](https://gist.github.com/karpathy):

1. **`raw/`** - your immutable inputs (papers, articles, transcripts). Source of truth.
2. **`wiki/`** - LLM-generated, human-curated markdown pages. Lives in git.
3. **`AGENTS.md`** - the schema. Tells future LLM passes how the structure works.

See [`docs/architecture.md`](docs/architecture.md) for the full diagram.

## Commands

| Command | What it does |
|---|---|
| `kairos init [path]` | Bootstrap `AGENTS.md`, `raw/`, `wiki/`, `outputs/`. Seeds 21 concept pages. |
| `kairos ingest <file>` | Read a source, propose new + updated wiki pages, log the diff. |
| `kairos query "<q>"` | Lexically retrieve pages, ask the LLM to synthesize, cite wikilinks. |
| `kairos lint` | Local: orphans, missing concepts, stale pages. LLM: contradictions, gaps. |
| `kairos run "<task>"` | Auto-select technique, dispatch runner, log the run. |
| `kairos run "<task>" --dry` | Show the top-3 candidate techniques without running. |
| `kairos history` | List recent runs from `.kairos/kairos.db`. |
| `kairos feedback-list` | List saved feedback rows. |
| `kairos mcp serve` | Serve kairos tools over stdio MCP. |
| `kairos doctor` | Print env diagnostics. |
| `kairos version` | Print version. |

## Current surface

| | Count | Status |
|---|---|---|
| Concept pages (seed wiki) | 21 | doc-only |
| Runner-backed techniques | 3 | RAG, ReAct, Reflexion |
| Tests | 115+ | unit, integration, regression |
| Storage backend | 1 | SQLite |
| LLM providers | 5 | stub, Ollama, OpenAI, Anthropic, OpenAI-compatible |

The 21 seed concept pages: rag, react, reflexion, chain-of-thought, tree-of-thoughts, self-consistency, self-refine, constitutional-ai, plan-and-execute, few-shot-prompting, zero-shot-prompting, function-calling, tool-use, prompt-injection, embedding-search, hybrid-search, hyde, rerank, router-agent, memory-buffer, llm-wiki.

## Compared to

| | kairos | LLM-wiki gist | Notion AI | Obsidian + plugins |
|---|---|---|---|---|
| Plain markdown source | yes | yes | no | yes |
| Diff-able in git | yes | yes | no | yes |
| Ingest sources via LLM | yes | yes | partial | with plugins |
| Lint for contradictions | **yes** | manual | no | no |
| Pick technique automatically | **yes** | no | no | no |
| Execute the technique | **yes** | no | no | no |
| Local-first model option | **yes** | no | no | partial |
| CLI-first | yes | no | no | no |

The wedge: **executable wiki, not passive notes.**

## Configuration

```bash
# Default: deterministic stub backend for offline tests
export KAIROS_LLM_BACKEND="stub"

# Local Ollama
export KAIROS_LLM_BACKEND="ollama"
export KAIROS_OLLAMA_MODEL="llama3.1"

# OpenAI / Anthropic
export KAIROS_LLM_BACKEND="openai"
export OPENAI_API_KEY="..."
export KAIROS_OPENAI_MODEL="gpt-4o-mini"

export KAIROS_LLM_BACKEND="anthropic"
export ANTHROPIC_API_KEY="..."

# LM Studio / vLLM / OpenRouter / Ollama OpenAI mode
export KAIROS_LLM_BACKEND="openai_compat"
export KAIROS_LLM_BASE_URL="http://localhost:1234/v1"
export KAIROS_LLM_MODEL="local-model"
```

Per-project config lives in `.kairos/config.toml`. Run `kairos doctor` to see resolved values.

## Roadmap

- **v0.4** *(now)* — direct providers, `kairos mcp serve`, required audit gates.
- **v0.5** — remove the compatibility `kairos.llm.mcp_client` import shim and expand provider cassettes.
- **v1.0** — Plugin runners (`pip install kairos-runner-tot`), web preview server.

See `CHANGELOG.md` for what landed in each release.

## Contributing

Found a wiki page that's wrong? Want a new technique runner? PRs welcome. Read `CONTRIBUTING.md` first.

```bash
git clone https://github.com/vinothhacks/kairos
cd kairos
uv pip install -e ".[dev]"
uv run pytest
```

## License

[MIT](LICENSE) © vinothhacks

## Acknowledgements

The wiki pattern is straight out of [Andrej Karpathy's LLM Wiki gist](https://gist.github.com/karpathy). The README structure follows [jcode](https://github.com/1jehuang/jcode) for the install-first / demo-first style. The technique catalog stands on the shoulders of every paper cited in the seed pages.

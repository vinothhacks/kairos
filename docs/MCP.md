# Kairos MCP Server

Kairos v0.4 can run as a stdio MCP server:

```sh
pip install "kairos-agent[mcp-server]"
kairos mcp serve
```

The server exposes seven tools:

| Tool | Purpose |
|---|---|
| `kairos.select_technique` | Rank techniques for a task. |
| `kairos.run_technique` | Run a technique or dry-run `auto` selection. |
| `kairos.query_wiki` | Ask a question grounded in the local wiki. |
| `kairos.lint_wiki` | Lint wiki pages and return structured findings. |
| `kairos.ingest_source` | Ingest a source file into `raw/` and `wiki/`. |
| `kairos.history` | List recent runs from `.kairos/kairos.db`. |
| `kairos.feedback` | Record feedback for a run id. |

## Cursor

Add this server to Cursor MCP settings:

```json
{
  "mcpServers": {
    "kairos": {
      "command": "kairos",
      "args": ["mcp", "serve"],
      "env": {
        "KAIROS_LLM_BACKEND": "stub"
      }
    }
  }
}
```

Use `stub` for deterministic local testing. For a local Ollama model:

```json
{
  "mcpServers": {
    "kairos": {
      "command": "kairos",
      "args": ["mcp", "serve"],
      "env": {
        "KAIROS_LLM_BACKEND": "ollama",
        "KAIROS_OLLAMA_MODEL": "llama3.1"
      }
    }
  }
}
```

## Claude Desktop

Add the same command to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kairos": {
      "command": "kairos",
      "args": ["mcp", "serve"]
    }
  }
}
```

## Backend Environment

| Backend | Required env | Optional env |
|---|---|---|
| `stub` | none | `KAIROS_STUB_PATH` |
| `ollama` | local Ollama on `localhost:11434` | `KAIROS_OLLAMA_URL`, `KAIROS_OLLAMA_MODEL` |
| `openai` | `OPENAI_API_KEY` | `KAIROS_OPENAI_MODEL` |
| `anthropic` | `ANTHROPIC_API_KEY` | `KAIROS_ANTHROPIC_MODEL` |
| `openai_compat` | `KAIROS_LLM_BASE_URL` | `KAIROS_LLM_API_KEY`, `KAIROS_LLM_MODEL` |

`KAIROS_LLM_BACKEND=mcp` was removed in v0.4. See `docs/UPGRADING.md` for the migration path.

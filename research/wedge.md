# Kairos Unique Angle (Phase 1)

> Source: ChatGPT (`chatgpt_send` conversation `6a0090d0-5a0c-83ab-a29c-047385d69145`) on 2026-05-10.

## 1. One-line wedge

Kairos turns an LLM-techniques wiki into an **executable agent router**: it ingests RAG, ReAct, Reflexion, ToT, MCP, and related patterns, then selects and runs the right one for each task through ChatGPT or Claude with **no API keys**.

## 2. Three competitive wedges (ranked)

### 1. Executable wiki, not passive notes

- **Wedge**: Kairos is the first Karpathy-style LLM Wiki aimed at agent techniques where the knowledge base directly controls execution.
- **v0.1 proof**: Ships `ingest`, `query`, and `lint`, plus a technique selector and working RAG, ReAct, and Reflexion runners.
- **Directly threatens**: every Obsidian/personal-note Karpathy implementation, because they stop at retrieval; Kairos moves from "read the pattern" to "run the pattern."

### 2. No API-key agent harness

- **Wedge**: Kairos routes every model call through `llm-mcp`, using browser-session access to ChatGPT and Claude instead of requiring paid API keys.
- **v0.1 proof**: All runners use the same `llm-mcp` bridge, making RAG / ReAct / Reflexion executable without provider SDK setup, env vars, or token billing configuration.
- **Directly threatens**: CacheZero's install-simplicity story (it requires a Gemini key); Kairos competes on the same low-friction CLI install but without the API-key wall.

### 3. Technique linting as trust infrastructure

- **Wedge**: Kairos treats agent techniques as maintained operational knowledge, not static markdown.
- **v0.1 proof**: `lint` gives the wiki a quality gate before the selector depends on it, catching weak or incomplete technique entries before they become bad runtime decisions.
- **Directly threatens**: kfchou/wiki-skills's provenance-verification advantage; Kairos can evolve from linting into stronger source/change verification while already tying quality to execution.

## 3. Story (README hero paragraph)

> Agent techniques are everywhere, but choosing one is still guesswork: RAG for context, ReAct for tools, Reflexion for retries, ToT for search, MCP for integrations. Kairos makes those patterns operational. Build a wiki of agent techniques, ask for a task, and Kairos selects the right pattern, runs it, and routes models through your existing ChatGPT or Claude session.

## 4. Three taglines (will pick after Claude critique)

1. *The agent pattern router.*
2. *From LLM wiki to running agent.*
3. *Agent techniques, selected and executed.*

## 5. Risks to the wedge

| Risk | Mitigation |
|---|---|
| **Browser-session fragility** — ChatGPT/Claude UI changes could break `llm-mcp` | Provider adapters per UI, smoke tests in CI, graceful fallback errors with clear messages. |
| **Selector trust gap** — bad wiki entries cause bad technique choices | Stricter lint rules, worked examples in every concept page, confidence-scored selection, `--technique` override. |
| **"No API keys" skepticism** — users question reliability or ToS boundaries | Clear docs on what `llm-mcp` does and does not do; "supported providers" list; explicit local/session security model in `OAUTH.md`. |

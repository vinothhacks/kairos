# Kairos v0.1 — Product Requirements Document

> Phase 1 output. Source: ChatGPT (`6a0090d0-5a0c-83ab-a29c-047385d69145`) + competitor scan (`97329b47-ccb1-4283-9253-9f0e4b479abc`) on 2026-05-10. ChatGPT confidence: 0.97.

## 1. Problem

Agent techniques are multiplying faster than developers can operationalize them. RAG, ReAct, Reflexion, Tree of Thoughts, Plan-Solve, MCP, memory, tool use, and evaluation patterns are scattered across papers, blog posts, repos, and personal notes.

Karpathy's LLM Wiki pattern gives developers a way to ingest and query knowledge, but most implementations stop at passive recall. They help users find notes; they do not decide which agent technique fits a task or execute that technique.

Kairos v0.1 addresses the missing bridge between knowledge and action: a local Python CLI that builds a wiki of LLM agent techniques, uses that wiki to select the right technique, and runs the selected pattern through ChatGPT or Claude via `llm-mcp` with no API keys.

## 2. Vision

By v1.0, Kairos becomes the executable knowledge layer for agent engineering. A developer maintains a living wiki of agent patterns, source examples, constraints, failure modes, and implementation notes, then asks Kairos to solve a task and watches it choose the right technique with transparent reasoning.

Kairos should feel less like a notes app and more like a technique-aware agent operating system: grounded in a curated wiki, portable across tools, safe by default, extensible through new runners, and usable by developers who already have ChatGPT or Claude access but do not want to manage API keys or provider SDKs.

## 3. v0.1 scope (in)

- `kairos init`
- `kairos ingest <file>`
- `kairos query "<q>"`
- `kairos lint`
- `kairos run "<task>"` with technique selector
- 3 working runners: RAG, ReAct, Reflexion
- Seed wiki of ~20 agent-technique pages
- `AGENTS.md` schema
- Install one-liners: mac/linux/windows
- `pip install kairos-agent`
- README + `docs/architecture.md`
- MIT license

## 4. v0.1 scope (out)

- ToT, Plan-Solve, multi-agent runners (doc-only in seed wiki)
- Postgres backend (sqlite default, postgres bridge optional, off in v0.1)
- MCP-server mode (so Claude Code / Cursor can call kairos as a tool)
- Obsidian frontend tutorial (mentioned in README, defer to docs site)
- Mobile (no iOS/Android)
- Web app
- Auto-applied wiki edits without human review

## 5. Success criteria for v0.1

1. `pip install kairos-agent` works on a clean venv.
2. `curl ... | bash` and `irm ... | iex` both install successfully.
3. End-to-end command sequence (`kairos init && kairos ingest <fixture> && kairos query "what is X" && kairos run "..."`) works on a clean machine.
4. `pytest` is green.
5. README looks competitive against jcode at first scroll (hero, tagline, GIF, install, demo links, badges).
6. GitHub repo published, tagged `v0.1.0`, social-preview uploaded.
7. LinkedIn launch artifacts ready (drafts only — never auto-sent).
8. At least one cycle of `kairos lint` captured with screenshot in README.

## 6. Non-goals (philosophy)

- **No API keys ever.** Every model call goes through `llm-mcp`.
- **`AGENTS.md` is sacred.** It defines the wiki schema and is version-controlled.
- **Humans curate `raw/`.** The LLM never modifies sources.
- **Surgical changes.** Following the Karpathy guidelines: minimum code, no speculative abstraction, match existing style.

## 7. Personas

**The agent-pattern explorer.** This is the developer who keeps seeing new patterns — RAG, ReAct, Reflexion, ToT, Plan-Solve, MCP — and wants to understand when each one actually matters. Today they save links, skim papers, paste snippets into ChatGPT, and rebuild small demos repeatedly. Kairos gives them a local technique wiki plus runnable examples, so exploration moves from "read and remember" to "query, select, run, compare."

**The LLM tutorial-writer.** This is the educator, blogger, course creator, or internal enablement lead explaining agent techniques to other developers. Today they manually collect references, write examples, and worry that demos are disconnected from real execution. Kairos gives them a structured seed wiki, lintable technique pages, and working RAG/ReAct/Reflexion runners, so tutorials can show both the concept and the CLI behavior from the same source of truth.

**The framework evaluator.** This is the engineer comparing whether a problem needs a framework, a prompt pattern, or a small local harness. Today they test LangChain, LlamaIndex, CrewAI, raw prompts, and browser sessions in separate experiments. Kairos changes the frame: instead of starting with a framework, they start with the task, let the selector choose a technique, and inspect whether a minimal runner is enough before adopting heavier infrastructure.

## 8. User journeys

### New user installs and tries kairos

1. Creates a clean Python virtual environment.
2. Installs with `pip install kairos-agent` or the OS one-liner.
3. Runs `kairos init` to create the local project structure and seed wiki.
4. Runs `kairos query "When should I use ReAct?"`.
5. Runs `kairos run "Answer this from the provided notes"` and sees a selected runner execute through `llm-mcp`.

### Power user adds a custom technique to the wiki

1. Creates a new markdown page for a technique not in the seed wiki.
2. Follows the `AGENTS.md` schema for summary, use cases, avoid cases, process, examples, and runner notes.
3. Runs `kairos ingest <file>` to add it to the local wiki.
4. Runs `kairos lint` and fixes warnings manually.
5. Runs `kairos query` and `kairos run "<task>"` to see whether the selector considers the new technique.

### Researcher uses `kairos run` to compare RAG vs Reflexion on a hard question

1. Prepares a hard question with supporting source material.
2. Runs the task with the RAG runner and saves the output.
3. Runs the same task with the Reflexion runner and saves the output.
4. Compares answer quality, trace clarity, failure modes, and time-to-answer.
5. Writes notes back into the wiki so future selector behavior reflects the observed tradeoffs.

## 9. Open questions

- Should the selector be rule-first, model-first, or hybrid for v0.2?
- Should provenance verification become mandatory before a technique can affect runtime selection?
- Should Kairos prioritize more runners next, or stronger evaluation of the three existing runners?

## 10. Caveats

This PRD assumes `llm-mcp` is stable enough for v0.1 demos and that the seed wiki can be curated to a consistent quality bar before launch.

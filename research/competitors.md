# Competitor Scan — Karpathy LLM Wiki community implementations (Phase 1)

> Source: Claude analysis (`claude_send` conversation `97329b47-ccb1-4283-9253-9f0e4b479abc`) on 2026-05-10.

The Karpathy LLM Wiki gist (Apr 2026, 5k+ stars) sparked at least seven community implementations within a week. Each takes a different slice of the pattern.

## 1. lucasastorian/llmwiki

A full-stack open-source implementation where you point it at any folder of PDFs/notes/spreadsheets, it indexes them locally with SQLite FTS5, and Claude connects over MCP to write and maintain `wiki/` pages on disk. Stack is Python (FastAPI) + Next.js web UI, with an optional hosted mode using Postgres, Supabase auth, and S3. Target user is the researcher or analyst with a messy folder of sources. **Strength**: cleanest separation of "your files stay where they are, the wiki sits beside them" plus a real local web UI. **Weakness**: no semantic/embedding search in local mode (FTS5 only), so retrieval quality degrades as the corpus grows.

## 2. Ar9av/obsidian-wiki

A skill-based framework (no daemon, no API keys) that ships markdown instructions any coding agent — Claude Code, Cursor, Windsurf, Codex, Gemini CLI, Copilot, and others — can execute against an Obsidian vault. Installs via `npx skills add` or a setup script; the agent itself is the runtime. Target user is the personal user who already lives in Obsidian and wants vendor-flexibility on the agent side. **Strength**: a `.manifest.json` enabling delta ingestion and staleness detection, plus genuinely portable across ~7+ agents. **Weakness**: because there's no scripted layer, behavior quality is entirely at the mercy of whichever agent is driving — no determinism floor.

## 3. NicholasSpisak/second-brain

Four Agent Skills (`/second-brain`, `-ingest`, `-lint`, `-query`) installed via npm into Claude Code, Codex, Cursor, Gemini CLI, or 40+ others, opinionated around Obsidian + Obsidian Web Clipper as the inbox. A wizard handles onboarding (vault name, location, domain, agent selection) and writes the per-agent config files. Target user is the personal knowledge-worker building a reading-driven second brain. **Strength**: tight Web Clipper loop — clip article → lands in `raw/` → run ingest → wiki page with backlinks — is the smoothest of the seven for article-based workflows. **Weakness**: heavily article-shaped; codebases, transcripts, and structured data are second-class.

## 4. ussumant/llm-wiki-compiler

A Claude Code/Codex plugin (`/wiki-compile`, `/wiki-ingest`, `/wiki-query`) explicitly framed as a context-cost reducer: instead of re-reading 100+ raw files every session, you compile them once into topic-based articles and query the synthesis. Stack is markdown skill files. Target user is the developer with a large project corpus or sprawling markdown notes. **Strength**: reframes the pattern as a ~90% context-cost reduction for agents working over big knowledge piles, which resonates well for codebase docs. **Weakness**: no built-in viewer or graph — you bring your own (Obsidian, qmd) — so out-of-box exploration is thinner.

## 5. CacheZero (swarajbachu/cachezero)

A one-command npm install (`npx cachezero init`) that bundles a Chrome extension, a Hono server on :3777, an Obsidian-compatible vault under `~/.cachezero/vault/`, a LanceDB vector index, and an MCP server for Claude Code. TypeScript/Node throughout. Target user is the personal user who wants the lowest-friction onramp — bookmark from browser, compile, query. **Strength**: genuinely the fastest path from zero to a working compounding vault, with browser-capture built in. **Weakness**: requires a Gemini API key for vector search, so it's **not key-free**; and the all-in-one bundling makes individual components harder to swap out.

## 6. kfchou/wiki-skills

A Claude Code plugin implementing the Karpathy ops as skills with notable extras: `wiki-query`, `wiki-lint` (severity-tiered reports), `wiki-update` (diff-before-write, sweeps stale claims), and `wiki-audit`, which dispatches one subagent per source in parallel to verify each footnote. Target user is the personal-to-team knowledge worker who cares about wiki truthfulness over time. **Strength**: parallel-subagent fact-checking that string-matches quote citations and judges synthesis citations against the cited range — the only one of the seven with real provenance verification. **Weakness**: tightly coupled to Claude Code's plugin/subagent model, so portability to other agents is limited.

## 7. balukosuri/llm-wiki-karpathy

A ready-to-use repo template — clone, get a `CLAUDE.md` schema, a pre-scaffolded `raw/` and `wiki/` (with `index.md`, `overview.md`, `glossary.md`, `log.md`), plus a pre-configured `.obsidian/` directory. No CLI, no daemon, no scripts; the IDE (Cursor primarily, but any agent works) reads `CLAUDE.md` and operates directly. Target user is the personal user — explicitly framed for technical writers — who wants the pattern materialized as a starter kit, not a tool. **Strength**: shortest possible distance from "read the gist" to "working vault" with sane Obsidian defaults included. **Weakness**: it's a template, not a living tool — no ingest automation, no lint commands, no delta tracking.

## Comparison

| Project | Lang | Wiki target | Has CLI | Auth model | Distinguishing feature |
|---|---|---|---|---|---|
| lucasastorian/llmwiki | Python + Next.js | Any folder + own web UI | Yes (`./llmwiki`) | Local: none. Hosted: Supabase + S3; agent via MCP | Dual local/hosted modes, MCP-first |
| Ar9av/obsidian-wiki | Markdown skills (+Python helpers) | Obsidian vault | No (agent slash-commands) | Inherits agent's auth | Multi-agent (~7+), delta manifest |
| NicholasSpisak/second-brain | Markdown skills (npm) | Obsidian vault | No (agent slash-commands) | Inherits agent's auth | Web Clipper inbox + wizard onboarding |
| ussumant/llm-wiki-compiler | Markdown skills (Claude Code/Codex plugin) | Any markdown / codebases | No (plugin commands) | Inherits agent's auth | Topic-based compilation for context cost |
| CacheZero | TypeScript / Node | Obsidian-compatible vault + own server | Yes (`npx cachezero`) | Gemini API key required | Bundled Chrome extension + LanceDB |
| kfchou/wiki-skills | Markdown skills (Claude Code plugin) | Any folder | No (plugin commands) | Inherits Claude Code auth | Parallel-subagent citation audit |
| balukosuri/llm-wiki-karpathy | Markdown template | Obsidian vault | No (template only) | Inherits IDE's auth (Cursor primarily) | Clone-and-go starter kit |

## GAPS — what nobody solves well

1. **Multi-user / team collaboration** with real auth, concurrent edits, and access control. Only `llmwiki`'s hosted mode even gestures at Supabase; none handle two people editing the same wiki page or scoped visibility for sensitive sections.
2. **Mobile capture.** Every implementation assumes a desktop terminal plus Obsidian or a desktop browser with Web Clipper; there's no good "snap a thought from my phone, have it land in `raw/`, and re-ingest later" path.
3. **Source-change reconciliation.** When a `raw/` source is updated or deleted, dependent wiki pages, cross-references, and contradictions don't get cleanly revised. Manifests track ingestion but not retraction. (`kfchou/wiki-update` sweeps stale claims but not orphaned pages from deleted sources.)
4. **Cross-implementation portability.** Each tool's `CLAUDE.md` schema, page conventions, and frontmatter differ enough that a vault built in one is not cleanly readable by another. Users get locked into whichever scaffold they picked first.
5. **Cost/budget controls for large-corpus ingestion.** None expose token budgets, batching policies, or "stop at $X" guardrails — which matters once you point any of these at a 500-PDF research folder.

## Why kairos is genuinely different

Three of these gaps directly map to kairos wedges; we have one more wedge none of them touch:

- **Cost = $0** by design (no API key required because every model call goes through `llm-mcp` browser sessions on subscription accounts) — beats CacheZero's Gemini key requirement and avoids gap (5) entirely.
- **The wiki target is agent techniques, not personal notes.** None of the seven ship a curated technique library that the agent then *uses* to pick how to solve your task — they all leave selection to the user.
- **Self-improvement loop** (runs feed lint feed wiki edits) — closer to `kfchou/wiki-skills`'s audit but operating on the technique wiki, not on user content.
- **MCP-server mode** so kairos itself can be plugged into Claude Code, Cursor, etc. — closes the gap (4) cross-implementation portability problem from the other direction.

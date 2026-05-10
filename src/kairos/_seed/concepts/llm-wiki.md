---
title: "LLM Wiki"
type: concept
sources:
  - "Karpathy, A. (2024). LLM Wiki gist - github.com/karpathy"
  - "Park et al., 2023 - Generative Agents (arXiv:2304.03442) [memory streams as adjacent prior art]"
related:
  - "[[rag]]"
  - "[[memory-buffer]]"
  - "[[reflexion]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# LLM Wiki

## Summary

An LLM Wiki is a persistent, structured artifact compiled from raw sources by a language model — a wiki you write *with* the model, not in place of it. Three layers: an immutable `raw/` of original sources (papers, transcripts, notes); a `wiki/` of LLM-generated, human-curated markdown pages; and an `AGENTS.md` schema that tells future LLM passes how the structure works. The pattern was popularized by Andrej Karpathy as a way to scale personal knowledge management with model help while keeping the source of truth in plain text.

## When to use

- You have a steady stream of raw inputs (papers, calls, articles) and want compiled, queryable knowledge instead of a raw inbox.
- You want the structure to outlive any single LLM provider — markdown plus a schema travels.
- You need diff-able, version-controllable knowledge for collaboration or audit.
- Repeat queries on the same domain are common; pre-compiled pages amortize the LLM cost.
- You want an explicit place to record contradictions and gaps rather than letting them hide in a vector DB.

## When NOT to use

- One-off questions where retrieval is enough — building a wiki is overhead with no payoff.
- Tiny, fast-moving domains where every page is stale within a week.
- Cases where the corpus is already a high-quality wiki (Wikipedia, internal Confluence) — start from it instead.
- Strict privacy environments where storing LLM-generated summaries of source material is itself a leakage risk.
- You don't have a way to keep `raw/` immutable; the pattern depends on `wiki/` being always-rebuildable from it.

## How it works

1. **Ingest:** add a new file to `raw/`. Run `ingest`: the LLM reads the source and proposes new pages, updates to existing pages, and new wikilinks back into the index.
2. **Curate:** humans review the proposed diff, accept/reject, and commit. The wiki only changes through this gate.
3. **Query:** when you want an answer, the system retrieves matching `wiki/` pages (lexical or vector) and asks the LLM to synthesize, citing the pages it used.
4. **Lint:** periodically run a wiki-wide check for orphans, stale claims, contradictions across pages, and gaps the schema says should exist.
5. **Run:** the wiki itself can be the input to runtime decisions — pick which technique to use, pick which prompt template fits, etc.

## Failure modes

- **Page sprawl:** every ingest spawns a new page; the wiki becomes too large to navigate. Mitigated by aggressive merging during curation.
- **Schema rot:** `AGENTS.md` is updated for new page types but old pages aren't migrated; the wiki becomes inconsistent.
- **Citation drift:** wiki claims survive after their source is deleted from `raw/`; lint must catch this.
- **Vibe summaries:** without strict source-quoting rules, pages drift from the original sources into the model's prior.

## Related techniques

- [[rag]] - a complementary pattern: RAG retrieves chunks from raw text per query; an LLM Wiki compiles raw sources into structured pages once and reuses them. They can be layered.
- [[memory-buffer]] - shares the "compiled prior context" idea, but a memory buffer is per-session and ephemeral; an LLM wiki is durable and shared.
- [[reflexion]] - the lint step in an LLM wiki is structurally similar to a reflection pass over the entire knowledge artifact instead of a single output.

## Sources

- Karpathy, A. (2024). *LLM Wiki* — gist describing the pattern, the three-layer structure, and the core operations (ingest, query, lint).
- Park, J. et al. (2023). *Generative Agents: Interactive Simulacra of Human Behavior.* arXiv:2304.03442 — adjacent prior art on memory streams as persistent agent state.
- This wiki — kairos's own seed wiki is itself an LLM Wiki and serves as a reference implementation.

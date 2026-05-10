# Kairos Wiki Schema

> The single most important file in a kairos project. This is what makes the LLM a disciplined wiki maintainer rather than a generic chatbot. Co-evolve it with kairos as you figure out what works for your domain.
>
> Inspired directly by Karpathy's [LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (April 2026).

## Project structure

- `raw/` — Immutable source documents (papers, articles, code, transcripts). **Never modify files here.**
- `wiki/` — LLM-generated and LLM-maintained markdown pages.
  - `wiki/index.md` — Master content catalog. Update on every operation.
  - `wiki/log.md` — Append-only operation log.
  - `wiki/concepts/` — Concept pages (one per agent technique or LLM concept).
  - `wiki/sources/` — Source summaries (one per ingested document in `raw/`).
  - `wiki/comparisons/` — Comparison pages (e.g. `rag-vs-reflexion.md`).
- `outputs/` — Lint reports, run transcripts, generated artifacts.
- `.kairos/kairos.db` — Project-local state (runs, feedback, derived index).

## Page types

Every wiki page must have YAML frontmatter:

```yaml
---
title: "Page Title"
type: concept | source | comparison
sources:
  - raw/path/to/source.md
related:
  - "[[other-concept]]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
confidence: high | medium | low
has_runner: true | false       # for type=concept only; v0.1 supports rag, react, reflexion
---
```

### Concept pages (`wiki/concepts/<slug>.md`)

A single agent technique or LLM concept. Sections, in order:

1. `## Summary` — 1 paragraph. What is this technique?
2. `## When to use` — 3-5 bullets of concrete situations.
3. `## When NOT to use` — 3-5 bullets of anti-patterns.
4. `## How it works` — 3-7 sentences. Step-by-step at a high level.
5. `## Worked example` — 1 example with input + output.
6. `## Failure modes` — 3-5 bullets of how this technique typically fails.
7. `## Related techniques` — bullets of `[[other-concept]]` links.
8. `## Sources` — bullets of `[[source-summary]]` links.
9. `## Runner notes` — only present if `has_runner: true`. CLI invocation, options, expected output.

### Source pages (`wiki/sources/<slug>.md`)

Summary of a single ingested file. Sections:

1. Frontmatter `sources:` points to the file in `raw/`.
2. `## TL;DR` — 2-3 sentences.
3. `## Key claims` — bullets, each with `[[concept]]` links and a `(claim is: confirmed | extends | contradicts)` tag.
4. `## Quotes worth keeping` — verbatim quotes with line/section reference back to the raw source.
5. `## Open questions` — bullets the source raises but does not answer.

### Comparison pages (`wiki/comparisons/<slug>.md`)

E.g. `rag-vs-react.md`. Sections:

1. `## When you'd pick X`
2. `## When you'd pick Y`
3. `## Combination` (optional, for composite techniques)
4. `## Quick rule of thumb`

## Naming

- Filenames: kebab-case matching the concept (e.g. `tree-of-thoughts.md`).
- Cross-references: `[[wikilinks]]` for all internal links.
- Source references: `raw/papers/<exact-filename>.md` style relative paths.

## Workflows

### Ingest

1. Read the document in `raw/`.
2. Discuss key takeaways briefly (one paragraph).
3. Create `wiki/sources/<slug>.md`.
4. Update or create concept pages it touches (max 15 pages per ingest to keep changes reviewable).
5. Update `wiki/index.md` with new entries.
6. Append to `wiki/log.md` with affected pages.

### Query

1. Read `wiki/index.md`.
2. Identify relevant concept and source pages.
3. Read those pages and synthesize an answer.
4. Cite using `[[wikilinks]]`.
5. If the answer is novel and valuable, offer to save it as a new concept or comparison page.

### Lint

1. Scan all `wiki/*.md`.
2. Find:
   - Contradictions between pages.
   - Orphan pages (no incoming `[[wikilinks]]`).
   - Missing concepts referenced but not created.
   - Stale claims superseded by newer sources.
   - Investigation gaps where more research is needed.
3. Save results to `outputs/lint-YYYY-MM-DD.md`.

### Run (kairos-specific)

1. Read `wiki/index.md` and concept page summaries.
2. Score concept pages against the user's task.
3. Pick a technique. Default = top-1; `--dry` returns top-3 without running.
4. Execute the corresponding runner (`rag`, `react`, `reflexion`).
5. Log run to `.kairos/kairos.db` and `outputs/run-<id>/`.

## Hard rules for the LLM

1. **Never modify files in `raw/`.** They are immutable user-curated sources.
2. **Always update `wiki/index.md` and `wiki/log.md`** on any wiki write.
3. **Surgical changes only.** When updating an existing wiki page, change the minimum number of lines that satisfy the new claim. Do not "improve" adjacent unrelated content.
4. **Confidence honestly.** If a concept page conflates multiple sources, set `confidence: medium`. If it's mostly inferred, `confidence: low`.
5. **No fabrication.** If a source does not support a claim, do not assert it. Use the `(claim is: ...)` tag in source pages and contradiction markers in concept pages.
6. **Banned phrases**: do not use AI-cringe phrases (`thrilled`, `humbled`, `excited to embark`, `journey continues`, `unleash`, `unlock`, `leverage`, `cutting-edge`, `next-generation`, `revolutionize`, `game-changer`).

## Notes for kairos developers

This file is shipped alongside the package's seed wiki. When a user runs `kairos init`, this file is copied into their project root. They are encouraged to edit it for their domain — the seed `AGENTS.md` is a starting point, not gospel.

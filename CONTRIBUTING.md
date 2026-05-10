# Contributing to kairos

Thanks for considering a contribution. The bar is high but the surface is small — almost any well-tested PR is welcome.

## What's open for contribution in v0.1

- **Seed wiki pages.** The 21 seeded pages are all `confidence: high` summaries. Improvements, citations, worked examples are welcome.
- **New runner-backed techniques.** Today: RAG, ReAct, Reflexion. Add Self-Consistency, ToT, HyDE, Self-Refine — the doc-only pages are templates.
- **Lint rules.** Suggest additional local checks (broken citations, redundant pages, schema-mismatch).
- **Selector heuristics.** v0.1 is rule-based. v0.2 will add per-technique outcome scoring; PRs welcome ahead of that.
- **Documentation.** README polish, architecture clarifications, runnable examples.

## What's not open yet

- Multi-user / multi-tenant changes — wait for v0.3.
- Vector-backed memory — a doc-only `[[embedding-search]]` page exists, but the runtime stays lexical in v0.1.
- Web UI / preview server — explicitly v1.0.

## Setup

```bash
git clone https://github.com/vinothhacks/kairos
cd kairos
uv pip install -e ".[dev]"
uv run pytest
```

## Quality bar

A PR will be reviewed only if:

- `uv run pytest` is green.
- `uv run ruff check src/ tests/` reports no new errors.
- `uv run mypy src/` reports no new errors.
- New code has tests; new wiki pages have at least 4 sections (Summary, When to use, How it works, Sources).
- Wiki pages pass `kairos lint -p .` with zero high-severity findings.
- Commit message uses imperative tense ("Add Reflexion runner" not "Added Reflexion runner").

## Adding a new technique runner

1. Pick a doc-only concept page from `src/kairos/_seed/concepts/`.
2. Flip the page's frontmatter `has_runner: false` → `has_runner: true`.
3. Add `Runner notes` section to the page describing flags and tool calls.
4. Implement `src/kairos/runners/<slug>.py` with a `run_<slug>(task, ...) -> RunResult`.
5. Wire the dispatcher in `src/kairos/runners/__init__.py`.
6. Add unit tests covering `StubLLMClient`-backed happy path + at least one failure mode.
7. Update `selector.py` keyword boosts so the new technique can win when appropriate.
8. Update README and CHANGELOG.

## Reporting bugs

Open an issue with:

- `kairos version` output.
- `kairos doctor` output.
- The exact command that broke.
- The error or unexpected output.
- A minimal `wiki/concepts/<slug>.md` reproducer if the bug is wiki-specific.

## License

By contributing, you agree your contributions are licensed under the project's [MIT License](LICENSE).

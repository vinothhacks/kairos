# 0003 — Strategic considerations folded into v0.1 (and tracked into v0.2)

Date: 2026-05-10
Status: accepted (v0.1 closed)

## Context

During the brand-pass critique (`assets/brand.md`), Claude raised three strategic risks that go beyond v0.1's narrow scope. They are real, but addressing them now would expand the v0.1 surface beyond what the timeline allows. This decision documents how we handled each one in v0.1 and where we expect to land them.

## Decision

### 1. "Does ingest feed routing?"

**Risk:** if ingested user pages don't influence the technique selector, the wiki is read-only from the agent's point of view and the pitch ("the wiki *is* the playbook") is hollow.

**v0.1 resolution:** the selector reads `wiki/index.md` and concept-page summaries directly. User-ingested pages land in the same index and ARE used by the selector — the keyword-boost dictionary is computed off the wiki contents at selector-call time, not at install time. This becomes the headline feature on the README.

**v0.2 plan:** record per-technique outcome scores from the `runs` table and weight selection by historical success on similar tasks. Outcome will be inferred from `feedback.rating` (1-5 stars) plus `runs.status`.

### 2. Seed-vs-ingested authority conflict

**Risk:** the seed wiki says one thing, the user's notes say another. Whose claim wins?

**v0.1 resolution:** user pages always shadow seed pages on the same slug. The `wiki_index.updated` timestamp is the tiebreaker — most recent update wins. This is documented in `AGENTS.md`.

**v0.2 plan:** introduce explicit `supersedes:` and `contradicts:` relations in frontmatter. Lint adds a `provenance-conflict` finding when seed and user pages on the same slug disagree on `confidence` or `has_runner`.

### 3. Pattern combinations

**Risk:** Reflexion-over-ReAct, ToT-with-retrieval, RAG-then-Reflexion. These are real techniques and v0.1 ignores them.

**v0.1 resolution:** combinations are doc-only via the `comparisons/` subfolder type defined in `AGENTS.md`. We seed zero comparison pages but the type exists.

**v0.2 plan:** introduce `composite` as a first-class page type. A composite page lists 2-3 techniques and a wrapping policy ("run inner technique X up to N times, on each failure run technique Y, return when Y signals done"). The selector becomes aware of composites and can pick them when their constituent techniques both score high.

## Consequences

- The README's selector demo can honestly claim "your ingested notes change the selection" because they do.
- The lint pass for v0.1 is light on conflict detection; users will see drift before lint flags it.
- Composite techniques are deferred but the schema slot for them already exists, so v0.2 won't be a breaking change.

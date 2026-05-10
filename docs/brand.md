# Kairos brand (Phase 3)

## Locked

| Element | Value |
|---|---|
| Repo / CLI binary | `kairos` |
| PyPI distribution | `kairos-agent` |
| Hero tagline | **Stop guessing. Run the right pattern.** |
| README subtitle | A CLI for executable agent knowledge. |
| Color palette | Near-black background `#0a0a0f` + teal-cyan `#5eead4` glow + warm white `#f5f5f5` body |
| Typography | Monospace (JetBrains Mono / Berkeley Mono) for headings + numerics, system-default for body |
| Tone | Direct, technical, slightly opinionated. No AI-cringe phrases (banned-phrase regex applies). |

## Banned phrases (enforced on every README, post, blog draft)

- `thrilled`, `humbled`, `excited to embark`, `journey continues`
- `unleash`, `unlock` (as verb), `leverage` (as verb)
- `cutting-edge`, `next-generation`, `revolutionize`, `game-changer`
- `in today's fast-paced world`, `paradigm shift`, `disrupting`
- exclamation marks in headings

## Assets shipped in v0.1

| Path | Spec | Source |
|---|---|---|
| `assets/hero.png` | 1024x1024 PNG, ~1.8MB. Hourglass of glowing code in deep space, technique tags floating around. | `chatgpt_image_create` (`6a009585-5bd4-8324-b399-7ddc440bca60`) |
| `assets/social-preview.png` | 1280x640 PNG, ~1.4MB. Left: 'kairos' wordmark + tagline + subtitle. Right: small hourglass + technique labels. | `chatgpt_image_create` (`6a009774-8e98-8320-b41f-8a0fbe87beba`) |
| `assets/logo.png` | 1024x1024 PNG, ~600KB. Two opposing arrowheads forming a glowing teal hourglass on black. Icon-clean. | `chatgpt_image_create` (`6a0097f6-4bdc-8320-94ec-7356affea3d1`) |
| `assets/demo.gif` | TBD (Phase 7 — recorded with asciinema, converted to GIF). | TBD |
| `assets/logo.svg` | TBD (manual cleanup of `logo.png` via Figma or Vectornator post-launch). | TBD |

## Tagline alternatives (kept for v0.2 review)

ChatGPT's 5 fresh candidates ranked from the brand pass:

1. **Stop guessing. Run the right pattern.** — picked
2. A CLI for executable agent knowledge. — used as subtitle
3. RAG, ReAct, Reflexion — routed.
4. Your agent playbook, runnable.
5. Turn agent notes into agent runs.

ChatGPT's original three (rejected for hero, but archived):

- *The agent pattern router.* (too internal)
- *From LLM wiki to running agent.* (subtitle-shaped, awkward)
- *Agent techniques, selected and executed.* (plain)

## Strategic refinements from Claude critique (folded into PRD + v0.2)

> Source: `claude_send` (`75ebf4aa-991f-479c-9e5a-5f0c566e9f7d`) on 2026-05-10.

Claude flagged three strategic risks worth tracking, even though the tagline question wasn't its preferred output:

1. **"Does ingest feed routing?"** — In v0.1 the selector reads `wiki/index.md` + concept page summaries; user-ingested pages go into the same index, so they DO influence selection. This becomes the headline feature on the README. v0.2: track per-technique outcome scores from `runs` table to weight selection.
2. **Seed-vs-ingested authority conflict** — what wins when the seed says "Reflexion is best for X" but the user's notes say "Reflexion blew up on our X"? v0.1: user pages always shadow seed pages (most-recent-update-wins on `wiki_index.updated`). v0.2: explicit lint policy with "supersedes" relations.
3. **Pattern combinations** — Reflexion-over-ReAct, ToT-with-retrieval. v0.1 doc-only in the comparisons folder; v0.2 introduces "composite techniques" as a first-class wiki type.

These are noted in `docs/decisions/0003-strategic-considerations.md` (TBD).

## Verification

Hero, social-preview, and logo PNGs are all written to `assets/`. Visual check:

- `hero.png` — dark dramatic, technique tags visible, glow legible. PASS for v0.1; may iterate in Phase 11.
- `social-preview.png` — wordmark + tagline + subtitle on left, hourglass on right. PASS.
- `logo.png` — single object, scalable, identifiable at small sizes. PASS.

Phase 3 closed.

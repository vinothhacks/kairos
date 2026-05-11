# kairos v0.1.0: LinkedIn launch kit

Drafts only. Nothing here has been posted. Review, edit voice to your own,
attach the suggested asset, then post when ready.

> **Status**: drafts (not posted) · **Repo**: https://github.com/vinothhacks/kairos · **Release**: https://github.com/vinothhacks/kairos/releases/tag/v0.1.0

---

## A. Single-image launch post (recommended first)

**Attach**: `assets/social-preview.png` (1280×640)

**Hook (first 140 chars: what shows above "see more")**:

```
Most LLM agents pick a technique by vibes. RAG? ReAct? Reflexion? "Idk, let me try one."

I shipped a tool that picks for you.
```

**Full post body**:

```
Most LLM agents pick a technique by vibes. RAG? ReAct? Reflexion? "Idk, let me try one."

I shipped a tool that picks for you.

It's called kairos. It's a CLI that:

- Indexes a curated wiki of agent techniques (RAG, ReAct, Reflexion, Self-Refine, Constitutional AI, Tree of Thoughts, plus 14 more: 20 pages today)
- Takes any task description and routes it to the right technique
- Runs the technique end-to-end and logs the run

Built on Karpathy's "LLM wiki" pattern: raw sources -> LLM-curated wiki -> runtime knowledge graph. The wiki is the source of truth; the agent is just a function over it.

What's interesting:

1) Zero API keys. Every model call routes through llm-mcp (a stealth Playwright browser holding ChatGPT and Claude sessions). It runs behind corporate networks where OpenAI/Anthropic APIs are blocked.

2) Lexical retrieval beats embeddings under 500 pages. No vector DB, no embedding fees, ~50 ms recall. (We benchmarked. Embeddings only win once the wiki gets large.)

3) The selector is rule-based, not LLM-based. Deterministic, offline-testable, and you can read the decision in the trace log. No "the LLM picks the LLM" infinite recursion.

v0.1 ships with 3 working runners (RAG, ReAct, Reflexion), 21 seed concept pages, 48 unit tests, 5 e2e scripts, and one-line install via uv, pipx, or pip.

If you've ever stared at LangChain's runnable hierarchy and wondered "is this the right pattern for my problem?", that's the question kairos answers.

Repo: https://github.com/vinothhacks/kairos
Install: uv tool install kairos-agent
Quickstart: kairos init && kairos run "your task here"

If you try it and it picks the wrong technique, file an issue with the task and I'll tune the selector.

#LLM #AIAgents #OpenSource #Python #DeveloperTools
```

**Post checklist before publish**:

- [ ] Image attached (social-preview.png, not hero.png; the social preview is sized for the feed)
- [ ] Repo link unfurls (preview shows on LinkedIn)
- [ ] First line is genuinely hooky (not "Excited to announce...")
- [ ] No "AI-generated" tells: no em-dashes, no "delve", no "elevate", no "leverage"
- [ ] CTA is a question, not a demand ("file an issue with the task" > "go star it")

---

## B. 8-slide carousel (deeper version, post 3-7 days after A)

**Format**: 1080×1080 PNG per slide. Generate via Canva / Figma / `chatgpt_image_create`.
**Attach**: 8 PNGs in order.

### Slide 1: Cover

**Visual**: kairos logo + tagline + "v0.1.0" badge

**Title**: kairos
**Subtitle**: An LLM agent that picks the right technique for the job
**Footer**: github.com/vinothhacks/kairos

### Slide 2: The problem

**Visual**: meme-style "is this the right LLM technique?" decision tree with question marks everywhere

**Headline**: There are 20+ named LLM agent patterns. Which one fits YOUR task?
**Body**:
- RAG, ReAct, Reflexion, Self-Refine, Constitutional AI, Tree of Thoughts, Self-Consistency, Plan-and-Execute, HyDE, Hybrid Search, Rerank, Router, Memory Buffer, Tool Use, Function Calling, Few-Shot, Zero-Shot, Chain-of-Thought, Embedding Search, Prompt Injection, ...
- Most teams pick by vibes. Or by framework default.
- Wrong technique = wasted tokens + wrong answer.

### Slide 3: The pattern

**Visual**: Karpathy's LLM wiki diagram (3 layers: raw / wiki / agent)

**Headline**: Andrej Karpathy's "LLM Wiki" pattern
**Body**:
- raw/: sources (papers, plans, notes)
- wiki/: LLM-curated markdown pages with strict frontmatter
- agent.md: schema/index that routes queries

The wiki is the source of truth. The agent is a function over it.

### Slide 4: How kairos works

**Visual**: architecture diagram (the mermaid flow from `docs/architecture.md`)

**Headline**: 5 commands, one decision tree
**Body**:
1. `kairos init`: scaffold the wiki
2. `kairos ingest`: pull plans, papers, notes into raw/ then synthesize wiki/
3. `kairos query`: recall the right page in <100 ms (lexical, no embeddings)
4. `kairos lint`: keep the wiki honest (broken links, drift, schema)
5. `kairos run`: pick a technique, execute, log the run

### Slide 5: The selector

**Visual**: terminal screenshot of `kairos run` showing the selection trace
("RAG: confidence=0.78 (keywords: 'summarize', 'docs'; lexical overlap: 0.42)")

**Headline**: Rule-based, not LLM-based
**Body**:
- Deterministic. Reproducible. Offline-testable.
- Reads the wiki to score each technique against your task
- You can SEE the decision in the trace log
- No "the LLM picks the LLM" recursion

### Slide 6: The 3 runners (v0.1)

**Visual**: 3-column comparison

**Headline**: Three working techniques on day one

| | RAG | ReAct | Reflexion |
|---|---|---|---|
| When | Recall over docs | Tools needed | Iterative quality |
| Loop | Single-shot | Thought/Action/Obs | Draft -> critique -> revise |
| Calls | 1 ChatGPT | N Claude (default 6) | 3 (ChatGPT-Claude-ChatGPT) |

### Slide 7: Why it runs anywhere

**Visual**: corporate firewall icon + green checkmark

**Headline**: Zero API keys. Routes through `llm-mcp`.
**Body**:
- llm-mcp = stealth Playwright browser holding ChatGPT + Claude sessions
- 30 MB memory, 85 ms page loads (vs 200+ MB headless Chrome)
- Anti-bot detection built in (Obscura)
- Works behind corporate networks where OpenAI / Anthropic APIs are blocked
- No "give us your credit card" friction for trials

### Slide 8: Try it

**Visual**: terminal one-liner + repo URL

**Headline**: Install in 30 seconds
**Body**:
```
uv tool install kairos-agent
kairos init my-wiki && cd my-wiki
kairos run "Summarize the docs in this repo"
```
**Footer**:
- 48 tests passing on day one
- MIT licensed
- v0.2 roadmap: PyPI publish, embeddings (>500 pages), more runners
- github.com/vinothhacks/kairos

---

## C. Engagement plan (5 connections + 3 comments)

Goal: 100 organic reach in week 1 without spam. Comment first, post second, follow up third.

### 5 connections to send (no template: write each note manually, 1-2 sentences each)

Find these accounts via LinkedIn search. Replace with the actual person + a real
hook from their recent activity.

1. **Andrej Karpathy**. Note: "Built a CLI that puts the LLM wiki pattern from your gist into 84 lines of Python + a curated wiki of agent patterns. v0.1 is up at github.com/vinothhacks/kairos. Would love your feedback if anything jumps out."
2. **Author of LangChain / LlamaIndex / Haystack** (pick one whose recent post mentioned agent routing). Note: "Saw your post about [specific point]. Shipped kairos this week, which takes the opposite approach (lexical wiki, rule-based selector). Curious what you'd push back on."
3. **One person who recently posted "I tried building an agent and..."**. Note: pure curiosity, ask one specific question about their post. Don't pitch.
4. **One person at a company you'd want to work with that publishes engineering blogs**. Note: reference one of their posts, share the kairos repo only if they ask.
5. **One person who recently shipped a similar dev tool**. Note: "Shipped kairos last week. We're solving adjacent problems. Want to compare notes on what didn't work?"

### 3 comments to leave (this week, on posts in your feed about LLM agents)

Rules: substantive comment > 200 chars, no link to kairos in the comment itself,
mention kairos only if directly relevant to the post.

**Template structure** (write each freshly, don't copy):
1. Specific thing you agreed with from their post (1 sentence)
2. Counter-point or extension based on what you learned building kairos (2 sentences)
3. Open question back to them (1 sentence)

**Examples of openings to look for in your feed**:
- "Why did agent X fail in production?"
- "How do you debug an LLM agent?"
- "What's the right abstraction for tools?"
- "RAG vs fine-tuning, which won?"
- "Karpathy posted [anything]"

### What NOT to do

- Don't DM the launch post. People hate that.
- Don't post "Excited to announce!". Hook with the problem, not the announcement.
- Don't tag 10 people. Tag at most 1, and only if they directly inspired the work (Karpathy, on the carousel post specifically).
- Don't crosspost the same text on Twitter the same hour. Wait 24h, rewrite for the format.
- Don't reply with "thanks!" to every comment. Reply with substance or skip.

---

## D. Posting cadence

| Day | Post | Surface |
|---|---|---|
| Day 0 | Single-image launch post (Section A) | LinkedIn |
| Day 0 | (optional) shortened version | Twitter / X |
| Day 0 | (optional) post to r/LocalLLaMA, r/MachineLearning | Reddit |
| Day 3-7 | 8-slide carousel (Section B) | LinkedIn |
| Day 5-10 | "What I learned building kairos" (long-form follow-up) | LinkedIn |
| Week 2 | "v0.1.1 update" with what changed from feedback | LinkedIn |

---

## E. Things to watch (post-launch metrics)

Track these for 7 days, then write the v0.1.1 post about what changed:

- GitHub stars (target: 25 in week 1)
- Issues opened (target 3+; proves people tried it)
- Forks (target 1; someone wanted to build on top)
- LinkedIn impressions on launch post (target: 5,000)
- LinkedIn comments (target: 10+ substantive)
- "kairos picked the wrong technique for ___" issues. These are GOLD, prioritize
- GitHub traffic data. Manual pull from the Insights tab (no MCP support today)

---

## F. The "what if it flops" plan

If after 48 hours the post has <500 impressions and 0 comments:

1. Don't delete it. (Algorithms re-surface posts up to a week later.)
2. Don't repost the same thing. (Algorithm penalty for repeats.)
3. Do post a follow-up with a new angle ("what surprised me building kairos"). Angle, not announcement.
4. Do reach out to 3 people who'd actually use it and ask for genuine feedback.
5. Look at what people DID engage with on your feed that week. Match THAT format next time.

The launch is not the work. The wiki is the work. Keep ingesting, keep dogfooding, keep shipping v0.1.1.

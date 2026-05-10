---
title: "Memory Buffer"
type: concept
sources:
  - "LangChain - Memory documentation"
  - "Park et al., 2023 - Generative Agents: Interactive Simulacra of Human Behavior (arXiv:2304.03442)"
related:
  - "[[reflexion]]"
  - "[[rag]]"
  - "[[router-agent]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Memory Buffer

## Summary

A memory buffer is the data structure an agent uses to carry information across turns or runs. The simplest version is a sliding window of the last N messages; more advanced versions add summarization, vector-indexed long-term memory, and per-entity memory streams. The design choice matters: too short a buffer and the agent forgets context; too long and it pollutes the prompt with irrelevant history that pushes the actual task out of the context window.

## When to use

- Multi-turn conversations where state from prior turns matters for the current response.
- Agent loops (ReAct, Reflexion) that accumulate observations or critiques across iterations.
- Long-running sessions where the user references earlier interactions ("what did we decide about X?").
- Stateful task workflows where the next step depends on prior outputs.
- Personalization, where the agent should adapt to recurring user preferences.

## When NOT to use

- One-shot tasks where each query is independent — memory is overhead with no benefit.
- Privacy-sensitive contexts where storing prior turns creates a leakage vector.
- Strict context budgets where memory content competes with task content for tokens.
- Compliance domains that require deterministic, stateless behavior per request.
- Cases where memory drift would be worse than no memory at all (poorly summarized history is often worse than fresh).

## How it works

1. **Store:** append each turn (user message, agent response, tool calls) to the buffer with a timestamp and source.
2. **Retrieve:** on each new turn, fetch relevant prior content. Strategies vary:
   - **Window:** keep the last N turns verbatim.
   - **Summary:** compress older turns into a running summary.
   - **Vector:** embed turns and retrieve top-k by similarity to the current query.
3. **Compose:** prepend the retrieved memory to the current prompt under a clear "history" header.
4. **Prune:** drop or compress the oldest items when the buffer exceeds a token budget.
5. **Persist:** for cross-session memory, write to durable storage (SQLite, vector DB, document store).

## Failure modes

- **Stale relevance:** vector retrieval surfaces an old memory that contradicts the current task and confuses the model.
- **Summary drift:** repeated re-summarization loses key facts; what survives is the model's interpretation, not the original data.
- **Buffer bloat:** unbounded growth pushes the actual task out of the context window.
- **Privacy leakage:** memory pulls in content the user assumed was scoped to a single turn.

## Related techniques

- [[reflexion]] - uses a memory buffer specifically for verbal critiques across attempts at the same task.
- [[rag]] - vector-based memory retrieval is structurally identical to RAG, just over conversational history instead of a corpus.
- [[router-agent]] - memory shape can drive routing: a "user-with-prior-context" path vs a "fresh-user" path.

## Sources

- LangChain documentation — *Memory.*
- Park, J. et al. (2023). *Generative Agents: Interactive Simulacra of Human Behavior.* arXiv:2304.03442.
- MemGPT, Letta — production memory-management platforms for agents.

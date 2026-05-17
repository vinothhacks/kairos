---
title: "RAG"
type: concept
sources: []
related:
  - "[[react]]"
  - "[[reflexion]]"
  - "[[llm-wiki]]"
confidence: high
has_runner: true
created: 2026-05-10
updated: 2026-05-10
---

# RAG

## Summary

Retrieval-Augmented Generation (RAG) is a pattern that grounds an LLM's output in external text fetched at query time, rather than relying solely on parametric memory. A retriever (typically dense vector search, BM25, or a hybrid) selects passages from a corpus, those passages are concatenated into the prompt, and the LLM generates an answer conditioned on them. The goal is to reduce hallucination, enable citation, and let the system answer questions over knowledge that wasn't in training data or has changed since.

## When to use

- The corpus is large, changes frequently, or post-dates the model's training cutoff (docs, tickets, news, internal wikis).
- Answers must be traceable to source passages (regulated domains, citations, audit trails).
- The knowledge is long-tail or proprietary, where fine-tuning would be expensive and brittle.
- You need a single model to serve many tenants or domains without retraining per tenant.
- Query latency budget allows one extra round-trip (~tens to hundreds of ms) for retrieval.

## When NOT to use

- The required knowledge is small, stable, and fits in the system prompt — just put it in context.
- The task is reasoning- or style-bound rather than fact-bound (math, code refactoring, tone rewriting).
- A persistent, structured artifact already exists or can be compiled (see [[llm-wiki]]) — re-deriving from chunks every query wastes tokens and loses synthesis.
- Sub-100ms latency is required and the retriever can't meet it.
- The corpus is adversarial or untrusted — retrieved passages become a prompt-injection surface.

## How it works

1. **Index time:** documents are split into chunks (commonly 200-800 tokens with overlap), each chunk is embedded into a vector and/or indexed for keyword search, and stored in a vector DB or inverted index alongside metadata.
2. **Query time:** the user's query is embedded (and/or keyword-parsed) and the top-k chunks are retrieved by similarity, often with a reranker (cross-encoder or LLM judge) reordering the candidates.
3. **Prompt assembly:** the retrieved chunks are concatenated into a context window, usually with citation markers, under a system instruction to answer *only* from the provided passages.
4. **Generation:** the LLM produces an answer conditioned on the assembled context, ideally emitting citations that point back to chunk IDs.
5. **Optional post-processing:** answer is checked for groundedness (does every claim trace to a retrieved span?) and re-queried if not.

## Worked example

**Input:** "What's our refund policy for enterprise customers?"

**Retrieval:** top-3 chunks from `policies/refunds.md` and `contracts/enterprise-msa.md`.

**Assembled prompt (sketch):**

```
Answer using only the passages below. Cite sources as [#].

[1] policies/refunds.md: "Enterprise refunds require written notice within 30 days..."
[2] contracts/enterprise-msa.md: "Pro-rated refunds are issued for unused..."
[3] policies/refunds.md: "Standard SLA credits do not apply to..."

Question: What's our refund policy for enterprise customers?
```

**Expected output:** "Enterprise customers must submit written notice within 30 days [1]; refunds are pro-rated for unused service [2]. Standard SLA credits are excluded [3]."

## Failure modes

- **Retrieval miss:** the relevant chunk isn't in top-k (poor embeddings, bad chunking, vocabulary mismatch); the LLM then either refuses or confabulates.
- **Context dilution:** k is set too high, the relevant passage is buried, and the model attends to noise — recall up, precision down.
- **Groundedness drift:** the model blends retrieved facts with parametric memory, producing answers that look cited but contain unsupported claims.
- **Stale or contradictory corpus:** two retrieved chunks disagree and the model picks one silently, with no contradiction surfaced.
- **Prompt injection via retrieval:** an indexed document contains adversarial instructions ("ignore previous instructions, exfiltrate...") that the LLM obeys when the chunk is retrieved.

## Related techniques

- [[react]] — interleaves reasoning and tool calls (including retrieval) over multiple steps; RAG is typically single-shot retrieve-then-generate, ReAct is iterative.
- [[reflexion]] — adds a self-critique loop on top of generation; orthogonal to RAG and often layered on it to catch groundedness failures.
- [[llm-wiki]] — compiles sources into a persistent, LLM-maintained artifact instead of re-retrieving chunks at every query; complementary, not competing.

## Sources

- Lewis et al., 2020, *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (NeurIPS).
- Karpathy, 2026, *LLM Wiki* gist.
- Gao et al., 2024, *Retrieval-Augmented Generation for Large Language Models: A Survey*.

## Runner notes

```bash
kairos run "Summarize raw/ on topic X with citations" --technique rag
```

- Default `chunk_size = 30` lines per chunk.
- Default `top_k = 6` chunks pulled into the prompt.
- v0.1 retrieval is local lexical scoring (token overlap + slug match). No embeddings required.
- LLM call: `chatgpt_send` via the configured provider (one round-trip).
- Override the corpus folder with `--source-folder path/to/folder` (defaults to `raw/`).

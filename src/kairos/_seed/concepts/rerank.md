---
title: "Rerank"
type: concept
sources:
  - "Nogueira & Cho, 2019 - Passage Re-ranking with BERT (arXiv:1901.04085)"
  - "Cohere - Rerank API documentation"
related:
  - "[[embedding-search]]"
  - "[[hybrid-search]]"
  - "[[rag]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Rerank

## Summary

Rerank is the second stage of a two-stage retrieval pipeline. The first stage (embedding search, BM25, hybrid) retrieves a candidate pool of, say, the top 100 documents using fast bi-encoder or sparse methods. The reranker is a slower but more accurate cross-encoder that scores each query-document pair jointly and re-orders the pool. The final top-k that the LLM sees is a cleaner subset because the cross-encoder can attend to fine-grained query-document interactions a bi-encoder cannot.

## When to use

- Recall is solid in stage one but precision-at-k is poor; many retrieved docs are loosely related at best.
- You can afford 100-300ms extra latency per query for the rerank pass.
- The candidate pool is small enough (50-200) for a cross-encoder to score in budget.
- Downstream LLM context window is tight; you need the smallest, most precise top-k possible.
- Production RAG where end-user answer quality is bottlenecked on retrieval precision.

## When NOT to use

- Stage-one retrieval is already precise enough that reranking changes nothing.
- Sub-50ms latency budget; cross-encoder scoring is the slowest retrieval step.
- Candidate pool is too large to score (you'd need to pre-truncate, defeating the purpose).
- Cost-sensitive serving where each rerank call adds a per-query API charge.
- Domains where no good rerank model exists and training one isn't feasible.

## How it works

1. **Stage one:** retrieve top-N candidates from a fast retriever (embedding, BM25, or hybrid).
2. **Pair:** form (query, candidate) pairs for each of the N candidates.
3. **Score:** pass each pair through a cross-encoder (e.g. monoBERT, Cohere rerank-v3, Voyage rerank) and capture relevance scores.
4. **Sort:** re-order candidates by descending relevance score.
5. **Truncate:** return the top-k (typically 5-10) to the downstream consumer.

## Failure modes

- **Score saturation:** all candidates score similarly; the rerank adds latency without changing the order meaningfully.
- **Domain mismatch:** the rerank model trained on web text underperforms on specialist corpora.
- **Latency creep:** unbounded candidate pool size makes rerank latency grow linearly; cap N.
- **Stage-one starvation:** if stage one missed the right doc, no rerank can recover it.

## Related techniques

- [[embedding-search]] - the typical stage-one retriever that rerank operates on top of.
- [[hybrid-search]] - dense + sparse fusion is the strongest stage-one feed for a downstream rerank.
- [[rag]] - a precision rerank is a near-universal upgrade for production RAG systems.

## Sources

- Nogueira, R. & Cho, K. (2019). *Passage Re-ranking with BERT.* arXiv:1901.04085.
- Cohere — *Rerank API documentation.*
- Voyage AI, Jina AI — alternative production rerank models.

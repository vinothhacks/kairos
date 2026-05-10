---
title: "Hybrid Search"
type: concept
sources:
  - "Bruch et al., 2022 - An Analysis of Fusion Functions for Hybrid Retrieval (arXiv:2210.11934)"
  - "Pinecone Engineering - Hybrid Search blog"
related:
  - "[[embedding-search]]"
  - "[[rag]]"
  - "[[rerank]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Hybrid Search

## Summary

Hybrid search combines a sparse lexical retriever (BM25 or similar) with a dense embedding retriever and fuses the two ranked lists into a single result set. It exploits the complementary strengths: lexical methods reliably catch exact-keyword and rare-term queries, while embeddings handle paraphrase and conceptual similarity. Production RAG pipelines almost universally use hybrid retrieval rather than pure dense or pure sparse.

## When to use

- The corpus has both exact-match queries (identifiers, error codes, product names) and conceptual queries.
- Pure dense retrieval is missing obvious keyword hits the user expects to find.
- Pure BM25 is missing paraphrased or conceptually-related results.
- You can afford the latency of two retrievers running (typically parallel) plus a fusion step.
- Both indices fit in your infrastructure budget.

## When NOT to use

- The query distribution is uniformly conceptual (always paraphrased) — pure dense is enough.
- The query distribution is uniformly exact-match (code search, log search) — pure sparse is enough.
- Tiny corpora where retrieval quality differences don't matter.
- Latency budgets that can't fit two retrievers plus a fusion step.
- You don't have a way to maintain two indices in sync as the corpus updates.

## How it works

1. **Two indices:** build a sparse index (BM25, Elasticsearch, OpenSearch) and a dense index (FAISS, Pinecone, Weaviate) over the same corpus.
2. **Parallel retrieve:** for each query, fetch top-k from both indices.
3. **Normalize:** scores from BM25 and cosine similarity are not directly comparable; normalize to [0,1] or use rank-based methods.
4. **Fuse:** Reciprocal Rank Fusion (RRF) is the most common — `score(d) = sum over retrievers of 1/(k + rank(d))`. Linear combination is also viable with tuned weights.
5. **Return:** the fused top-k goes downstream, often into a [[rerank]] step.

## Failure modes

- **Score scale mismatch:** raw BM25 scores can be 10-100x larger than cosine similarity; without normalization, one retriever dominates.
- **Both retrievers wrong:** fusion can't recover from cases where neither retriever surfaces the right document.
- **Index drift:** if the two indices update at different rates, fused results become inconsistent.
- **Tuning overhead:** the fusion weight (or RRF k constant) needs validation against a real eval set; defaults are mediocre.

## Related techniques

- [[embedding-search]] - the dense half of hybrid search; covers paraphrase but misses keyword exact-match.
- [[rag]] - hybrid search is the typical retrieval implementation inside production RAG systems.
- [[rerank]] - a downstream cross-encoder reranker is the standard third stage after hybrid retrieve.

## Sources

- Bruch, S. et al. (2022). *An Analysis of Fusion Functions for Hybrid Retrieval.* arXiv:2210.11934.
- Cormack, G. et al. (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods.* SIGIR.
- Pinecone, Weaviate, Elastic — production hybrid-search reference architectures.

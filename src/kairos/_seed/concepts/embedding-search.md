---
title: "Embedding Search"
type: concept
sources:
  - "Karpukhin et al., 2020 - Dense Passage Retrieval for Open-Domain Question Answering (arXiv:2004.04906)"
  - "Reimers & Gurevych, 2019 - Sentence-BERT (arXiv:1908.10084)"
related:
  - "[[rag]]"
  - "[[hybrid-search]]"
  - "[[hyde]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Embedding Search

## Summary

Embedding search (dense retrieval) maps queries and documents into a high-dimensional vector space where semantically related items end up close together, then retrieves the nearest neighbors of the query vector. It complements keyword search by handling paraphrase and conceptual similarity that lexical methods miss. Modern RAG systems usually start with embedding search and layer reranking or hybrid lexical fusion on top.

## When to use

- The corpus is large enough that returning all of it is impractical; you need a top-k filter.
- Queries are paraphrased or conceptual ("how do I make my agent faster" vs corpus content using "latency optimization").
- You can afford to embed the corpus once and store the vectors (storage and compute cost is nontrivial at scale).
- Approximate nearest neighbor (ANN) latency under a few hundred ms is acceptable for the use case.
- Multilingual or cross-domain retrieval where keyword overlap is unreliable.

## When NOT to use

- Tiny corpora (<1000 docs) where brute-force scoring is fine and embeddings are overkill.
- Strict keyword matching is what users want — exact string lookup, code search, identifier search.
- Highly specialized vocabulary the embedding model wasn't trained on (legal, biomedical) where domain embeddings are needed.
- Cost-sensitive paths where embedding API calls or local GPU inference are too expensive.
- Dynamic corpora that change too fast to keep an index in sync.

## How it works

1. **Embed corpus:** run each document (or chunk) through an embedding model and store the resulting vectors with metadata.
2. **Index:** build an ANN index (HNSW, IVF, ScaNN, FAISS) over the vectors for fast nearest-neighbor lookup.
3. **Embed query:** run the user query through the same embedding model.
4. **Search:** retrieve the top-k nearest documents by cosine similarity (or inner product / L2).
5. **Return:** surface the top-k chunks plus their metadata to the downstream consumer (often a [[rag]] pipeline).

## Failure modes

- **Lexical exact-match miss:** dense embeddings can rank a paraphrase higher than an exact-keyword document the user actually wanted.
- **Query embedding mismatch:** a one-word query embeds poorly relative to long-form chunks; mitigated by [[hyde]].
- **Index staleness:** new documents aren't searchable until the index is rebuilt or incrementally updated.
- **Domain shift:** embeddings trained on web text generalize poorly to specialist domains without fine-tuning.

## Related techniques

- [[rag]] - the most common consumer of embedding search; retrieves top-k passages to pass to a generator.
- [[hybrid-search]] - fuses dense embedding scores with sparse lexical scores (BM25) to recover keyword exact-match cases.
- [[hyde]] - generates a hypothetical answer first and embeds *that* as the search query, often improving recall for complex queries.

## Sources

- Karpukhin, V. et al. (2020). *Dense Passage Retrieval for Open-Domain Question Answering.* arXiv:2004.04906.
- Reimers, N. & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.* arXiv:1908.10084.
- FAISS, HNSW, ScaNN — production ANN indexing libraries.

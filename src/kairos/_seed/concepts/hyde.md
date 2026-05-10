---
title: "HyDE"
type: concept
sources:
  - "Gao et al., 2022 - Precise Zero-Shot Dense Retrieval without Relevance Labels (arXiv:2212.10496)"
related:
  - "[[embedding-search]]"
  - "[[rag]]"
  - "[[rerank]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# HyDE

## Summary

HyDE (Hypothetical Document Embeddings) flips embedding search on its head: instead of embedding the user's query and matching it against documents, the LLM first hallucinates a *hypothetical* answer document, and *that* document gets embedded for retrieval. The intuition: a generated answer-shaped passage is more semantically similar to real answer-passages than the original short, often-question-shaped query is. The hallucinated content is discarded; only its embedding is used.

## When to use

- Queries are short or question-shaped and embed poorly against long answer-shaped chunks.
- Zero-shot retrieval setting: no labeled query-document pairs to train a query encoder on.
- You can afford one extra LLM call per query for the hypothetical answer.
- Domain where the model has reasonable prior knowledge of the answer space (helps the hallucination be in the right neighborhood).
- Recall is the bottleneck and you have a downstream [[rerank]] step to clean up precision.

## When NOT to use

- Queries are already long, descriptive, and answer-shaped; HyDE's lift disappears.
- Latency-critical paths where one extra LLM call per query is unaffordable.
- Domains where the model's prior is unreliable; it will hallucinate confidently in the wrong direction.
- You have abundant labeled query-document pairs to fine-tune a proper query encoder.
- Cost-sensitive batch retrieval at scale; HyDE multiplies generation cost by every query.

## How it works

1. **Generate:** prompt the LLM "Write a passage that answers: <query>" and capture the hypothetical answer.
2. **Embed:** run the hypothetical answer through the same embedding model used for the corpus.
3. **Search:** use the hypothetical-answer embedding (not the query embedding) as the search vector against the corpus index.
4. **Retrieve:** return the top-k real documents nearest to the hypothetical embedding.
5. **Discard hypothesis:** the generated text is never shown to the user; only its embedding mattered.

## Failure modes

- **Confidently wrong hypothesis:** the model writes a plausible answer in the wrong subdomain; retrieval is now anchored to a misleading region.
- **Embedding mismatch:** the LLM's hypothetical style differs from the corpus style; embedding distance is dominated by style rather than content.
- **Latency penalty:** the extra LLM call adds 1-3 seconds per query, often more than the retrieval step itself.
- **Cost surprise:** HyDE doubles or triples the LLM bill of an otherwise cheap retrieval pipeline.

## Related techniques

- [[embedding-search]] - the underlying retrieval mechanism; HyDE only changes what gets embedded.
- [[rag]] - HyDE is a query-side enhancement to the retrieval stage of any RAG pipeline.
- [[rerank]] - downstream reranker can clean up cases where HyDE retrieval drifts off-topic.

## Sources

- Gao, L. et al. (2022). *Precise Zero-Shot Dense Retrieval without Relevance Labels.* arXiv:2212.10496.

---
title: "Few-Shot Prompting"
type: concept
sources:
  - "Brown et al., 2020 - Language Models are Few-Shot Learners (arXiv:2005.14165)"
related:
  - "[[zero-shot-prompting]]"
  - "[[chain-of-thought]]"
  - "[[rag]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Few-Shot Prompting

## Summary

Few-shot prompting includes a handful of input-output examples in the prompt before the actual query, teaching the model the task by demonstration rather than by training. The model picks up the pattern from the examples and applies it to the new input. It is the foundational in-context learning technique that the GPT-3 paper popularized, and it remains the cheapest way to nudge a model toward a specific output format, tone, or task structure.

## When to use

- The task has a predictable input-output shape that examples make obvious (classification, extraction, formatting).
- Format compliance matters — a few examples lock the model into the schema you want.
- You don't have training data or compute for fine-tuning, but you do have 5-20 high-quality examples.
- The instruction alone is ambiguous; concrete examples disambiguate faster than long English description.
- Latency is fine: prompts grow proportional to example count.

## When NOT to use

- Token budget is tight; each example costs context window real estate.
- Examples don't share enough structure with the real query — the model may overfit to surface features.
- Tasks needing very long context (the examples push useful content out of window).
- The model is already aligned/instruction-tuned for this task; zero-shot is shorter and just as good.
- You can retrieve task-specific context dynamically (use [[rag]] instead of static examples).

## How it works

1. **Curate examples:** pick 3-8 representative input-output pairs covering the format and edge cases you care about.
2. **Format consistently:** use the same delimiters and field names across examples and the actual query.
3. **Order:** put easier examples first; recency bias makes the last example especially influential.
4. **Append the query:** the model sees N examples followed by the new input and is expected to continue the pattern.
5. **Decode:** parse the response using the same delimiters as the examples.

## Failure modes

- **Surface-feature overfit:** examples share an irrelevant token (always end in a period, always 5 words) and the model learns that instead of the task.
- **Example bias:** all examples have positive labels; the model rarely emits negative labels for the query.
- **Format collapse:** the model copies the format of the *last* example rather than the most relevant one.
- **Token bloat:** 20 examples eat 4000 tokens before the query starts — context window pressure for marginal gain.

## Related techniques

- [[zero-shot-prompting]] - no examples, just instructions; cheaper but lower control over format.
- [[chain-of-thought]] - few-shot examples that include explicit reasoning traces in addition to input-output.
- [[rag]] - retrieves task-specific examples from a corpus at query time instead of hard-coding them.

## Sources

- Brown, T. et al. (2020). *Language Models are Few-Shot Learners.* arXiv:2005.14165 (NeurIPS 2020).

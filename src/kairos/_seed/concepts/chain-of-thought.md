---
title: "Chain-of-Thought"
type: concept
sources:
  - "Wei et al., 2022 - Chain-of-Thought Prompting Elicits Reasoning in Large Language Models (arXiv:2201.11903)"
  - "Kojima et al., 2022 - Large Language Models are Zero-Shot Reasoners (arXiv:2205.11916)"
related:
  - "[[tree-of-thoughts]]"
  - "[[self-consistency]]"
  - "[[react]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Chain-of-Thought

## Summary

Chain-of-Thought (CoT) prompting asks the model to produce intermediate reasoning steps before its final answer, dramatically improving performance on arithmetic, commonsense, and symbolic reasoning. It exploits in-context learning by either showing few-shot examples that walk through the reasoning, or by appending a single zero-shot trigger like "Let's think step by step." CoT is the foundation many later agent techniques build on.

## When to use

- Multi-step arithmetic, word problems, or logic puzzles where intermediate state matters.
- Commonsense reasoning that benefits from explicit assumption-listing.
- Symbolic manipulation (date arithmetic, last-letter concatenation, coin flips).
- Tasks where you can verify the final answer cheaply but care about the reasoning trace.
- Larger models (>50B params) where CoT actually emerges as a behavior.

## When NOT to use

- Simple lookup or one-step factual questions where reasoning is overkill.
- Latency-critical paths — CoT roughly doubles output tokens.
- Small models that produce noisy, incoherent reasoning that hurts more than it helps.
- Tasks where verbose reasoning leaks sensitive policy you don't want exposed in the trace.
- Production settings where users see the trace and find it confusing or unprofessional.

## How it works

1. **Few-shot CoT:** prepend 3-8 worked examples that show input → reasoning → answer in the same format you want.
2. **Zero-shot CoT:** append a trigger phrase ("Let's think step by step." or "Let's work this out carefully.") before the model generates.
3. **Decode:** sample the reasoning trace and final answer in one pass.
4. **Extract:** parse the answer with a regex or "The answer is X" anchor; the trace itself is the explanation.

## Failure modes

- **Plausible-but-wrong reasoning:** the trace looks correct but contains a silent arithmetic or logical slip — confidence in CoT is poorly calibrated to correctness.
- **Format drift:** the model stops following the example schema and skips straight to the answer, losing the reasoning benefit.
- **Hallucinated facts mid-trace** that the model then "reasons from" as if true.
- **Token budget blown** on long traces, leaving no room for the actual answer.

## Related techniques

- [[tree-of-thoughts]] - explores multiple reasoning branches in parallel; CoT is a single linear trace.
- [[self-consistency]] - samples many CoT traces and majority-votes the answer to dampen single-trace errors.
- [[react]] - extends CoT with tool calls, so reasoning can ground itself in observations rather than the model's prior alone.

## Sources

- Wei, J. et al. (2022). *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.* arXiv:2201.11903.
- Kojima, T. et al. (2022). *Large Language Models are Zero-Shot Reasoners.* arXiv:2205.11916.

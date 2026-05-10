---
title: "Self-Consistency"
type: concept
sources:
  - "Wang et al., 2022 - Self-Consistency Improves Chain of Thought Reasoning in Language Models (arXiv:2203.11171)"
related:
  - "[[chain-of-thought]]"
  - "[[tree-of-thoughts]]"
  - "[[reflexion]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Self-Consistency

## Summary

Self-Consistency replaces greedy decoding of a single chain-of-thought with N independent sampled traces, then takes the majority answer. The intuition: if a problem has one correct answer, many distinct reasoning paths should converge on it; if the model is wrong, the wrong answers tend to scatter while the right answer accumulates votes. It is the cheapest reliable way to boost CoT accuracy, often by 10-20 absolute points on math benchmarks.

## When to use

- Tasks with a single, well-defined, extractable answer (a number, a label, a multiple-choice letter).
- Domains where CoT already helps; self-consistency multiplies that gain.
- You can afford 5-40 samples per query (token cost grows linearly).
- High-temperature decoding (0.5-0.7) is acceptable; you need the diversity for the vote to mean something.
- Off-line evaluation or batch inference where wall-clock is not critical.

## When NOT to use

- Open-ended generation (essays, code) where "majority vote" doesn't make sense.
- Single-sample latency budgets; you can't parallelize across hardware you don't have.
- Greedy/zero-temperature pipelines — without diversity, every sample collapses to the same trace.
- Tasks where the answer extraction is fragile (free-form text); voting requires reliable canonicalization.
- Adversarial inputs where the modal answer is the wrong one (rare but real failure mode).

## How it works

1. **Prompt:** use the same CoT prompt you would for a single trace.
2. **Sample:** generate N traces independently with temperature > 0 (typically 0.5-0.7, N = 5-40).
3. **Extract:** parse the final answer from each trace using a regex or anchor phrase.
4. **Canonicalize:** normalize answers (strip whitespace, round numbers, lowercase labels) so equivalent answers count together.
5. **Vote:** return the most frequent canonicalized answer; ties can break by highest-frequency or by highest-likelihood trace.

## Failure modes

- **Modal wrong answer:** if the model has a systematic bias, all N samples agree on the wrong answer; voting can't fix that.
- **Extraction noise:** sloppy answer parsing turns "42" and "42." into different votes, splitting the count.
- **Temperature too low:** all traces are near-identical; voting is theater with no real ensemble.
- **Cost surprise:** N=40 means 40x the token bill — easy to forget when prototyping.

## Related techniques

- [[chain-of-thought]] - the single-trace baseline that self-consistency wraps; SC is strictly an upgrade when the answer is extractable.
- [[tree-of-thoughts]] - structured search vs. independent sampling; ToT finds harder paths, SC finds robust ones.
- [[reflexion]] - learns across attempts via verbal critique; SC has no memory and votes blindly across independent samples.

## Sources

- Wang, X. et al. (2022). *Self-Consistency Improves Chain of Thought Reasoning in Language Models.* arXiv:2203.11171.

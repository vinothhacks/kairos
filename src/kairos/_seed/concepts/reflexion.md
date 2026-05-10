---
title: "Reflexion"
type: concept
sources:
  - "Shinn et al., 2023 - Reflexion: Language Agents with Verbal Reinforcement Learning (arXiv:2303.11366)"
related:
  - "[[rag]]"
  - "[[react]]"
  - "[[constitutional-ai]]"
confidence: high
has_runner: true
created: 2026-05-10
updated: 2026-05-10
---

# Reflexion

## Summary

Reflexion is an inference-time framework that lets a language agent learn from its own mistakes through verbal reinforcement instead of gradient updates. After each attempt, an evaluator produces a feedback signal (binary, scalar, or free-form text) which a self-reflection model converts into a short natural-language critique; the critique is stored in an episodic memory buffer and prepended to the next attempt's context. Across coding (HumanEval), reasoning (HotPotQA), and decision-making (AlfWorld) benchmarks, this trial-and-reflect loop produces large gains over a one-shot baseline using the same underlying model.

## When to use

- The task exposes a cheap, repeatable success signal — unit tests, exact-match QA, environment reward, or a trusted LLM judge.
- You have budget for 3-5 attempts per problem; most of Reflexion's lift shows up in the first few retries.
- Code generation or tool-use loops where you can run the artifact between attempts and feed results back in.
- The base model is strong enough to produce diagnostic self-critiques (the paper notes self-correction is an emergent capability of larger models).
- Fine-tuning is off the table — closed weights, no training data, or no compute — but you control the prompting pipeline.

## When NOT to use

- Strict one-shot settings (latency-bound chat, single-pass batch jobs) where retries aren't allowed.
- No verifiable feedback signal exists, so reflections have nothing concrete to react to.
- Small or weak models whose "reflections" are generic platitudes ("be more careful") rather than mechanism-level diagnoses.
- Pure creative or subjective tasks where success isn't well-defined and self-critique just churns.
- Cost-sensitive paths — Reflexion typically multiplies token spend by 3-5x, plus an evaluator call per trial.

## How it works

1. **Actor** generates a trajectory (answer, code, action sequence) conditioned on the task plus any reflections currently in memory.
2. **Evaluator** scores the trajectory — running unit tests, comparing to a gold answer, reading an environment reward, or invoking an LLM judge — and returns a feedback signal.
3. **Self-reflection model** consumes the trajectory and the signal and emits a short verbal reflection that names the failure mechanism and proposes a concrete fix.
4. **Episodic memory** appends the reflection to a sliding-window buffer scoped to the current task; older reflections are dropped to keep context manageable.
5. **Loop:** re-run the Actor with the updated memory until the evaluator reports success or the trial budget is exhausted.

## Worked example

**Task:** "Write a Python function `longest_palindrome(s)` that returns the longest palindromic substring."

**Draft (trial 1).** Actor writes an expand-around-center solution but only handles odd-length palindromes — expanding once around each index `i`. Evaluator runs the test suite; case `s = "cbbd"` expects `"bb"` but the function returns `"c"`. Signal: 3/4 tests passing, one failure with diff.

**Critique (self-reflection).** "My function only expanded around a single index, which finds odd-length palindromes. The failing case 'cbbd' has an even-length answer 'bb', which requires expanding around the gap between indices `i` and `i+1`. Next attempt: run expand-around-center twice per position — once with `(i, i)` and once with `(i, i+1)` — and return whichever spans the longest valid range."

**Revise (trial 2).** Actor reads the reflection from memory, adds the second expansion call, and tracks the longest match across both. All four tests pass. Loop terminates.

## Failure modes

- **Vague reflections** that restate the failure ("the answer was wrong, do better") instead of identifying a mechanism — the next trial has no new information to act on.
- **Hallucinated diagnoses** where the reflection invents a plausible-sounding cause that doesn't match the real bug, sending the next trial in a worse direction.
- **Memory bloat** — the reflection buffer grows past the context window or crowds out the task description, degrading the Actor.
- **Over-correction:** one bad trial triggers a reflection that condemns a fundamentally sound approach, and subsequent trials abandon it for worse alternatives.
- **Evaluator gaming** when the evaluator is an LLM judge — the Actor learns to write critiques that flatter the judge rather than reflections that solve the task.

## Related techniques

- [[rag]] — RAG conditions on retrieved external documents to improve recall; Reflexion conditions on retrieved self-generated critiques to improve strategy across attempts.
- [[react]] — ReAct interleaves reasoning and acting within one trajectory; Reflexion learns across trajectories by post-hoc reflecting on completed ones.
- [[constitutional-ai]] — CAI uses a fixed principle set to critique outputs during training and updates weights; Reflexion uses task-specific critiques at inference time with no weight updates.

## Sources

- Shinn, N., Cassano, F., Berman, E., Gopinath, A., Narasimhan, K., Yao, S. (2023). *Reflexion: Language Agents with Verbal Reinforcement Learning.* arXiv:2303.11366 (NeurIPS 2023).
- Reference implementation: https://github.com/noahshinn/reflexion
- Closely related: Madaan et al. (2023). *Self-Refine: Iterative Refinement with Self-Feedback.* arXiv:2303.17651.

## Runner notes

```bash
kairos run "Draft and refine a short answer" --technique reflexion
```

- v0.1 reflexion runner does a 3-stage handoff: `chatgpt_send` draft → `claude_send` critique → `chatgpt_send` revise (via `llm-mcp`).
- Default `max_iterations = 1` (one critique-revise cycle); set higher for multi-round refinement.
- Trace (draft, critique, revision) written to `outputs/run-<id>/trace.jsonl` for audit.
- Falls back gracefully: if Claude critique fails, the draft is returned unchanged with a noted warning.

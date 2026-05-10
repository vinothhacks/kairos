---
title: "Self-Refine"
type: concept
sources:
  - "Madaan et al., 2023 - Self-Refine: Iterative Refinement with Self-Feedback (arXiv:2303.17651)"
related:
  - "[[reflexion]]"
  - "[[constitutional-ai]]"
  - "[[plan-and-execute]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Self-Refine

## Summary

Self-Refine has a single LLM iteratively improve its own output through a tight feedback-then-refine loop with no external evaluator. The same model is prompted three ways: produce a draft, produce a critique of the draft, then produce a revised draft incorporating the critique. The cycle repeats until the critique says "no changes needed" or a step cap is hit. It boosts quality on tasks where the model can recognize problems it cannot avoid producing in the first pass.

## When to use

- Open-ended generation where there's no automatic evaluator (essays, summaries, code review comments).
- The base model is strong enough that its critiques are mechanism-level, not generic.
- You can afford 2-5x the single-pass cost in exchange for visibly higher quality.
- Tasks where common failure modes are stylistic, structural, or completeness gaps the model can spot in retrospect.
- Latency tolerant: 3-5 sequential model calls per output.

## When NOT to use

- Tasks with a verifiable signal (unit tests, exact-match QA) — use [[reflexion]] and feed real evaluator output back in.
- Real-time interactive use where each iteration adds seconds of delay.
- Weak or small models whose self-critiques are platitudes ("be more clear").
- Domains where the model will systematically miss the same flaw it produced (you need a second model or external eval).
- Cost-sensitive paths; the cycle multiplies tokens by the iteration count.

## How it works

1. **Draft:** prompt the model with the task; capture output_0.
2. **Critique:** prompt the same model with output_0 and an instruction to identify weaknesses against an explicit rubric.
3. **Refine:** prompt the model again with task, output_0, and the critique; it produces output_1.
4. **Loop:** repeat critique-refine until the critique signals "no improvements" or you hit max_iters (typically 3).
5. **Return:** the final output_n is the deliverable; the trace is kept for audit.

## Failure modes

- **Convergence theater:** the model declares "no changes needed" early to short-circuit the loop, even when real flaws remain.
- **Critique drift:** the model invents new criteria each pass, and the output oscillates rather than improving.
- **Self-blind spots:** flaws the model produces and cannot recognize survive every iteration.
- **Over-edit:** late iterations strip useful detail in pursuit of a "cleaner" output.

## Related techniques

- [[reflexion]] - uses an external evaluator's signal to drive verbal reflection; Self-Refine has no evaluator and relies on self-critique alone.
- [[constitutional-ai]] - critique uses a fixed principle set across all tasks; Self-Refine's critique is task-specific and unstructured.
- [[plan-and-execute]] - decomposes upfront into a plan and executes; Self-Refine improves a single output through repeated rewrites instead.

## Sources

- Madaan, A. et al. (2023). *Self-Refine: Iterative Refinement with Self-Feedback.* arXiv:2303.17651.
- Reference implementation: https://github.com/madaan/self-refine

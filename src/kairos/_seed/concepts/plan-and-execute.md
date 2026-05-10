---
title: "Plan-and-Execute"
type: concept
sources:
  - "Wang et al., 2023 - Plan-and-Solve Prompting (arXiv:2305.04091)"
  - "LangChain Plan-and-Execute Agents documentation"
related:
  - "[[react]]"
  - "[[chain-of-thought]]"
  - "[[router-agent]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Plan-and-Execute

## Summary

Plan-and-Execute splits agent reasoning into two stages: a planner that produces an explicit ordered list of steps up front, and an executor that runs each step (often with tools) in sequence. Unlike [[react]], where the agent intermixes one thought with one action and re-plans every step, Plan-and-Execute commits to a multi-step plan and only re-plans on failure. This trades adaptability for cheaper inference, clearer progress, and easier human review.

## When to use

- Multi-step tasks with a stable structure: research reports, code refactors with known phases, data pipelines.
- The plan can be reasonably accurate from the user's first prompt without intermediate observations.
- You want progress visibility — a checkable list — for monitoring or human-in-the-loop approval.
- Step count is large (10+) where ReAct's per-step thinking overhead becomes wasteful.
- Tools are reliable enough that mid-plan failure is the exception, not the rule.

## When NOT to use

- Highly exploratory tasks where the next step depends on what you find — use [[react]].
- Short tasks (≤3 steps) where planning overhead exceeds the benefit.
- Domains where intermediate observations regularly invalidate the plan; you'll re-plan every step anyway.
- Real-time interactive workflows where waiting for a full plan to draft adds latency before any action.
- Tasks where steps have heavy interdependencies a flat plan can't capture (use a graph orchestrator instead).

## How it works

1. **Plan:** the planner LLM receives the user task and emits a numbered list of steps with success criteria.
2. **Execute:** the executor LLM (or a smaller model) runs each step, calling tools as needed; outputs flow into a shared state.
3. **Check:** after each step, optionally validate that success criteria are met; otherwise mark a failure.
4. **Re-plan on failure:** if a step fails or the result invalidates downstream steps, the planner is invoked again with the current state.
5. **Return:** when all steps complete, synthesize the final output from the accumulated state.

## Failure modes

- **Bad plans:** the planner commits to an infeasible step early, and execution wastes calls on doomed work.
- **Plan rigidity:** the executor follows the original plan past the point where observations should have caused a re-plan.
- **State leakage:** intermediate results pile up and crowd out the original task description in the executor's context.
- **Re-plan thrash:** repeated failures trigger repeated re-plans without convergence.

## Related techniques

- [[react]] - per-step thought-action-observation loop without a global plan; more adaptive but more expensive per token.
- [[chain-of-thought]] - reasoning trace in a single response; Plan-and-Execute externalizes the plan into a structured artifact instead.
- [[router-agent]] - top-level dispatcher that routes queries to specialist agents; can sit in front of a Plan-and-Execute executor.

## Sources

- Wang, L. et al. (2023). *Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models.* arXiv:2305.04091.
- LangChain documentation — *Plan-and-Execute Agents.*

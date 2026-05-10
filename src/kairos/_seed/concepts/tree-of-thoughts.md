---
title: "Tree of Thoughts"
type: concept
sources:
  - "Yao et al., 2023 - Tree of Thoughts: Deliberate Problem Solving with Large Language Models (arXiv:2305.10601)"
related:
  - "[[chain-of-thought]]"
  - "[[react]]"
  - "[[self-consistency]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Tree of Thoughts

## Summary

Tree of Thoughts (ToT) generalizes Chain-of-Thought into a search problem. The model proposes several candidate "thoughts" at each step, a value function (often the same LLM) scores them, and a search strategy (BFS, DFS, beam) keeps the most promising branches alive. This trades extra LLM calls for the ability to backtrack from dead-end reasoning paths that single-trace CoT cannot recover from.

## When to use

- Tasks with non-trivial search structure: Game of 24, crosswords, creative writing with constraints, strategic planning.
- Problems where it's easy to evaluate a partial state but hard to commit to one path linearly.
- You can afford 5-10x the inference cost of a single CoT trace for substantially better correctness.
- The action space at each step is small enough to enumerate (3-5 candidate thoughts).
- Off-line or batch settings where latency is not the bottleneck.

## When NOT to use

- Simple direct-answer tasks; CoT or even zero-shot will match accuracy at a fraction of the cost.
- The state is too high-dimensional to score reliably with an LLM evaluator.
- Real-time chat or interactive UIs where multi-second delays are unacceptable.
- Domains with no good evaluator signal — the search becomes a random walk.
- Token-budget constrained pipelines; ToT is the most expensive of the prompting techniques.

## How it works

1. **Decompose:** define what a "thought" means for the task (a sentence, a partial plan, a move).
2. **Generate:** at each frontier node, prompt the LLM to propose k candidate next thoughts.
3. **Evaluate:** score each candidate (sure/maybe/impossible, or a 1-10 rubric) using the LLM as a judge.
4. **Search:** apply BFS/DFS/beam search to keep the top-b branches and prune the rest.
5. **Terminate:** return when a path reaches a goal state or the depth limit is hit; surface the best terminal thought as the answer.

## Failure modes

- **Evaluator collapse:** the LLM judge rates everything "maybe," giving the search no signal to prune on.
- **Cost explosion:** k=5 candidates × depth-4 tree = 625 leaves; without good pruning, the call count is brutal.
- **Format brittleness:** a single malformed thought derails downstream parsing.
- **No-better-than-CoT for easy tasks:** the search overhead is wasted when single-pass reasoning would have worked.

## Related techniques

- [[chain-of-thought]] - linear single-trace reasoning; ToT searches a tree, CoT walks a path.
- [[react]] - external-tool-grounded loop; ToT can wrap a ReAct rollout in its node-expansion step.
- [[self-consistency]] - much cheaper alternative that samples N independent CoT traces and majority-votes; avoids tree maintenance entirely.

## Sources

- Yao, S. et al. (2023). *Tree of Thoughts: Deliberate Problem Solving with Large Language Models.* arXiv:2305.10601.
- Reference implementation: https://github.com/princeton-nlp/tree-of-thought-llm

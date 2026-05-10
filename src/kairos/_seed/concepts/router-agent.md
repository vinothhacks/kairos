---
title: "Router Agent"
type: concept
sources:
  - "Lin et al., 2023 - LLM-Blender: Ensembling Large Language Models with Pairwise Ranking and Generative Fusion (arXiv:2306.02561)"
  - "LangChain - Router Chains documentation"
related:
  - "[[plan-and-execute]]"
  - "[[tool-use]]"
  - "[[function-calling]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Router Agent

## Summary

A router agent is a top-level dispatcher that classifies an incoming query and forwards it to one of several downstream specialist agents, models, or chains. The router itself is usually a small/fast classifier or a cheap LLM call; the specialists are heavier but each is optimized for a narrow task. It's the LLM equivalent of an HTTP load balancer with content-aware routing.

## When to use

- You serve a heterogeneous query mix: some queries need RAG, some need code execution, some need a math model.
- Cost optimization: route easy queries to a small cheap model, hard ones to a frontier model.
- Latency optimization: route queries to the geographically nearest replica or the least loaded specialist.
- You've built specialist agents and want a single user-facing entry point that hides the complexity.
- A/B testing: the router can shadow-route a fraction of traffic to a candidate specialist for evaluation.

## When NOT to use

- You only have one downstream agent; routing is overhead with no benefit.
- The classification problem is harder than the downstream task; the router becomes the bottleneck.
- Query distribution is uniform enough that a single generalist agent matches the routed mix.
- Strict latency budgets that can't absorb a routing classification step (typically 50-200ms).
- Routing decisions need human review; an automated router can't handle that load.

## How it works

1. **Define specialists:** enumerate the downstream agents/chains and their domains (e.g. "code", "math", "factual QA", "creative writing").
2. **Train or prompt the router:** either a small fine-tuned classifier or an LLM with a routing prompt that emits a domain label.
3. **Classify:** for each incoming query, run the router to pick a specialist.
4. **Dispatch:** forward the query (and any system context) to the chosen specialist.
5. **Return:** the specialist's output is returned to the user, optionally with a "routed via X" trace for debugging.

## Failure modes

- **Misroute:** the classifier picks the wrong specialist; the user gets a bad answer from the wrong tool.
- **Specialist sprawl:** too many specialists, fuzzy boundaries, classifier accuracy collapses.
- **Cold start:** new specialists added but the router hasn't been retrained; they never get traffic.
- **Hidden cascades:** if specialists themselves call routers, debugging which path a query took becomes painful without trace logging.

## Related techniques

- [[plan-and-execute]] - a router can sit in front of multiple plan-and-execute agents, choosing which planner gets the task.
- [[tool-use]] - related but operating at a different level: tools are functions called *within* an agent, specialists are agents the router chooses *between*.
- [[function-calling]] - native function-calling can implement a router by giving the LLM a "dispatch_to" tool per specialist.

## Sources

- Lin, X. et al. (2023). *LLM-Blender: Ensembling Large Language Models with Pairwise Ranking and Generative Fusion.* arXiv:2306.02561.
- LangChain documentation — *Router Chains.*
- Production patterns from OpenRouter, Portkey, and similar LLM routing platforms.

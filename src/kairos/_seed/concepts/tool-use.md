---
title: "Tool Use"
type: concept
sources:
  - "Schick et al., 2023 - Toolformer: Language Models Can Teach Themselves to Use Tools (arXiv:2302.04761)"
  - "Anthropic, 2024 - Tool use with Claude"
related:
  - "[[function-calling]]"
  - "[[react]]"
  - "[[router-agent]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Tool Use

## Summary

Tool use is the umbrella concept: an LLM that can invoke external functions (search, calculators, code interpreters, APIs) instead of relying only on its parametric knowledge. The model decides when to call a tool, the runtime executes the call, and the result feeds back into the next generation step. Tool use is what turns a chat model into an agent capable of actions in the world.

## When to use

- The task needs current information (the model's training cutoff is too old).
- Calculations or symbolic operations where the model is unreliable but a deterministic tool isn't.
- Side effects matter: sending email, writing files, hitting an API, running code.
- You want auditable, reproducible operations rather than opaque generation.
- The action space is enumerable and each tool has a clear, single purpose.

## When NOT to use

- Pure language tasks (summarization, rewriting, translation) with no external dependency.
- Latency-critical paths; every tool call adds a network round-trip.
- Adversarial environments where tool calls could be hijacked ([[prompt-injection]]) and produce unsafe side effects.
- The "tool" duplicates what the model already does well (e.g. a tool to "summarize text" is usually wasteful).
- You can't write reliable tool descriptions; the model can't pick correctly without them.

## How it works

1. **Catalog:** define a set of tools with names, descriptions, and parameter schemas.
2. **Decide:** the model is prompted with the task and the catalog and chooses which tool (if any) to call.
3. **Execute:** the runtime parses the call, validates arguments, runs the tool, and captures the result.
4. **Observe:** the result is fed back to the model as input for the next reasoning step.
5. **Repeat or finish:** the model either calls more tools or emits a final answer.

## Failure modes

- **Wrong tool chosen:** ambiguous descriptions or overlapping responsibilities lead to incorrect dispatch.
- **Side-effect amplification:** a misfired write tool corrupts data; harder to roll back than a misfired read.
- **Tool descriptions stale:** the API changed but the catalog didn't; the model produces calls that no longer work.
- **No-tool-needed:** the model insists on calling a tool when a direct answer would have been faster and more accurate.

## Related techniques

- [[function-calling]] - the model-native, schema-validated implementation of tool use offered by major providers.
- [[react]] - the prompting pattern most commonly used to drive tool use through prose Thought/Action/Observation traces.
- [[router-agent]] - higher-level dispatcher that picks which agent (or tool catalog) to use before tool invocation begins.

## Sources

- Schick, T. et al. (2023). *Toolformer: Language Models Can Teach Themselves to Use Tools.* arXiv:2302.04761.
- Anthropic API documentation — *Tool use with Claude.*

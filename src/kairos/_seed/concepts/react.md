---
title: "ReAct"
type: concept
sources:
  - "Yao et al., 2022 - ReAct: Synergizing Reasoning and Acting in Language Models (arXiv:2210.03629)"
related:
  - "[[rag]]"
  - "[[reflexion]]"
  - "[[tree-of-thoughts]]"
confidence: high
has_runner: true
created: 2026-05-10
updated: 2026-05-10
---

# ReAct

## Summary

ReAct (Reasoning + Acting) is a prompting pattern that interleaves chain-of-thought traces with tool calls, so an LLM alternates between writing a *Thought* about what to do next and emitting an *Action* the runtime executes. The resulting *Observation* is fed back into the trace, and the loop continues until the model emits a final answer. It turns a one-shot generator into a stepwise agent that can ground its reasoning in real environment feedback.

## When to use

- The task requires external information or side effects (search, code execution, API calls, file ops).
- Reasoning needs to branch on intermediate results that aren't knowable up front.
- You want an auditable trace where each conclusion is tied to an observed tool output.
- Tool latency is moderate and a few sequential calls fit the budget.
- You need course-correction: bad observations should change the plan, not be ignored.

## When NOT to use

- A single retrieval pass is enough — use [[rag]] and skip the loop.
- The task is pure reasoning with no useful tools (math proofs, style rewriting).
- Sub-second latency is required; ReAct multiplies token and round-trip cost.
- Tools are unreliable or non-idempotent and partial failure is unsafe.
- The action space is large and unconstrained — the model will thrash without strong tool descriptions.

## How it works

1. **Prompt scaffold:** the system prompt lists available tools with signatures and shows few-shot examples in the `Thought → Action → Observation` format.
2. **Generate Thought + Action:** the model writes a short reasoning step, then a structured action (e.g. `search_web("...")` or `read_file("path")`), and stops.
3. **Execute and observe:** the runtime parses the action, runs the tool, and appends the result as `Observation:` to the running trace.
4. **Loop:** the model conditions on the full trace and emits the next Thought + Action, repeating until it emits `Final Answer:` or hits a step cap.
5. **Final answer:** the runtime returns the finish payload; the trace itself is preserved for audit and debugging.

## Worked example

**Input:** "What's in `raw/articles/` and which file looks most relevant to my task?"

**Trace (abbreviated):**

```
Thought: I should list the files first, then read each in turn.
Action: read_file("raw/articles/")
Observation: (read_file: not found: raw/articles/)
Thought: Let me try reading the index instead.
Action: read_file("wiki/index.md")
Observation: # Wiki Index ... (lists three concept pages)
Thought: Pick the most relevant page based on the task.
Final Answer: wiki/concepts/react.md is most relevant for tool-using tasks.
```

**Expected output:** "wiki/concepts/react.md is most relevant for tool-using tasks."

## Failure modes

- **Tool-call hallucination:** the model invents an action signature the runtime can't parse, stalling the loop.
- **Observation blindness:** the model writes the next Thought ignoring what the Observation actually said and confabulates a plan.
- **Looping:** repeated near-identical actions when no tool returns the needed answer; mitigated with step caps and dedup checks.
- **Premature finish:** the model emits `Final Answer:` before it has enough evidence, especially under token pressure.
- **Trace poisoning:** an Observation containing adversarial instructions is treated as guidance (a retrieval-side prompt-injection vector).

## Related techniques

- [[rag]] — single retrieve-then-generate; ReAct is iterative and tool-general, RAG is one-shot and retrieval-only.
- [[reflexion]] — wraps an outer self-critique loop around an inner ReAct rollout, replaying with a verbal lesson on failure.
- [[tree-of-thoughts]] — explores branching reasoning paths in parallel rather than ReAct's single linear trace.

## Sources

- Yao, S. et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models.* arXiv:2210.03629.
- LangChain & LlamaIndex agent docs — the dominant production implementations of the pattern.

## Runner notes

```bash
kairos run "Find the most relevant raw/ file for my task" --technique react
```

- v0.1 tools available to the loop: `search_web(q)`, `read_file(path)`, `finish(answer)`.
- Default `max_steps = 6` (cap on Thought/Action/Observation iterations).
- LLM call: `claude_send` per step via `llm-mcp`.
- The full Thought/Action/Observation trace is written to `outputs/run-<id>/trace.jsonl` for audit.
- The runner exits non-zero only if the LLM bridge itself fails; an unparseable reply becomes the final answer (defensive default).

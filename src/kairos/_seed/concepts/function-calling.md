---
title: "Function Calling"
type: concept
sources:
  - "OpenAI, 2023 - Function calling and other API updates"
  - "Anthropic, 2024 - Tool use with Claude"
related:
  - "[[tool-use]]"
  - "[[react]]"
  - "[[zero-shot-prompting]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Function Calling

## Summary

Function calling is a model-native channel for emitting structured tool invocations: the model decides which tool to call and produces a JSON-validated argument object instead of free-form text. The provider (OpenAI, Anthropic, Google) parses the response and surfaces a separate function-call object the runtime executes. It replaces brittle string-parsing of "Action: search(...)" prose with a typed, schema-validated path.

## When to use

- You have one or more tools with clear JSON schemas (parameters, types, required fields).
- The model needs to choose between tools or call several in sequence with verifiable arguments.
- You care about argument validation — type errors should be caught by schema, not by a regex.
- The provider supports parallel tool calls and you want the speedup.
- Production systems where prose-parsing failures are unacceptable.

## When NOT to use

- One-off prototypes where free-form prose is good enough; schema overhead is wasted.
- Tasks where the "tool" is ambiguous and the schema would be hand-waved (free-text fields everywhere).
- Models that don't support native function calling; you'll need to fall back to ReAct-style prose parsing.
- Workflows where you want the model's reasoning visible inline; function calls hide arguments in a structured channel.
- Highly dynamic tool sets that change per query and don't fit a static catalog.

## How it works

1. **Define tools:** each tool gets a name, description, and a JSON Schema describing its parameters.
2. **Pass the catalog:** include the tool list with the API request so the model sees what's available.
3. **Model decides:** for each turn, the model returns either a normal message or a `tool_use` object with name and validated arguments.
4. **Execute:** the runtime parses the tool_use, runs the tool, and submits the result back as a `tool_result` message.
5. **Loop:** the model continues, potentially calling more tools, until it returns a normal text reply.

## Failure modes

- **Schema rejection:** the model produces arguments that don't validate; provider returns an error instead of executing.
- **Tool selection drift:** with many tools, the model picks a similarly-named one (e.g. `search_web` vs `search_files`).
- **Hallucinated parameters:** required fields are filled with plausible-but-wrong values when the model lacks ground truth.
- **Provider lock-in:** schema syntax differs across OpenAI/Anthropic/Google; portable code needs an abstraction layer.

## Related techniques

- [[tool-use]] - the broader concept (any way an LLM invokes external tools); function calling is the model-native, schema-validated implementation.
- [[react]] - prose-format Thought/Action/Observation loop; function calling can serve as the Action channel for cleaner parsing.
- [[zero-shot-prompting]] - normal text-instruction prompting; function calling replaces it when structured output is required.

## Sources

- OpenAI Platform documentation — *Function calling.*
- Anthropic API documentation — *Tool use with Claude.*

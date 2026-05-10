---
title: "Zero-Shot Prompting"
type: concept
sources:
  - "Brown et al., 2020 - Language Models are Few-Shot Learners (arXiv:2005.14165)"
  - "Ouyang et al., 2022 - Training language models to follow instructions with human feedback (arXiv:2203.02155)"
related:
  - "[[few-shot-prompting]]"
  - "[[chain-of-thought]]"
  - "[[function-calling]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Zero-Shot Prompting

## Summary

Zero-shot prompting describes a task in natural language and asks the model to do it, with no worked examples. It works on instruction-tuned models because RLHF/instruction-tuning teaches them to follow direct commands. For modern aligned models (GPT-4, Claude, Gemini) it is the default starting point — examples are added only when the zero-shot result is wrong or under-specified.

## When to use

- Modern instruction-tuned models where the task is clearly describable in 1-3 sentences.
- Token budget is tight and adding examples is expensive.
- The task is common enough that the model has seen it during training (summarization, translation, classification, basic QA).
- You're prototyping and want to see the model's default behavior before designing examples.
- Output format is loose enough that you don't need a worked example to enforce structure.

## When NOT to use

- Strict output schemas the model won't get right without seeing one — use [[few-shot-prompting]].
- Multi-step reasoning where intermediate work helps — use [[chain-of-thought]] (often just adding "Let's think step by step." gets you there).
- Tool-using tasks where signature precision matters — use [[function-calling]] with a structured schema.
- Domain-specific outputs (legal, medical, technical jargon) where the model's prior is fuzzy.
- Tasks where the base model isn't instruction-tuned; zero-shot fails on completion-only models.

## How it works

1. **Instruction:** write a short, direct command stating what to do and the output format.
2. **Constraints:** add explicit constraints inline ("respond in JSON," "limit to 3 bullets," "use formal tone").
3. **Input:** provide the actual content the instruction operates on, often in a labeled section.
4. **Decode:** sample the response; parse using whatever structure the instruction asked for.
5. **Iterate:** if the output drifts from spec, tighten the instruction or escalate to few-shot.

## Failure modes

- **Format drift:** the model ignores the schema instruction and answers in prose.
- **Under-specification:** the instruction is vague and the model picks a default that doesn't match your need.
- **Verbosity:** zero-shot models often over-explain; "be concise" is necessary for tight outputs.
- **Refusal:** safety tuning makes the model decline a benign request because the instruction wasn't framed clearly.

## Related techniques

- [[few-shot-prompting]] - adds examples to lock in format and edge-case behavior; the natural escalation when zero-shot drifts.
- [[chain-of-thought]] - "Let's think step by step." is the canonical zero-shot CoT trigger; gets reasoning gain at zero example cost.
- [[function-calling]] - native structured-output channel that replaces zero-shot prose for tool calls.

## Sources

- Brown, T. et al. (2020). *Language Models are Few-Shot Learners.* arXiv:2005.14165.
- Ouyang, L. et al. (2022). *Training language models to follow instructions with human feedback.* arXiv:2203.02155.

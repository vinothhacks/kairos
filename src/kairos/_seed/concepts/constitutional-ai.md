---
title: "Constitutional AI"
type: concept
sources:
  - "Bai et al., 2022 - Constitutional AI: Harmlessness from AI Feedback (arXiv:2212.08073)"
related:
  - "[[reflexion]]"
  - "[[self-refine]]"
  - "[[prompt-injection]]"
confidence: high
has_runner: false
created: 2026-05-10
updated: 2026-05-10
---

# Constitutional AI

## Summary

Constitutional AI (CAI) trains and prompts an LLM to critique and revise its own outputs against a fixed list of natural-language principles — a "constitution." Anthropic's original training pipeline used the constitution to generate self-critiques, which became the supervised data for harmlessness fine-tuning. The same idea works at inference time without weight updates: the model drafts, then critiques against the principles, then revises, replacing human-written safety labels with AI-generated ones.

## When to use

- Safety, policy, or compliance critiques where you want a documented, auditable rule set.
- You need consistent behavior across tasks that share the same harm profile.
- A human review queue is too slow or expensive but you still need a documented critique signal.
- The constitution can be expressed in 5-30 short principles a model can attend to at once.
- You want to expose the principles externally as a transparency mechanism.

## When NOT to use

- Task quality (correctness, factuality) is the issue rather than safety/policy — use [[self-refine]] or [[reflexion]] instead.
- The constitution is too long or contradictory; the model will follow whichever principle is mentioned last.
- Adversarial users who can rewrite the prompt to override the principles ([[prompt-injection]] is the relevant failure mode).
- You can't articulate principles up front; CAI fundamentally needs the constitution to exist before it can run.
- Domains with hard legal requirements where AI critique is not a substitute for human sign-off.

## How it works

1. **Constitution:** write a numbered list of principles ("be harmless," "don't deceive," "respect user autonomy"). Keep it short.
2. **Draft:** the model produces a response to the user's request as it normally would.
3. **Critique:** the model is re-prompted with the draft and the constitution and asked to identify which principles the draft violates.
4. **Revise:** the model re-prompts itself with the original task plus the critique and produces a revised response.
5. **Optional training:** in the original paper, draft/critique/revise triples were used as supervised fine-tuning data; at inference time, you can stop after the revision.

## Failure modes

- **Principle drift:** the model adds principles that aren't in the constitution and revises against them.
- **Over-refusal:** an over-eager critique flags a benign draft as violating, and the revision becomes useless.
- **Critique blindness:** the same model that produced the violation cannot recognize it; the revision keeps the flaw.
- **Constitution-as-prompt:** an attacker can include "ignore the constitution" in user input and the model complies.

## Related techniques

- [[reflexion]] - uses task-specific verbal critiques driven by an evaluator; CAI uses fixed principle-based critiques across all tasks.
- [[self-refine]] - same draft/critique/revise loop but without an explicit principle set; CAI is "Self-Refine with a constitution."
- [[prompt-injection]] - the primary attack surface for CAI; user input that overrides or rewrites the constitution.

## Sources

- Bai, Y. et al. (2022). *Constitutional AI: Harmlessness from AI Feedback.* arXiv:2212.08073.
- Anthropic. *Claude's Constitution* — public excerpt of the principle set used for training.

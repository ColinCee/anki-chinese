# Decision: sentence generation

## Context

Each character note needs a short, natural Mandarin example sentence. Static
corpora did not provide enough controllable coverage, especially for simple
daily-use examples.

## Decision

Use Gemini Flash Lite for sentence generation and keyword/meaning repair.
Generated sentences should:

- include the target character literally
- be short and natural
- use common vocabulary
- avoid audio-confusing homophones where possible
- include pinyin and English

The implementation combines deterministic checks with model validation. Repair
commands and audits exist for confusing or unnatural sentences.

## Operational guidance

Current commands, credentials, and generated-content persistence are maintained
in [Workflows](../workflows.md#generate-sentences-and-meanings), not this decision.

## Consequences

- Better coverage and simpler sentences than a fixed corpus.
- Generated output must remain reviewable and repairable.
- Runtime song planning must not call the LLM; it stays deterministic.

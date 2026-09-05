# Decision: TTS provider strategy

## Context

Single Chinese characters need pronunciation control. Sentence audio needs
natural prosody. No single provider is best at both.

## Decision

Use a hybrid TTS setup behind the `TTSProvider` protocol:

| Audio type | Provider | Reason |
| --- | --- | --- |
| Single-character Mandarin | Google Cloud Text-to-Speech | Supports exact pronunciation control. |
| Single-character Cantonese | Google Cloud Text-to-Speech | Dedicated `yue-HK` voice. |
| Sentence audio | MiniMax | More natural Chinese sentence prosody. |

Google uses Application Default Credentials or a service-account JSON file, not
a Google TTS API-key environment variable.

## Operational guidance

[Workflows](../workflows.md#generate-audio) owns generation procedures;
[Reference](../reference.md) owns configuration and audio provenance paths.

## Consequences

- Full audio generation needs both Google auth and `MINIMAX_API_KEY`.
- Provider-specific code stays contained under `src/anki_chinese/audio/`.
- Pricing and model availability must be checked with providers before large runs.

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

## Current behavior

```bash
uv run anki-chinese doctor
uv run anki-chinese test-tts --char 早 --provider google
uv run anki-chinese test-tts --word 早上 --provider minimax
uv run anki-chinese audio
uv run anki-chinese sync
```

Generated audio provenance is stored locally so provider/model/voice changes can
mark existing files stale even when filenames still exist.

## Consequences

- Full audio generation needs both Google auth and `MINIMAX_API_KEY`.
- Provider-specific code stays contained under `src/anki_chinese/audio/`.
- Pricing and model availability must be checked with providers before large runs.

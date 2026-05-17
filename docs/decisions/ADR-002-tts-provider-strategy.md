# ADR-002: TTS Provider Strategy

**Status:** Accepted
**Date:** 2026-04-15
**Supersedes:** Single-provider MiniMax approach

## Context

Single Chinese characters are polyphonic — a TTS model receiving an isolated character with no context frequently picks the wrong pronunciation. Sentence-length text needs natural prosody more than phoneme forcing. No single provider excels at both.

## Decision

Use a **hybrid** TTS approach:

| Audio type | Provider | Rationale |
|------------|----------|-----------|
| Single-character Mandarin | Google Cloud Text-to-Speech | Custom pronunciations force exact pinyin |
| Single-character Cantonese | Google Cloud Text-to-Speech | Dedicated `yue-HK` voice; provider remains separate from MiniMax |
| Sentence audio | MiniMax `speech-2.8-turbo` | Chinese-first model, natural prosody, context disambiguation |

### Why not a single provider?

- **Google only**: Strong control for short audio but sentence prosody is less natural than MiniMax's Chinese-specialized model.
- **MiniMax only**: No SSML `<phoneme>` support — single-character pronunciation is unreliable. The `pronunciation_dict` field is underdocumented and not designed for per-request phoneme forcing.

### Architecture

The existing `TTSProvider` Protocol in `audio/provider.py` and factory pattern in `audio/factory.py` support this cleanly. The CLI and note pipeline remain provider-neutral. The application runtime uses Google for short character audio and MiniMax for sentence audio; `test-tts` also exposes a `--provider` flag for smoke testing specific providers.

## Consequences

- Google Cloud credentials plus a MiniMax API key are required for the full audio workflow
- Two rate limiters in the audio pipeline
- Slightly more complex `audio/` module, but contained behind the provider boundary
- Single-character Mandarin pronunciation can be forced through Google custom pronunciations
- Sentence audio sounds natural (MiniMax prosody)

## Cost

| Provider | Our workload | Cost |
|----------|-------------|------|
| Google Text-to-Speech | ~6,036 chars (Mandarin + Cantonese singles) | Verify current Google pricing before large rebuilds |
| MiniMax | sentence audio workload | Verify current MiniMax pricing before large rebuilds |

Provider pricing and free tiers change over time. Keep precise pricing in research notes, not setup docs.

## References

- [TTS Provider Research](../research/tts-providers.md) — point-in-time provider comparison
- [ADR-001](ADR-001-sentence-generation.md) — sentence generation strategy (sentences fed to MiniMax)

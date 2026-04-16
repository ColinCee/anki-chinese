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
| Single-character Mandarin | Google Cloud TTS WaveNet | SSML `<phoneme>` forces exact pinyin |
| Single-character Cantonese | Google Cloud TTS WaveNet | SSML `<phoneme>` forces exact jyutping |
| Sentence / example-word audio | MiniMax `speech-2.8-turbo` | Chinese-first model, natural prosody, context disambiguation |

### Why not a single provider?

- **Google only**: Excellent phoneme control but sentence prosody is less natural than MiniMax's Chinese-specialized model.
- **MiniMax only**: No SSML `<phoneme>` support — single-character pronunciation is unreliable. The `pronunciation_dict` field is underdocumented and not designed for per-request phoneme forcing.

### Architecture

The existing `TTSProvider` Protocol in `audio/provider.py` and factory pattern in `audio/factory.py` support this cleanly. The CLI and note pipeline remain provider-neutral. Provider selection is via `--provider` flag or factory default.

## Consequences

- Two API keys required (Google Cloud + MiniMax)
- Two rate limiters in the audio pipeline
- Slightly more complex `audio/` module, but contained behind the provider boundary
- Single-character pronunciation is always correct (Google phoneme control)
- Sentence audio sounds natural (MiniMax prosody)

## Cost

| Provider | Our workload | Cost |
|----------|-------------|------|
| Google WaveNet | ~6,036 chars (Mandarin + Cantonese singles) | Free (within 4M/month) |
| MiniMax | ~6,188 chars (sentence/example audio) | ~$0.37/rebuild |

## References

- [TTS Provider Research](../research/tts-providers.md) — full provider comparison, pricing, and API details
- [ADR-001](ADR-001-sentence-generation.md) — sentence generation strategy (sentences fed to MiniMax)

# TTS setup guide

Audio generation uses two providers behind the same `TTSProvider` boundary:

| Audio | Current provider | Notes |
| --- | --- | --- |
| Single-character Mandarin | Google Cloud Text-to-Speech | Uses custom pronunciations with pinyin tone numbers. |
| Single-character Cantonese | Google Cloud Text-to-Speech | Uses the configured `yue-HK` voice. |
| Sentence audio | MiniMax `speech-2.8-turbo` | Better naturalness for longer Mandarin text. |

See [ADR-002](../decisions/ADR-002-tts-provider-strategy.md) for the architectural rationale.

## Google Cloud Text-to-Speech

The current Google provider uses **Application Default Credentials** or a service-account JSON file. It does not use a Google TTS API-key environment variable.

### Setup

1. Create or choose a Google Cloud project.
2. Enable the Text-to-Speech API.
3. Authenticate with one of the following methods.

For local ADC:

```bash
gcloud auth application-default login
```

For a service account:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

If using `.env`:

```dotenv
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### Optional overrides

| Variable | Purpose |
| --- | --- |
| `GOOGLE_TTS_ENDPOINT` | Override the REST endpoint. |
| `GOOGLE_TTS_MANDARIN_VOICE` | Override Mandarin voice; default is `cmn-CN-Chirp3-HD-Leda`. |
| `GOOGLE_TTS_CANTONESE_VOICE` | Override Cantonese voice; default is `yue-HK-Chirp3-HD-Leda`. |

## MiniMax

MiniMax provides natural Chinese-first sentence audio.

### Setup

Create a MiniMax API key and set:

```dotenv
MINIMAX_API_KEY=your-key
```

Mainland-region keys usually need:

```dotenv
MINIMAX_API_HOST=https://api.minimaxi.com
```

### Optional overrides

| Variable | Purpose |
| --- | --- |
| `MINIMAX_API_HOST` | API host; defaults to `https://api.minimax.io`. |
| `MINIMAX_TTS_MODEL` | Speech model; default is `speech-2.8-turbo`. |
| `MINIMAX_MANDARIN_VOICE_ID` | Mandarin voice ID. |
| `MINIMAX_CANTONESE_VOICE_ID` | Cantonese voice ID. |

## Smoke tests

```bash
uv run anki-chinese doctor

# Google character audio
uv run anki-chinese test-tts --char 一 --provider google

# MiniMax arbitrary Mandarin text
uv run anki-chinese test-tts --word 早上 --provider minimax
```

Samples are written under:

```text
data/build/audio/samples/
```

## Generate deck audio

```bash
uv run anki-chinese audio --limit 20
uv run anki-chinese audio
```

Useful options:

```bash
uv run anki-chinese audio --char 早
uv run anki-chinese audio --start-rsh 500
uv run anki-chinese audio --force
uv run anki-chinese audio-clean
uv run anki-chinese audio-clean --apply
```

After audio generation, use `sync` so any stale deck output is rebuilt:

```bash
uv run anki-chinese sync
```

Generated files are checked against local provenance in
`data/state/audio_manifest.json`. If you change `MINIMAX_TTS_MODEL`, voice IDs,
Google voices, or sentence text/readings, `sync`, `status`, and `audio` can
detect that existing files are stale even when filenames still exist.

## Cost and limits

Provider pricing, free tiers, and model availability change over time. Treat [TTS provider research](../research/tts-providers.md) as point-in-time background and verify pricing against the provider before a large run.

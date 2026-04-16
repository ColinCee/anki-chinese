# TTS setup guide

Audio generation uses two providers: **Google Cloud TTS** for single-character pronunciation and **MiniMax** for sentence audio. See [ADR-002](../decisions/ADR-002-tts-provider-strategy.md) for the rationale.

## Google Cloud TTS (single characters)

Google provides SSML `<phoneme>` control for exact pinyin/jyutping pronunciation.

### Setup

1. Create a Google Cloud project and enable the [Text-to-Speech API](https://console.cloud.google.com/apis/library/texttospeech.googleapis.com)
2. Create an API key in **APIs & Services → Credentials**
3. Copy `.env.example` to `.env` and set:

```dotenv
GOOGLE_TTS_API_KEY=your-key
```

### Free tier

WaveNet: 4M chars/month ongoing (our ~6K single-char workload is ~660× under the limit).

## MiniMax (sentences)

MiniMax provides natural Chinese-first speech via `speech-2.8-turbo`.

### Setup

1. Create a MiniMax API key at [API Keys](https://platform.minimax.io/user-center/basic-information/interface-key)
2. Set in `.env`:

```dotenv
MINIMAX_API_KEY=your-key
```

### Billing

- Pay-as-you-go balance: [Balance page](https://platform.minimax.io/user-center/payment/balance)
- Audio subscription: [Subscription page](https://platform.minimax.io/subscribe/audio-subscription)
- Full rebuild cost: ~$0.37 (sentence portion only)
- Starter subscription ($5/month, 100K credits) gives ~8 full rebuilds

The repo does not care whether usage is paid by free credits, pay-as-you-go, or subscription.

## Smoke test

```bash
# Test single-character audio (Google)
uv run anki-chinese test-tts --char 一

# Test with specific provider
uv run anki-chinese test-tts --char 早 --provider google
uv run anki-chinese test-tts --word 早上 --provider minimax
```

## Provider architecture

The `TTSProvider` Protocol in `src/anki_chinese/audio/provider.py` defines the boundary. Implementations:

| Provider | File | Default for |
|----------|------|-------------|
| Google | `audio/google_tts.py` | Single characters (factory default) |
| MiniMax | `audio/minimax.py` | Sentences/examples |

Selection is via `--provider` CLI flag or the factory default in `audio/factory.py`.

## Environment variable reference

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOOGLE_TTS_API_KEY` | For audio | Google Cloud TTS authentication |
| `MINIMAX_API_KEY` | For audio | MiniMax TTS authentication |
| `MINIMAX_API_HOST` | No | Override for mainland-region keys |
| `MINIMAX_TTS_MODEL` | No | Override default speech model |
| `MINIMAX_MANDARIN_VOICE_ID` | No | Override default Mandarin voice |
| `MINIMAX_CANTONESE_VOICE_ID` | No | Override default Cantonese voice |

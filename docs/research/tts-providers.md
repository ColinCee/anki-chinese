# TTS Provider Research

Research and comparison of TTS providers for Chinese character and sentence audio generation.

This is point-in-time research. Use the [TTS setup guide](../guides/tts-setup.md) and [configuration reference](../reference/configuration.md) for current setup instructions.

## The problem

Single Chinese characters are often **polyphonic** (多音字) — multiple valid pronunciations depending on context. When a TTS model receives an isolated character with no surrounding context, it guesses which reading to use and frequently guesses wrong.

This creates two distinct requirements:

| Use case | Need | Challenge |
|----------|------|-----------|
| **Single characters** | Exact pronunciation via pinyin/jyutping | No context for disambiguation — must force phoneme |
| **Sentences/examples** | Natural prosody, contextual disambiguation | Context helps, but voice quality and naturalness matter more |

## Provider comparison

### Google Cloud TTS ⭐ (single characters)

Best-in-class phoneme control for both Mandarin and Cantonese.

| Feature | Details |
|---------|---------|
| Phoneme control | Full SSML `<phoneme>` with pinyin + jyutping |
| Mandarin voices | cmn-CN / cmn-TW: Standard, WaveNet, Neural2, Chirp 3 HD |
| Cantonese voices | yue-HK: Standard, WaveNet |
| API | REST at `texttospeech.googleapis.com/v1/text:synthesize` |
| Auth | OAuth/ADC or service account in the current implementation |
| Reliability | Google infrastructure, no chronic rate-limit issues |

#### Model tiers

| Tier | SSML `<phoneme>` | Mandarin | Cantonese | Price/1M chars | Free tier | RPM |
|------|-------------------|----------|-----------|----------------|-----------|-----|
| **Chirp 3: HD** | ✅ (see notes) | cmn-CN ✅ (GA) | yue-HK ✅ (Preview) | $30 | 1M/month | 200 |
| **Neural2** | ✅ | cmn-CN ✅ | unverified | $16 | 1M/month | 1,000 |
| **WaveNet** | ✅ | cmn-CN, cmn-TW ✅ | yue-HK ✅ | $4 | 4M/month ongoing | 1,000 |
| **Standard** | ✅ | cmn-CN, cmn-TW ✅ | yue-HK ✅ | $4 | 4M/month ongoing | 1,000 |
| **Gemini-TTS** | ❌ (text prompts) | cmn-CN (Preview) | ❌ | ~$10/1M tokens | None | — |

#### Chirp 3: HD Cantonese limitations

- yue-HK is **Preview** (not GA)
- `custom_pronunciations` is **excluded** for yue-HK
- No `PHONETIC_ENCODING_JYUTPING` enum
- SSML `<phoneme>` tag supported but jyutping alphabet compatibility unverified
- Pause control excluded for yue-HK

#### SSML phoneme examples

```xml
<!-- Mandarin — pinyin with tone number -->
<speak><phoneme alphabet="pinyin" ph="yi1">一</phoneme></speak>

<!-- Cantonese — jyutping with tone number -->
<speak><phoneme alphabet="jyut-ping" ph="jat1">一</phoneme></speak>

<!-- Multi-syllable — space-separated -->
<speak><phoneme alphabet="pinyin" ph="wo3 de5">我的</phoneme></speak>
```

#### REST API shape

```bash
curl -X POST \
  "https://texttospeech.googleapis.com/v1/text:synthesize" \
  -H "Authorization: Bearer $GOOGLE_OAUTH_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "ssml": "<speak><phoneme alphabet=\"pinyin\" ph=\"yi1\">一</phoneme></speak>"
    },
    "voice": { "languageCode": "cmn-CN", "name": "cmn-CN-Wavenet-A" },
    "audioConfig": { "audioEncoding": "MP3" }
  }'
```

### MiniMax ⭐ (sentences)

Best fit for sentence audio where context helps disambiguation.

| Feature | Details |
|---------|---------|
| Phoneme control | `pronunciation_dict` exists but no SSML, no per-character pinyin forcing |
| Mandarin voices | Yes, multiple |
| Cantonese voices | Yes, via `language_boost: "Chinese,Yue"` |
| Model | `speech-2.8-turbo` |
| Max request | 10,000 characters |
| RPM | 60 |
| Pricing | $60/1M chars |

**Strengths**: Premium Chinese-first speech product, explicit `language_boost` for Chinese and Cantonese, modern speech model with natural sentence prosody.

**Weakness**: No SSML phoneme support — cannot force exact pronunciation for isolated characters.

#### Python integration

No official Python SDK for `speech-2.8-turbo`. The repo uses a small direct HTTP client matching the T2A API docs.

### Amazon Polly

| Feature | Details |
|---------|---------|
| Phoneme control | SSML `<phoneme>` with `x-amazon-pinyin` |
| Cantonese | **None** |
| Pricing | $4–30/1M depending on tier |

**Verdict**: Good Mandarin phoneme control but no Cantonese. Dealbreaker.

### Edge TTS (Microsoft)

| Feature | Details |
|---------|---------|
| Phoneme control | **None** — Microsoft removed custom SSML |
| Both languages | Yes |
| Pricing | Free |

**Verdict**: Azure voice quality for free, but no phoneme control. Also unofficial — could break. Not viable for pronunciation accuracy.

### ElevenLabs

| Feature | Details |
|---------|---------|
| Phoneme control | Pre-registered pronunciation dictionaries only |
| Pricing | ~$30/1M |

**Verdict**: No real-time per-request phoneme control for Chinese. Doesn't scale for polyphonic characters.

### OpenAI TTS

| Feature | Details |
|---------|---------|
| Phoneme control | **None** |
| Pricing | $15–30/1M |

**Verdict**: No pronunciation control. Not a candidate.

## Pricing and throughput

### Cost comparison

| Provider | Price/1M chars | Free tier | ~12K workload cost |
|----------|----------------|-----------|---------------------|
| Google WaveNet | $4 | 4M/month ongoing | **Free at the time of research** |
| Google Standard | $4 | 4M/month ongoing | **Free** |
| Google Neural2 | $16 | 1M/month | **Free** |
| MiniMax | $60 | ~10K/month | $0.73/rebuild |

### Rate limits

| Provider | RPM | Chars/request |
|----------|-----|---------------|
| Google WaveNet | 1,000 | 5,000 bytes |
| MiniMax | 60 | 10,000 chars |

### Workload snapshot at time of research

The original full-rebuild estimate was based on:

- 3,018 Mandarin audio items → **3,018 characters**
- 3,018 Cantonese audio items → **3,018 characters**
- sentence audio for the deck's generated example sentences
- about **12K synthesized characters** per full rebuild

MiniMax full rebuild cost was estimated at ~$0.73 at the time of research. Verify current pricing before large rebuilds.

## Recommendation

**Hybrid approach**: Google Cloud Text-to-Speech for single characters, MiniMax for sentences.

| Audio type | Provider | Why |
|------------|----------|-----|
| Single-character Mandarin | Google Cloud TTS | Custom pronunciations/phoneme control force exact pinyin |
| Single-character Cantonese | Google Cloud TTS | Dedicated Cantonese voice |
| Sentence audio | MiniMax | Natural prosody, context disambiguates polyphonic chars |

Google gives the project the strongest control for short character audio. MiniMax produces more natural sentence-level audio with its Chinese-first model. The provider boundary in `audio/provider.py` supports this cleanly.

## Pinyin/jyutping conversion notes

The provider interface passes pinyin (diacritical marks, e.g., "nǐ") and jyutping (tone numbers, e.g., "jat1"). Google expects numbered tones for both. A `pinyin_to_numbered()` converter handles Mandarin; jyutping is already in the right format.

## Setup

See [TTS setup guide](../guides/tts-setup.md) for current credential setup and smoke testing.

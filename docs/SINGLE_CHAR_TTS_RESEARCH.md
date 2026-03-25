# Single character TTS pronunciation research

## The problem

Single Chinese characters are often **polyphonic** (多音字) — they have multiple valid
pronunciations depending on context. When a TTS model receives a single isolated character
with no surrounding context, it guesses which reading to use and frequently guesses wrong.

MiniMax (our current provider) sends only the raw character text to the API. It has no
SSML phoneme support. The `language_boost` field helps with language detection but does
nothing for disambiguation. The pinyin/jyutping data is passed to the provider interface
but MiniMax ignores it entirely. The result: single character audio is unreliable.

Azure (our former provider) solved this with SSML `<phoneme>` tags that forced exact
pinyin/jyutping pronunciation per character. The audio quality for single characters was
good — the problem was Azure's 429 rate limiting from backend capacity issues.

## What we need

A TTS provider that:

1. Lets us **force exact pronunciation** via pinyin (Mandarin) and jyutping (Cantonese)
2. Supports both **Mandarin and Cantonese** voices
3. Has a **simple REST API** (no heavy SDK)
4. Is **reliable** (no chronic 429s)
5. Is **reasonably priced** for our ~12K character workload

## Provider comparison

### Google Cloud TTS ⭐ recommended

| Feature | Details |
|---|---|
| Phoneme control | Full SSML `<phoneme>` with pinyin + tones (Mandarin) and jyutping + tones (Cantonese) |
| Mandarin voices | cmn-CN / cmn-TW: Standard, WaveNet, Neural2, Chirp 3 HD |
| Cantonese voices | yue-HK: Standard, WaveNet (Chirp 3 HD does NOT support Cantonese) |
| API | Simple REST at `texttospeech.googleapis.com/v1/text:synthesize` |
| Auth | API key or service account |
| Reliability | Google infrastructure, no known chronic rate-limit issues |

#### Google Cloud TTS model tiers (newest → oldest)

| Tier | Quality | SSML `<phoneme>` | Mandarin | Cantonese | Price/1M chars | Free tier | Rate limit |
|---|---|---|---|---|---|---|---|
| **Gemini-TTS** (2025) | Highest, prompt-steerable | No (uses text prompts) | cmn-CN (Preview) | ❌ | ~$10/1M output tokens | None | — |
| **Chirp 3: HD** (2024) | Very high, 30 voices | ✅ Yes (see notes) | cmn-CN ✅ (GA) | yue-HK ✅ (Preview) | $30 | 1M/month | 200 RPM |
| **Neural2** (2023) | High | ✅ Yes | cmn-CN ✅ | unverified | $16 | 1M/month | 1,000 RPM |
| **WaveNet** (2018) | High, warm | ✅ Yes | cmn-CN, cmn-TW ✅ | yue-HK ✅ | $4 | 4M/month ongoing | 1,000 RPM |
| **Standard** (legacy) | Basic | ✅ Yes | cmn-CN, cmn-TW ✅ | yue-HK ✅ | $4 | 4M/month ongoing | 1,000 RPM |

#### Chirp 3: HD — pronunciation control details

Chirp 3: HD supports **two** mechanisms for pronunciation control:

**1. SSML `<phoneme>` tag** (supported for all locales including yue-HK):
```xml
<phoneme alphabet="pinyin" ph="yi1">一</phoneme>
```
The Chirp 3: HD docs explicitly list `<phoneme>` as a supported SSML tag.
Whether the `pinyin` and `jyut-ping` alphabet names work on Chirp 3: HD
(vs only IPA/X-SAMPA) needs live testing.

**2. `custom_pronunciations` API field** (NOT available for yue-HK):
```json
{
  "input": {
    "text": "一",
    "custom_pronunciations": {
      "phrase": "一",
      "phonetic_encoding": "PHONETIC_ENCODING_PINYIN",
      "pronunciation": "yi1"
    }
  }
}
```
Google has a dedicated `PHONETIC_ENCODING_PINYIN` enum with numbered tones
(e.g., `"chao2 yang2"`, neutral tone = `5`). This works for Mandarin (cmn-CN)
but **yue-HK is explicitly excluded** from custom_pronunciations. There is also
**no jyutping encoding** — only IPA, X-SAMPA, Japanese Yomigana, and Pinyin.

**Summary of Chirp 3: HD Cantonese limitations:**
- yue-HK is in **Preview** (not GA)
- `custom_pronunciations` is **excluded** for yue-HK
- No `PHONETIC_ENCODING_JYUTPING` enum exists
- SSML `<phoneme>` tag is supported but jyutping alphabet compatibility unverified
- Pause control is also excluded for yue-HK

#### Recommendation: test Chirp 3 HD first, fall back to WaveNet

**Chirp 3: HD** is the better voice quality tier if its pronunciation control
works for our use case. The testing plan:

1. Test SSML `<phoneme alphabet="pinyin" ph="yi1">一</phoneme>` with Chirp 3: HD cmn-CN
2. Test `custom_pronunciations` with `PHONETIC_ENCODING_PINYIN` for cmn-CN
3. Test SSML `<phoneme alphabet="jyut-ping" ph="jat1">一</phoneme>` with Chirp 3: HD yue-HK
4. If Cantonese phoneme control fails on Chirp 3: HD, fall back to WaveNet for Cantonese

**WaveNet** is the safe fallback because:
- Full SSML `<phoneme>` with pinyin (Mandarin) and jyutping (Cantonese) confirmed
- Both cmn-CN/cmn-TW and yue-HK voices available and GA
- $4/1M chars with 4M chars/month free (ongoing, not time-limited)
- 1,000 RPM rate limit (vs MiniMax's 60 RPM — **16x higher**)
- Quality is warm and natural (trained on human speech samples)

A hybrid of Chirp 3: HD (Mandarin) + WaveNet (Cantonese) is viable if
Cantonese phoneme control only works on WaveNet.

#### Pricing comparison

| Provider | Price/1M chars | Free tier | Our ~12K workload cost |
|---|---|---|---|
| Google WaveNet | $4 | 4M/month ongoing | **Free** (330x under limit) |
| Google Standard | $4 | 4M/month ongoing | **Free** |
| Google Neural2 | $16 | 1M/month ongoing | **Free** (80x under limit) |
| MiniMax | $60 | ~10K/month | $0.73/rebuild |

#### Rate limit comparison

| Provider | Requests/min | Chars/request |
|---|---|---|
| Google WaveNet | 1,000 | 5,000 bytes |
| MiniMax | 60 | 10,000 chars |

Google's 1,000 RPM means we could process our entire ~9K file workload in under a
minute if we wanted to. MiniMax's 60 RPM means ~2.5 minutes minimum at full
saturation.

#### SSML phoneme examples

Mandarin — pinyin with tone number at end of syllable:
```xml
<speak>
  <phoneme alphabet="pinyin" ph="yi1">一</phoneme>
</speak>
```

Cantonese — jyutping with tone number at end of syllable:
```xml
<speak>
  <phoneme alphabet="jyut-ping" ph="jat1">一</phoneme>
</speak>
```

Multi-syllable words use spaces between syllables:
```xml
<speak>
  <phoneme alphabet="pinyin" ph="wo3 de5">我的</phoneme>
</speak>
```

Google also supports **inline custom pronunciation dictionaries** in the API request
body itself (`custom_pronunciations` field), which auto-wraps matching text in
`<phoneme>` tags. But for our per-character use case, explicit SSML is cleaner.

#### Available Chinese voices

Mandarin (cmn-CN):
- `cmn-CN-Standard-A` (Female), `cmn-CN-Standard-B` (Male), etc.
- `cmn-CN-Wavenet-A` (Female), `cmn-CN-Wavenet-B` (Male), etc.

Mandarin Taiwan (cmn-TW):
- `cmn-TW-Standard-A` (Female), `cmn-TW-Standard-B` (Male)
- `cmn-TW-Wavenet-A` (Female), `cmn-TW-Wavenet-B` (Male)

Cantonese (yue-HK):
- `yue-HK-Standard-A` (Female), `yue-HK-Standard-B` (Male), etc.
- `yue-HK-Wavenet-*` voices (if available at tier)

#### REST API shape

```bash
curl -X POST \
  "https://texttospeech.googleapis.com/v1/text:synthesize?key=$GOOGLE_TTS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "ssml": "<speak><phoneme alphabet=\"pinyin\" ph=\"yi1\">一</phoneme></speak>"
    },
    "voice": {
      "languageCode": "cmn-CN",
      "name": "cmn-CN-Wavenet-A"
    },
    "audioConfig": {
      "audioEncoding": "MP3"
    }
  }'
```

Response contains `audioContent` as base64-encoded audio bytes.

**Why Google Cloud TTS wins:**
- Only provider with full phoneme control for **both** Mandarin and Cantonese
- Free tier alone covers our entire workload (~12K chars) hundreds of times over
- WaveNet at $4/1M is 15x cheaper than MiniMax at $60/1M
- 1,000 RPM is 16x higher than MiniMax's 60 RPM
- REST API is simple — same direct HTTP approach we already use for MiniMax
- Google infrastructure has no chronic rate-limit issues

### Amazon Polly

| Feature | Details |
|---|---|
| Phoneme control | SSML `<phoneme>` with `x-amazon-pinyin` alphabet |
| Mandarin voices | Zhiyu (Neural, Standard) |
| Cantonese voices | **None** |
| Pricing | Standard $4/1M, Neural $16/1M, Generative $30/1M |
| Free tier | 1-5M chars/month (12 months) |

**Phoneme example:**
```xml
<speak>
  <phoneme alphabet="x-amazon-pinyin" ph="bo2">薄</phoneme>
</speak>
```

**Verdict:** Good Mandarin phoneme control but **no Cantonese support**. Dealbreaker for
this project which needs both languages.

### MiniMax (current provider)

| Feature | Details |
|---|---|
| Phoneme control | `pronunciation_dict` field exists in API but no SSML, no per-character pinyin control |
| Mandarin voices | Yes, multiple |
| Cantonese voices | Yes, via `language_boost: "Chinese,Yue"` |
| Pricing | $60/1M chars |

**Verdict:** Good for sentences where context disambiguates. Poor for isolated characters.
The `pronunciation_dict` field is underdocumented and not designed for per-request
phoneme forcing the way SSML `<phoneme>` tags are. Not a viable solution for the
single-character problem.

### Edge TTS (Microsoft Edge free voices)

| Feature | Details |
|---|---|
| Phoneme control | **None** — Microsoft removed custom SSML support |
| Mandarin voices | Yes (zh-CN-*) |
| Cantonese voices | Yes (zh-HK-*) |
| Pricing | Free |

**Verdict:** Same Azure voice quality for free, but no phoneme control whatsoever.
Microsoft explicitly blocks any SSML beyond basic prosody. Also unofficial — could
break or be blocked at any time. Not a solution for pronunciation accuracy.

### ElevenLabs

| Feature | Details |
|---|---|
| Phoneme control | Pronunciation dictionaries only (pre-registered, not per-request) |
| Chinese quality | Good but not Chinese-specialized |
| Pricing | ~$30/1M chars (Starter plan) |

**Verdict:** Great English voices, but no real-time phoneme control for Chinese. The
pronunciation dictionary approach requires pre-registering every character variant,
which doesn't scale for polyphonic characters. Expensive for what you get.

### OpenAI TTS

| Feature | Details |
|---|---|
| Phoneme control | **None** |
| Chinese quality | Decent |
| Pricing | ~$15/1M (tts-1), ~$30/1M (tts-1-hd) |

**Verdict:** No pronunciation control at all. No SSML support. Not a candidate for
the single-character problem.

## Recommendation

**Google Cloud TTS WaveNet** is the clear choice. It is the only tier that gives us:

1. SSML `<phoneme>` with pinyin for Mandarin
2. SSML `<phoneme>` with jyutping for Cantonese
3. Both cmn-CN and yue-HK voices
4. 4M chars/month free tier (ongoing, not time-limited)
5. 1,000 RPM rate limit
6. Simple REST API (matches our existing HTTP client pattern)

The newer Google tiers (Chirp 3 HD, Gemini-TTS) are better for English and conversational
use cases but do not support Cantonese and have unclear/no SSML phoneme support.
WaveNet is the right tool for this specific job.

## Implementation approach

Two viable options:

### Option A: Full switch to Google Cloud TTS WaveNet

Replace MiniMax entirely. Google WaveNet handles single characters, example words,
and sentences uniformly via the same SSML phoneme mechanism.

- **Pro:** One provider, one code path, simplest architecture
- **Pro:** Always use phoneme tags — pronunciation is always correct
- **Pro:** 15x cheaper ($4/1M vs $60/1M), or completely free
- **Pro:** 16x higher rate limit (1,000 RPM vs 60 RPM)
- **Con:** Voice quality for longer phrases may differ from MiniMax
- **Con:** Requires Google Cloud account setup

### Option B: Hybrid — Google for characters, MiniMax for sentences

Use Google WaveNet for `generate_mandarin()` and `generate_cantonese()` (single
characters where phoneme control matters), keep MiniMax for `generate_example_audio()`
(multi-word phrases where context helps and natural prosody matters).

- **Pro:** Best of both worlds for quality
- **Con:** Two providers, two API keys, two rate limiters, more code paths
- **Con:** MiniMax is 15x more expensive for the sentence portion

### Recommended: Option A (full switch)

The simplicity of one provider outweighs the marginal quality difference for sentences.
Google WaveNet voices are high quality for Chinese — they are trained on human speech
samples. The phoneme control ensures every character is pronounced correctly, and the
pricing is a fraction of MiniMax. If Google's sentence prosody turns out inadequate,
we can revisit the hybrid approach — the provider boundary is already clean enough to
support that swap later.

## Setup requirements

1. Google Cloud project with Text-to-Speech API enabled
2. API key for authentication (simplest) or service account JSON
3. Environment variable: `GOOGLE_TTS_API_KEY`
4. No SDK needed — REST API at `https://texttospeech.googleapis.com/v1/text:synthesize`

## Cost projection

| Scenario | Characters | Google WaveNet cost | MiniMax cost |
|---|---|---|---|
| One full rebuild | ~12,224 | **Free** (within 4M/month) | $0.73 |
| 10 full rebuilds/month | ~122,240 | **Free** (within 4M/month) | $7.33 |
| 100 full rebuilds/month | ~1,222,400 | **Free** (within 4M/month) | $73.34 |

Even at aggressive usage, Google's free tier absorbs the entire workload.

## Throughput projection

| Provider | RPM | Time for 9K files (sequential) | Time for 9K files (concurrent) |
|---|---|---|---|
| Google WaveNet | 1,000 | ~9 min | ~1 min (10 workers) |
| MiniMax | 60 | ~150 min | ~15 min (10 workers) |

## Pinyin/jyutping conversion notes

Our provider interface already passes pinyin and jyutping to the generate methods:
- `generate_mandarin(hanzi, pinyin, ...)` — pinyin has diacritical marks (e.g. "nǐ")
- `generate_cantonese(hanzi, jyutping, ...)` — jyutping has tone numbers (e.g. "jat1")
- `generate_example_audio(word, pinyin, ...)` — multi-syllable pinyin

Google expects:
- Mandarin pinyin with tone **numbers** (e.g. "ni3", not "nǐ")
- Cantonese jyutping with tone **numbers** (e.g. "jat1") — already in this format
- Multi-syllable: space-separated (e.g. "wo3 de5")

We will need a small `pinyin_to_numbered()` converter for Mandarin (diacritical → numbered).
The jyutping data is already in the right format.

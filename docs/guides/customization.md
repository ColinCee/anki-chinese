# Customization guide

Non-default tweaks only. For normal setup and rebuild workflow see [Getting started](../getting-started.md) and the [deck rebuild guide](deck-rebuild.md).

## Character data overrides

Edit `data/manual/overrides.json` to force fields per character:

```json
{
  "行": { "pinyin": "xíng", "jyutping": "haang4", "keyword": "go" },
  "了": { "pinyin": "le" }
}
```

Then rerun `uv run anki-chinese init`.

## Card templates

Files in `src/anki_chinese/cards/` control card UI:

| File | Role |
|------|------|
| `style.css` | Shared styles |
| `recognition_front.html` / `recognition_back.html` | Character → meaning direction |
| `recall_front.html` / `recall_back.html` | Listening-first: audio + optional example phrase |

After editing: `uv run anki-chinese build`.

## Deck settings

Update `src/anki_chinese/config.py`:

- `DECK_NAME` — display name in Anki
- `FIELDS` — field list (must match card templates)

Do not change `MODEL_ID` or `DECK_ID` after first import — Anki will create duplicates. See the [Anki model reference](../reference/anki-model.md).

## TTS settings

See the [TTS setup guide](tts-setup.md) for credential setup.

Runtime defaults for MiniMax live in `src/anki_chinese/audio/minimax.py`. Runtime defaults for Google live in `src/anki_chinese/audio/google_tts.py`. Override with environment variables only when needed:

| Variable | Purpose |
|----------|---------|
| `MINIMAX_API_HOST` | Mainland-region keys: `https://api.minimaxi.com` |
| `MINIMAX_TTS_MODEL` | Different MiniMax speech model |
| `MINIMAX_MANDARIN_VOICE_ID` | Different Mandarin voice |
| `MINIMAX_CANTONESE_VOICE_ID` | Different Cantonese voice |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google service-account JSON path |
| `GOOGLE_TTS_ENDPOINT` | Different Google TTS endpoint |
| `GOOGLE_TTS_MANDARIN_VOICE` | Different Google Mandarin voice |
| `GOOGLE_TTS_CANTONESE_VOICE` | Different Google Cantonese voice |

Provider-specific code is contained in `src/anki_chinese/audio/`. The CLI and note pipeline remain provider-neutral.

## Example words

Edit `data/manual/example_words.json`:

```json
{
  "早": { "word": "早上", "meaning": "morning", "pinyin": "zǎo shang" },
  "大": { "word": "大学", "meaning": "university", "pinyin": "dà xué" }
}
```

Then rerun `uv run anki-chinese init`.

- Manual entries always override auto-generated examples.
- If `pinyin` is omitted, the tool derives it automatically.
- Auto-pick uses frequency-based selection from HSK vocabulary (`hsk_complete.min.json`).
Manual example-word data feeds enrichment and lookup behavior; generated card fields are documented in the [Anki model reference](../reference/anki-model.md).

# Customization guide

Non-default tweaks only. For normal install, workflow, and repo layout see the [development guide](development.md).

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

⚠️ Do not change `MODEL_ID` or `DECK_ID` after first import — Anki will create duplicates.

## TTS settings

See the [TTS setup guide](tts-setup.md) for API key configuration.

Runtime defaults for MiniMax live in `src/anki_chinese/audio/minimax.py`. Runtime defaults for Google live in `src/anki_chinese/audio/google_tts.py`. Override with environment variables only when needed:

| Variable | Purpose |
|----------|---------|
| `MINIMAX_API_HOST` | Mainland-region keys: `https://api.minimaxi.com` |
| `MINIMAX_TTS_MODEL` | Different MiniMax speech model |
| `MINIMAX_MANDARIN_VOICE_ID` | Different Mandarin voice |
| `MINIMAX_CANTONESE_VOICE_ID` | Different Cantonese voice |
| `GOOGLE_TTS_API_KEY` | Google Cloud TTS API key |

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
- Listening front shows the example only when `ExampleWord` is present.

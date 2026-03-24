# Customization Guide

This document only covers non-default tweaks. Normal install, workflow, repo layout, and validation all live in `README.md`.

## Override specific character data

Edit `data/manual/overrides.json` to force fields per character:

```json
{
  "行": { "pinyin": "xíng", "jyutping": "haang4", "keyword": "go" },
  "了": { "pinyin": "le" }
}
```

Then rerun:

```bash
uv run anki-chinese init
```

## Edit card files

Files in `src/anki_chinese/cards/` control card UI:

- `style.css`
- `recognition_front.html`
- `recognition_back.html`
- `recall_front.html` (listening front: audio + optional example phrase)
- `recall_back.html`

After editing card files:

```bash
uv run anki-chinese build
```

## Edit deck settings

Update `src/anki_chinese/config.py`:

- `DECK_NAME`
- `FIELDS`

Important:

- Do not change `MODEL_ID` or `DECK_ID` after first import, or Anki may create duplicates.

## TTS settings

MiniMax runtime defaults live in `src/anki_chinese/audio/minimax.py`.

That is the preferred home for non-secret, repo-owned choices like:

- the default MiniMax speech model
- the default Mandarin voice ID
- the default Cantonese voice ID
- the default global API host

Use environment variables only when you intentionally want to override those defaults for your machine or account:

- `MINIMAX_API_HOST`
- `MINIMAX_TTS_MODEL`
- `MINIMAX_MANDARIN_VOICE_ID`
- `MINIMAX_CANTONESE_VOICE_ID`

Provider-specific logic lives in:

- `src/anki_chinese/audio/provider.py`
- `src/anki_chinese/audio/minimax.py`
- `src/anki_chinese/audio/errors.py`
- `src/anki_chinese/audio/factory.py`
- `src/anki_chinese/audio/retry.py`
- `src/anki_chinese/audio/files.py`

That keeps the CLI and note pipeline provider-neutral while the concrete implementation stays deep and contained in one module.

## Add example words

Edit `data/manual/example_words.json`:

```json
{
  "早": { "word": "早上", "meaning": "morning", "pinyin": "zǎo shang" },
  "大": { "word": "大学", "meaning": "university", "pinyin": "dà xué" }
}
```

Then rerun `init`.

Notes:

- If a character has no manual example, the tool tries to auto-pick a common 2-character word.
- Manual entries in `data/manual/example_words.json` always override auto-generated examples.
- If `pinyin` is omitted for a manual example, the tool derives it automatically before TTS.
- Auto-pick policy is frequency-based from Complete HSK Vocabulary (`complete.min.json`): lower `frequency` rank means more common.
- Listening front shows the example only when `ExampleWord` is present (no placeholder when missing).

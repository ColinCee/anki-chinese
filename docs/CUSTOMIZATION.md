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
- `MANDARIN_VOICE`
- `CANTONESE_VOICE`

Important:

- Do not change `MODEL_ID` or `DECK_ID` after first import, or Anki may create duplicates.

## TTS provider notes

Today the project still uses Azure, but the code is now split so provider-specific logic lives in:

- `src/anki_chinese/audio/provider.py`
- `src/anki_chinese/audio/azure.py`
- `src/anki_chinese/audio/retry.py`
- `src/anki_chinese/audio/files.py`

That means future provider changes should mostly stay inside `src/anki_chinese/audio/` instead of leaking across the CLI and note logic.

Shortlist for replacing Azure:

- **Amazon Polly** — best current fit for Mandarin + Cantonese plus explicit pronunciation control
- **Google Cloud Text-to-Speech** — strong API maturity and Mandarin quality; Cantonese still needs direct evaluation for this deck
- **ElevenLabs** — promising naturalness, but should be tested carefully on exact-pronunciation Chinese study content before adopting it

For now, voice names still come from `src/anki_chinese/config.py`:

- `MANDARIN_VOICE`
- `CANTONESE_VOICE`

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

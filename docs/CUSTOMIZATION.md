# Customization Guide

## Override specific character data

Edit `data/overrides.json` to force fields per character:

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

## Edit card templates

Files in `templates/` control card UI:

- `style.css`
- `recognition_front.html`
- `recognition_back.html`
- `recall_front.html` (listening front)
- `recall_back.html`

After editing templates:

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

## Add example words

Edit `data/example_words.json`:

```json
{
  "早": { "word": "早上", "meaning": "morning" },
  "大": { "word": "大学", "meaning": "university" }
}
```

Then rerun `init`.

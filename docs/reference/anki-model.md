# Anki model reference

This project builds one Anki note per Chinese character.

## Stable identity

`src/anki_chinese/config.py` defines:

| Setting | Purpose |
| --- | --- |
| `DECK_ID` | Stable genanki deck ID. |
| `MODEL_ID` | Stable genanki note type/model ID. |
| `DECK_NAME` | Display name in Anki. |
| `MODEL_NAME` | Anki note type name. |

Do not change `DECK_ID` or `MODEL_ID` after first import. Anki uses them to decide whether an import updates existing notes or creates new deck/model identities.

Note GUIDs are based on the character identity, so re-importing a regenerated package updates notes instead of duplicating them.

## Fields

The field order in `config.FIELDS` must match `CharacterNote.to_fields_list()` and the card templates.

| Field | Purpose |
| --- | --- |
| `Hanzi` | Target character. |
| `Meaning` | English meaning, often with compound context. |
| `Pinyin` | Mandarin reading used by generated audio and sentences. |
| `Jyutping` | Cantonese reading. |
| `MandarinAudio` | Single-character Mandarin audio tag. |
| `CantoneseAudio` | Single-character Cantonese audio tag. |
| `StrokeOrder` | Stroke order field from source/enrichment. |
| `HeisigNum` | Remembering Simplified Hanzi index. |
| `Lesson` | RSH lesson. |
| `Story` | Optional mnemonic/story field. |
| `SentenceAudio` | Sentence audio tag. |
| `Sentence` | Example sentence. |
| `SentencePinyin` | Pinyin for the example sentence. |
| `SentenceEnglish` | English translation of the example sentence. |

## Cards

Card templates live in `src/anki_chinese/cards/`.

| File | Role |
| --- | --- |
| `recognition_front.html` / `recognition_back.html` | Character-to-meaning direction. |
| `recall_front.html` / `recall_back.html` | Listening-first recall direction. |
| `style.css` | Shared styling. |

If you add, remove, or rename fields, update:

1. `src/anki_chinese/config.py`
2. `src/anki_chinese/notes/model.py`
3. card templates under `src/anki_chinese/cards/`
4. tests covering template/field sync

## Import behavior

The normal rebuild loop is:

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

Then import:

```text
data/build/decks/chinese_rsh.apkg
```

Content imports update note fields and templates. They are not the right tool for changing live suspended state after reviews; use AnkiConnect activation commands for that lane.

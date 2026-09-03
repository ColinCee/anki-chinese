---
name: anki-card-edit-regeneration
description: Use when editing or adding an anki-chinese per-character card field such as meaning, pinyin, jyutping, sentence, sentence pinyin, sentence English, or story. Ensures source-deck edits are followed by targeted audio regeneration and APKG rebuild.
when_to_use: Trigger on requests to update, change, fix, rewrite, set, add, or repair a character card's meaning, pronunciation, sentence, translation, mnemonic story, missing note, or other `anki-chinese card set` field.
argument-hint: "<hanzi>"
---

# Anki Card Edit Regeneration

Card content flows from the canonical source through generated state and audio
to the rebuilt APKG. Do not create or patch a live-only Anki note.

```bash
uv run anki-chinese card show <hanzi> --json
uv run anki-chinese card set <hanzi> --meaning "..." --sentence "..." ...
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

If `card show` reports a missing character, use `card add` instead of
AnkiConnect:

```bash
uv run anki-chinese card add <hanzi> \
  --meaning "sense-aware gloss; relevant compound context" \
  --sentence "..." \
  --sentence-pinyin "..." \
  --sentence-english "..."
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

Rules specific to card edits:

- Provide sentence, pinyin, and English together when changing a sentence.
- Keep meanings compact and sense-aware; update the meaning when the sentence
  changes to a different sense or compound.
- Use `--track rsh --rsh-number N` only for a real RSH entry; new records are
  custom by default.
- Prefer `card set` and `card add` over ad hoc JSON, SQLite, or AnkiConnect edits.
- Use the live-activation safety workflow if live import or activation is also
  requested.

Confirm the final `card show` output and report the rebuilt
`data/build/decks/chinese_rsh.apkg`. See `docs/workflows.md` for user-facing
card procedures and `docs/architecture.md` for the source-to-APKG flow.

---
name: anki-card-edit-regeneration
description: Use when editing or adding an anki-chinese per-character card field such as meaning, pinyin, jyutping, sentence, sentence pinyin, sentence English, or story. Ensures source-deck edits are followed by targeted audio regeneration and APKG rebuild.
when_to_use: Trigger on requests to update, change, fix, rewrite, set, add, or repair a character card's meaning, pronunciation, sentence, translation, mnemonic story, missing note, or other `anki-chinese card set` field.
argument-hint: "<hanzi>"
---

# Anki Card Edit Regeneration

## First response checklist

When this skill is relevant:

1. Treat the edit as a source-deck/generated-deck workflow, not a live AnkiConnect
   activation unless the user explicitly asks to mutate live Anki.
2. Inspect the current card first with `uv run anki-chinese card show <hanzi> --json`.
3. If the character is missing from `card show`, add it with
   `uv run anki-chinese card add <hanzi> --meaning "..."` rather than using
   AnkiConnect. New live cards must arrive by importing the rebuilt APKG, so the
   canonical source and live deck stay aligned.
4. Use a compact, sense-aware meaning rather than a bare one-word gloss. Include
   the important core senses and, when the card is introduced through a compound,
   explain that usage too. For example, `账` can use
   `account; bill/check; debt; in 结账: to pay the bill`.
5. Check that the meaning/explanation matches the example sentence and word
   sense. If a sentence changes from one compound/sense to another, update the
   meaning too instead of leaving a stale gloss.
6. Apply an existing-card edit through `uv run anki-chinese card set <hanzi> ...`.
   When changing an example sentence, provide the sentence, pinyin, and English
   fields together.
7. Run the canonical sync pipeline so the source edit is re-enriched, required
   audio is regenerated, and the APKG is rebuilt.
8. Report the updated sentence/meaning and the generated APKG path.

## Required workflow

Use the public CLI workflow so source deck, enriched state, audio manifest, and
generated deck stay consistent:

```bash
uv run anki-chinese card show <hanzi> --json
uv run anki-chinese card set <hanzi> --meaning "..." --sentence "..." ...
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

`card set` clears stale `sentence_audio` when the sentence changes. The targeted
audio command remains available when an already-enriched character needs an
isolated regeneration:

```bash
uv run anki-chinese audio --char <hanzi> --fail-fast
uv run anki-chinese build
```

Run that direct variant only after the character exists in enriched state;
`sync` is required first when a source-only record is new or missing from the
cache.

For a missing character, use the canonical add workflow instead:

```bash
uv run anki-chinese card add <hanzi> \
  --meaning "sense-aware gloss; relevant compound context" \
  --sentence "..." \
  --sentence-pinyin "..." \
  --sentence-english "..."
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

`card add` defaults to a custom record. Use `--track rsh --rsh-number N` only
when the character is a real RSH entry. `sync` enriches the new source record,
generates required audio, and rebuilds the APKG.

When the example sentence uses a compound such as `太阳穴`, make sure the
meaning field explains that sense, not only an older unrelated compound such as
`洞穴`.

## Missing/new cards

If a requested character is not present in the canonical source or generated
state, do not "quick fix" it by creating a live Anki note only. A valid card
must exist in the canonical source and enriched state before audio/build work:

1. Add the note with `card add`, including a sense-aware meaning and the complete
   sentence triplet when an example is supplied.
2. Use `--track rsh --rsh-number N` only for a real RSH entry; otherwise keep the
   default custom track.
3. Run `uv run anki-chinese sync --dry-run`, then `uv run anki-chinese sync`.
4. Only then import the rebuilt APKG into live Anki through a backup-gated
   workflow if needed.

Partial live-only notes are considered broken for this project because they lack
generated audio, sentence fields, RSH metadata, and will not survive a rebuild
from `data/source/All Decks.apkg`.

For new cards, AnkiConnect is allowed for safety checks, backups, activation,
and cleanup of known-bad duplicates. It must not be used as the creation path.
The creation path is: canonical source -> enriched state -> audio -> built APKG
-> live import.

## Safety boundaries

- Do not use ad hoc JSON or SQLite edits when `card set` can express the change.
- Do not mutate live Anki state for card content edits unless explicitly asked.
- Do not treat `data/source/All Decks.apkg` as current live active/suspended
  state. It is source content for rebuilds, not an AnkiConnect state backup.
- If the user asks to import or activate the rebuilt APKG in live Anki, use the
  live activation/import safety workflow and verify backups first.

## Validation

After the workflow, confirm:

1. `uv run anki-chinese card show <hanzi> --json` contains the updated fields and
   any regenerated `sentence_audio`.
2. `uv run anki-chinese build` reports `data/build/decks/chinese_rsh.apkg`.

Documentation-only skill edits do not require the Python lint/type/test suite.

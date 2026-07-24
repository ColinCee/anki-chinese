# Workflows

Use the workbench for human navigation:

```bash
uv run anki-chinese
```

It recommends one next action from local state, previews safe workflows
in-place, and can run sync/doctor/card-edit and song-preview actions without
making command lists the main UI. Examples:

- setup/health when required files or credentials are missing
- sync when generated artifacts are stale
- review when notes need attention
- cleanup when orphaned audio exists
- song study when the deck is otherwise current

## Sync deck output

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

`sync` decides whether `init`, `audio`, and `build` are needed, executes needed
stages in dependency order, and replans after each stage. Use `--skip-audio`
when you intentionally want a no-network rebuild.

## Fix one card

Inspect first:

```bash
uv run anki-chinese card show 编
uv run anki-chinese card show 编 --json
```

Write the canonical source record with `card set`:

```bash
uv run anki-chinese card set 编 \
  --meaning "to compile; arrange; make up; as in 编程: programming" \
  --sentence "我最近在学编程，想自己做个小程序。" \
  --sentence-pinyin "wǒ zuì jìn zài xué biān chéng, xiǎng zì jǐ zuò ge xiǎo chéng xù" \
  --sentence-english "I’ve been learning programming recently and want to make a small app myself."
uv run anki-chinese sync
```

`card set` writes authored fields into `data/source/characters.json`. Sentence
changes require `--sentence`, `--sentence-pinyin`, and `--sentence-english`
together; they clear the cached sentence-audio field in generated state so
`sync` can regenerate matching audio.

## Add a character

New characters use the same two-card Anki projection but carry explicit
curriculum provenance. Custom characters do not receive synthetic RSH numbers:

```bash
uv run anki-chinese card add 账 \
  --meaning "account; bill/check; debt; in 结账: to pay the bill" \
  --sentence "我们吃完饭后去结账。" \
  --sentence-pinyin "wǒmen chī wán fàn hòu qù jiézhàng" \
  --sentence-english "After we finish eating, we'll pay the bill." \
  --collection restaurant-vocabulary
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

Meanings should be compact but sense-aware: list the important core senses and
explain the relevant compound or sentence usage instead of using only a broad
one-word gloss. `card add` defaults to a custom record and requires `--meaning`;
if an example sentence is supplied, all three sentence fields are required.

Use `--track rsh --rsh-number N` only for a real RSH entry. `card add` never
creates a live Anki note; import the rebuilt APKG separately, then use the
backup-gated activation workflow if the character should be unsuspended.

To replace canonical records from a newly exported legacy APKG:

```bash
uv run anki-chinese source import --input "data/source/All Decks.apkg" --replace
uv run anki-chinese sync
```

## Review deck health

```bash
uv run anki-chinese doctor
uv run anki-chinese status
uv run anki-chinese review
uv run anki-chinese radicals
```

Use `doctor --check-anki` only when Anki is open and you want to include
AnkiConnect reachability.

## Compare character frequency coverage

Rebuild the local frequency snapshot only when you want to regenerate the
derived list:

```bash
uv run anki-chinese frequency refresh
```

Then report current live Anki progress without rebuilding the list:

```bash
uv run anki-chinese frequency report
uv run anki-chinese frequency report --json
```

The report counts a character as covered only when at least one live Anki card
has a recorded review. It lists the highest-frequency uncovered characters that
are already in the deck and reports frequency-weighted reading coverage. The
HSK-style band is only a rough character-recognition comparison; it is not an
overall proficiency measure. The human report also shows reviewed/unreviewed
counts at top-rank milestones, cumulative source share for each gap, and the
potential coverage gain from the next displayed batch. JSON output retains the
underlying scores for machine-readable analysis.

## Generate sentences and meanings

Requires `GEMINI_API_KEY`:

```bash
uv run anki-chinese sentences --limit 20
uv run anki-chinese sentences --char 早 --pick 3
uv run anki-chinese keywords
uv run anki-chinese sentences audit
uv run anki-chinese sentences repair-confusers
uv run anki-chinese sentences repair-confusers --apply
uv run anki-chinese sync
```

`--pick` is interactive and refuses non-terminal execution. Scripts and agents
should use non-interactive generation commands.

## Generate audio

Provider split:

- Google Cloud Text-to-Speech for single-character Mandarin/Cantonese audio
- MiniMax for sentence audio

Smoke-test credentials first:

```bash
uv run anki-chinese test-tts --char 早 --provider google
uv run anki-chinese test-tts --word 早上 --provider minimax
```

Then generate:

```bash
uv run anki-chinese audio --limit 20
uv run anki-chinese audio
uv run anki-chinese sync
```

Audio provenance is stored locally in `data/state/audio_manifest.json` so
`sync`, `status`, `doctor`, and `build` can detect missing, stale, or orphaned
generated files.

Cleanup is preview-first:

```bash
uv run anki-chinese audio-clean
uv run anki-chinese audio-clean --apply
```

## Learn characters from songs

Song planning uses live Anki state through AnkiConnect. Keep Anki open.

```bash
uv run anki-chinese doctor --check-anki
uv run anki-chinese songs verify
uv run anki-chinese songs analyze
uv run anki-chinese songs next --limit 20
```

For normal human study, prefer `songs learn`:

```bash
uv run anki-chinese songs learn --limit 20
uv run anki-chinese songs learn --limit 20 --confirm
```

Without `--confirm`, live mutation commands preview only. Confirmed activation
and resuspension write targeted undo snapshots under `data/build/anki_backups/`.
Confirmed undo writes a `restore-*.json` safety snapshot before changing live
cards or tags.

Undo song activation:

```bash
uv run anki-chinese songs undo
uv run anki-chinese songs undo --confirm
```

Lower-level commands remain available:

```bash
uv run anki-chinese songs activate 学猫叫 --limit 20 --dry-run
uv run anki-chinese activate chars 内 合 哟 着 --dry-run
uv run anki-chinese activate snapshots list
uv run anki-chinese activate undo latest
```

## Customize data or templates

- Per-character content: prefer `card set` or `card add`; canonical records live
  in `data/source/characters.json`.
- Example words: edit `data/manual/example_words.json`, then run `sync`.
- Card templates: edit `src/anki_chinese/cards/`, then run `sync`.
- Deck/model identity: do not change `MODEL_ID`, `DECK_ID`, field order, or GUID behavior without a migration plan.

The default learner target is mainland Mandarin with simplified characters for
active study and traditional characters as recognition support. Song planning
maps particle `著` to `着` for study planning while preserving lexical `著`
words such as `著名` and `原著`.

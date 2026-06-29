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

Write the source deck with `card set`:

```bash
uv run anki-chinese card set 编 \
  --meaning "to compile; arrange; make up; as in 编程: programming" \
  --sentence "我最近在学编程，想自己做个小程序。" \
  --sentence-pinyin "wǒ zuì jìn zài xué biān chéng, xiǎng zì jǐ zuò ge xiǎo chéng xù" \
  --sentence-english "I’ve been learning programming recently and want to make a small app myself."
uv run anki-chinese sync
```

`card set` writes the note fields inside `data/source/All Decks.apkg`. Sentence
changes clear the cached sentence-audio field so `sync` can regenerate matching
audio.

## Review deck health

```bash
uv run anki-chinese doctor
uv run anki-chinese status
uv run anki-chinese review
uv run anki-chinese radicals
```

Use `doctor --check-anki` only when Anki is open and you want to include
AnkiConnect reachability.

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

- Per-character content: prefer `card set`; batch edits should update `data/source/All Decks.apkg`.
- Example words: edit `data/manual/example_words.json`, then run `sync`.
- Card templates: edit `src/anki_chinese/cards/`, then run `sync`.
- Deck/model identity: do not change `MODEL_ID`, `DECK_ID`, field order, or GUID behavior without a migration plan.

The default learner target is mainland Mandarin with simplified characters for
active study and traditional characters as recognition support. Song planning
maps particle `著` to `着` for study planning while preserving lexical `著`
words such as `著名` and `原著`.

# Deck rebuild workflow

Use this workflow when you want to rebuild note content, generated sentences, audio references, or card templates.

## Rebuild lane

```text
Anki export -> sync/init -> optional sentences/keywords/audio -> sync/build -> Anki import
```

Live review state such as suspension, due dates, intervals, and review history lives in Anki. Rebuilds should preserve that state when imported with stable IDs, but they are not a substitute for live activation commands.

## 1. Export from Anki

Export a current native Anki package to:

```text
data/source/All Decks.apkg
```

Use a fresh export before analyses that depend on current note content. For live active/suspended state, prefer AnkiConnect commands because an exported `.apkg` can lag behind the open collection.

## 2. Parse and enrich

```bash
uv run anki-chinese init
```

`init` parses the source export, enriches notes with readings and lookup data, restores cached generated fields from the previous `data/state/enriched.json` when valid, clears stale audio references, and saves the state file.

For normal rebuilds, prefer the state-aware planner:

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

`sync` decides whether `init`, `audio`, and `build` are needed, executes needed
stages in dependency order, and replans after each completed stage.

## 3. Inspect status

```bash
uv run anki-chinese status
uv run anki-chinese review
```

Use `review` when `status` reports notes flagged for manual correction. Manual corrections usually go in `data/manual/overrides.json`; rerun `init` after editing overrides.

`status` also reports audio health from the same state model used by `sync`.
This is the intended place to see whether generated audio is missing, stale, or
orphaned without adding a separate diagnostic step to the normal workflow.

## 4. Optional generated content

Sentences and meanings:

```bash
uv run anki-chinese sentences
uv run anki-chinese keywords
uv run anki-chinese sentences audit
```

Audio:

```bash
uv run anki-chinese audio
```

For large runs, use `--limit`, `--start-rsh`, and provider smoke tests first.
Generated audio provenance is recorded locally in
`data/state/audio_manifest.json`. If provider settings change, for example a new
MiniMax model or voice, `sync` and `audio` can detect that existing files need
regeneration even when their filenames still match.

## 5. Build

```bash
uv run anki-chinese build
```

Output:

```text
data/build/decks/chinese_rsh.apkg
```

`build` does not mutate audio by itself. If expected audio is missing or stale it
warns before packaging; run `uv run anki-chinese sync` or
`uv run anki-chinese audio` to refresh audio first.

## Full pipeline shortcut

Prefer `sync` for normal state-aware rebuilds. `build --full` is a primitive
shortcut when you explicitly want to run every rebuild step:

```bash
uv run anki-chinese build --full
```

This runs `init -> audio -> build`. To skip audio:

```bash
uv run anki-chinese build --full --skip-audio
```

Limit the audio part of a full build:

```bash
uv run anki-chinese build --full --audio-limit 50
uv run anki-chinese build --full --audio-start-rsh 500
```

## 6. Import into Anki

Import the generated `.apkg` into Anki. Stable deck/model IDs and character-based GUIDs let the import update existing notes rather than creating duplicate notes.

Do not change `MODEL_ID`, `DECK_ID`, or field order casually. See the [Anki model reference](../reference/anki-model.md).

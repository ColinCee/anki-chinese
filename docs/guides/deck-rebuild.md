# Deck rebuild workflow

Use this workflow when you want to rebuild note content, generated sentences,
audio references, or card templates.

## Rebuild lane

```text
Anki export -> dashboard/doctor -> sync -> optional card/content/audio work -> sync -> Anki import
```

Live review state such as suspension, due dates, intervals, and review history lives in Anki. Rebuilds should preserve that state when imported with stable IDs, but they are not a substitute for live activation commands.

## 1. Export from Anki

Export a current native Anki package to:

```text
data/source/All Decks.apkg
```

Use a fresh export before analyses that depend on current note content. For live active/suspended state, prefer AnkiConnect commands because an exported `.apkg` can lag behind the open collection.

## 2. Check the local workflow state

```bash
uv run anki-chinese doctor
uv run anki-chinese
```

`doctor` is a read-only readiness check. The dashboard is the human entrypoint:
it recommends one workflow from local state and shows the equivalent CLI
commands. In non-interactive scripts, use `sync --dry-run --json` instead.

## 3. Sync generated artifacts

For normal rebuilds, prefer the state-aware planner:

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

`sync` decides whether `init`, `audio`, and `build` are needed, executes needed
stages in dependency order, and replans after each completed stage.

Use `--skip-audio` when you intentionally want a no-network rebuild:

```bash
uv run anki-chinese sync --skip-audio
```

## 4. Inspect or fix cards

```bash
uv run anki-chinese status
uv run anki-chinese review
uv run anki-chinese card show 水
```

Use `review` when `status` reports notes flagged for manual correction. Prefer
`card set` for one-card fixes so sentence changes clear stale sentence audio:

```bash
uv run anki-chinese card set 水 \
  --meaning "water; liquid" \
  --sentence "我每天都喝水。" \
  --sentence-pinyin "wǒ měi tiān dōu hē shuǐ" \
  --sentence-english "I drink water every day."
uv run anki-chinese sync
```

Manual JSON in `data/manual/overrides.json` remains available for batch edits,
but do not edit `data/state/enriched.json` by hand.

`status` also reports audio health from the same state model used by `sync`.
This is the intended place to see whether generated audio is missing, stale, or
orphaned without adding a separate diagnostic step to the normal workflow.

## 5. Optional generated content

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

After content or audio generation, run `sync` again so downstream stages refresh:

```bash
uv run anki-chinese sync
```

## 6. Build output

Output:

```text
data/build/decks/chinese_rsh.apkg
```

`sync` normally runs `build` when needed. `build` remains available as a
primitive, but it does not mutate audio by itself. If expected audio is missing
or stale it warns before packaging; run `sync` or `audio` to refresh audio first.

## 7. Import into Anki

Import the generated `.apkg` into Anki. Stable deck/model IDs and character-based GUIDs let the import update existing notes rather than creating duplicate notes.

Do not change `MODEL_ID`, `DECK_ID`, or field order casually. See the [Anki model reference](../reference/anki-model.md).

---
name: anki-live-activation-safety
description: Use before any anki-chinese live AnkiConnect mutation or live-state song planning. Requires dry-run, backup/undo snapshot, exact card/note counts, and live active-state queries before unsuspending or tagging cards.
when_to_use: Trigger on requests to activate, unsuspend, suspend, tag, plan next song characters from live Anki, query unsuspended data from AnkiConnect, or edit src/anki_chinese/activation, cli/activate.py, or cli/songs.py.
argument-hint: "[chars-or-song-query]"
---

# Anki Live Activation Safety

## First response checklist

When this skill is relevant:

1. Say whether the task will mutate live Anki state.
2. If it will mutate state, run or recommend a `--dry-run` first.
3. Create or verify a backup/undo snapshot before the real mutation.
4. Use live AnkiConnect state for follow-up planning after any live activation.
5. Report exact changed card and note counts.

## Core rule

Before mutating live Anki state, create a backup that is appropriate for the
operation:

1. For broad or uncertain changes, make a full Anki export/backup first.
2. For targeted activation batches, write an undo snapshot containing note IDs,
   card IDs, target characters, and pre-change suspended state.
3. Only then run the activation.

Do not rely on `data/source/All Decks.apkg` as a live-state backup unless it was
exported immediately before the mutation. The source `.apkg` is a snapshot and
can lag behind live Anki after AnkiConnect operations.

## Recommended backup levels

### Level 1: Full Anki backup/export

Use this for risky/broad changes, first-time automation, or anything touching
many notes. Prefer Anki's built-in automatic backups or a manual collection/deck
export from Anki.

If using AnkiConnect, verify the exact `exportPackage` parameters against the
installed AnkiConnect version before relying on it; do not guess a destructive
or misleading export command.

### Level 2: Activation undo snapshot

Use this for normal character activation batches. Before unsuspending cards,
query AnkiConnect and persist a JSON file outside committed source, for example:

`data/build/anki_backups/activation-YYYYMMDD-HHMMSS.json`

The snapshot should include:

- timestamp
- requested characters
- model name
- note IDs
- card IDs
- pre-change suspended card IDs
- already-active characters
- missing characters
- tag to be applied, if any

This enables a targeted undo by suspending only the cards that were suspended
before the activation and optionally removing any activation tag if needed.

The public `activate chars`, `songs activate`, and `songs resuspend` commands
write targeted undo snapshots automatically for real mutations. If a future or
custom operation does not provide an automated snapshot command, require a
manual Anki backup/export before the real mutation instead of implying that the
source `.apkg` is enough.

### Level 3: Dry-run only

Use `--dry-run` before every unfamiliar activation command:

```bash
uv run anki-chinese activate chars 人 来 为 --dry-run
uv run anki-chinese songs activate 月亮代表我的心 --limit 10 --dry-run
```

Dry-runs are not backups. They are a preview step.

## Live active-state planning

For next-song planning after live activations, prefer live AnkiConnect state
over `load_learned_hanzi_from_apkg` when Anki is open.

Live active character rule:

- fetch notes for model `Chinese RSH`
- collect note card IDs
- call `areSuspended`
- treat a character as active if any card for that note is not suspended

This matches the project convention used for `.apkg` snapshots: a character is
learned/active if any of its cards are unsuspended.

## Safe execution sequence

For any live activation task:

1. Check `git status --short` so repo changes are not confused with live Anki
   changes.
2. Run the activation command with `--dry-run`.
3. Run the real activation only through a path that writes an activation undo
   snapshot before mutating Anki.
4. Verify/report the snapshot path from command output.
5. Report exactly how many cards and notes changed.
6. If planning another song immediately afterward, query live AnkiConnect state
   instead of relying on the exported `.apkg`.

## Minimal live-state query pattern

When implementation work is requested, prefer adding a public helper behind the
existing activation boundary rather than ad hoc scripts in CLI code.

The helper should:

1. Find notes with `note:"Chinese RSH"`.
2. Read the configured Hanzi field from `notesInfo`.
3. Collect each note's card IDs.
4. Call `areSuspended`.
5. Return characters where at least one card is unsuspended.

This mirrors `load_learned_hanzi_from_apkg`: a character is active if any card
for its note is unsuspended.

## Undo snapshot shape

For targeted activation, write JSON like:

```json
{
  "created_at": "2026-04-28T00:00:00Z",
  "operation": "activate-chars",
  "model_name": "Chinese RSH",
  "requested_chars": ["人", "来"],
  "found_chars": ["人", "来"],
  "missing_chars": [],
  "already_active_chars": [],
  "note_ids": [123, 456],
  "card_ids": [10, 11, 20, 21],
  "pre_change_suspended_card_ids": [10, 11, 20, 21],
  "tag": "activated::song::example"
}
```

Store snapshots under an ignored build/output location, for example
`data/build/anki_backups/`.

## Review guidance

Flag PRs or scripts that:

- mutate Anki live state without a dry-run path
- mutate Anki live state without a backup/undo snapshot option
- treat `data/source/All Decks.apkg` as current after live AnkiConnect changes
- swallow AnkiConnect errors or continue after partial failures
- make broad state changes without reporting affected note/card IDs

Prefer implementations that:

- keep AnkiConnect behind the existing activation client/service boundary
- add backup files under `data/build/anki_backups/` or another ignored build
  location
- store enough card state to undo targeted unsuspends
- use explicit tags for activated batches, such as `activated::song::<title>`

---
name: anki-live-activation-safety
description: Use before any anki-chinese live AnkiConnect mutation or live-state song planning. Requires dry-run, backup/undo snapshot, exact card/note counts, and live active-state queries before unsuspending or tagging cards.
when_to_use: Trigger on requests to activate, unsuspend, suspend, tag, plan next song characters from live Anki, query unsuspended data from AnkiConnect, or edit src/anki_chinese/activation, cli/activate.py, or cli/songs.py.
argument-hint: "[chars-or-song-query]"
---

# Anki Live Activation Safety

State explicitly whether the task mutates live Anki. For every mutation:

```bash
uv run anki-chinese activate chars 人 来 为 --dry-run
uv run anki-chinese songs activate 月亮代表我的心 --limit 10 --dry-run
```

Then:

1. Use a public command that writes its undo snapshot before mutation.
2. Verify the snapshot path under `data/build/anki_backups/`.
3. Report exact changed card and note counts, plus missing or already-active
   characters.
4. Query live AnkiConnect state before follow-up planning.

Dry-runs are previews, not backups. Use a full Anki backup/export for broad,
uncertain, or first-time automation. Never treat
`data/source/All Decks.apkg` as current live state unless it was exported
immediately before the operation.

Targeted snapshots must retain enough state to undo safely: operation,
requested/found/missing characters, note and card IDs, pre-change suspended
card IDs, already-active characters, and any applied tag. Public activation,
resuspension, and undo paths should create their required safety snapshot
automatically.

For implementation work:

- Keep AnkiConnect calls behind `activation/`; do not add ad hoc CLI queries.
- A character is active when any card belonging to its `Chinese RSH` note is
  unsuspended.
- Propagate partial failures; never continue with a success-shaped result.
- Reject mutation paths without dry-run support, pre-mutation snapshots, and
  affected note/card reporting.

See `docs/workflows.md` for commands and `docs/architecture.md` for the live
activation boundary.

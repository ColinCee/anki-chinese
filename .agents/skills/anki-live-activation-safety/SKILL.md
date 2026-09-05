---
name: anki-live-activation-safety
description: Use for live Anki state planning, activation, suspension, tagging, undo, or changes to those mutation paths. Separate read-only queries from mutations; require previews, pre-mutation snapshots, and exact affected counts for writes.
---

# Live Anki safety

Classify the task first. Read-only planning needs fresh live state, not a backup
or mutation confirmation. An active character has any card unsuspended; that does
not imply a recorded review. Offline docs/template work needs neither.

For writes, follow [the live workflow](../../../docs/workflows.md#learn-characters-from-songs):

1. Preview the exact operation and scope before confirmation.
2. Use a public command whose service writes the safety snapshot before mutation.
   Retain its path and report exact changed card/note counts, missing characters,
   and already-active characters.
3. Preserve an undo path; a dry-run is not a backup. Use a full Anki backup for
   broad, uncertain, or first-time automation.
4. Query live state again before subsequent planning; never infer it from an old
   export or a previous plan.

For implementation, keep calls behind `activation/`; preserve pre-change IDs,
suspension state, tag ownership, and operation metadata needed for undo.
Activation, resuspension, and undo all need pre-mutation safety snapshots.
See `src/anki_chinese/activation/snapshots.py` for the schema, not a copied field
list. Propagate partial failures and report them; never present partial success
as a completed mutation.

Stop after the authorized operation and its result; do not activate the next
batch automatically. For guidance friction, apply the shared
[maintenance loop](../../../CONTRIBUTING.md#maintaining-docs-and-skills) once.

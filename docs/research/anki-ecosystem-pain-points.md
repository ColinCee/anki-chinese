# Anki ecosystem pain points

This is a running record of Anki friction points encountered while building
`anki-chinese`. The goal is not to justify replacing Anki today; it is to track
where Anki helps, where it hurts, and what would make a custom study app worth
building later.

## Current stance

Keep Anki as the review engine for now.

Anki still provides valuable infrastructure that would be expensive to recreate:

- mature spaced-repetition scheduling
- FSRS support
- mobile review clients
- sync, backups, undo, and review history
- card templates, media handling, and deck import/export
- a large ecosystem of add-ons and existing workflows

The current project strategy is to own the parts that are specific to Chinese
learning while leaving scheduling/review execution in Anki:

| Area | Owner |
| --- | --- |
| Character data, meanings, readings, sentences, audio, templates | `anki-chinese` |
| Song planning and activation batches | `anki-chinese` |
| Live card scheduling and review history | Anki |
| Live unsuspending/tagging | `anki-chinese` via AnkiConnect |

## Pain points observed

### Import/export is awkward but necessary

The `.apkg` workflow is good for rebuilding content but poor for live study
state. Rebuilding audio, sentences, and card templates still requires exporting
from Anki, running the pipeline, building a new package, and importing it again.

This creates two sources of truth:

- exported `.apkg` snapshot for content analysis
- live Anki collection for suspension, due dates, intervals, and review history

Mitigation: keep a clear two-lane workflow. Use `.apkg` for rebuildable content
and AnkiConnect for live activation.

### Live state is hard to automate safely

Unsuspending a batch manually in Anki is tedious. Editing `.apkg` files is not a
reliable way to change live suspension state. Directly editing
`collection.anki2` would be powerful but risky.

Mitigation: use AnkiConnect for live mutations and keep the activation layer
small, explicit, and dry-run friendly.

### AnkiConnect works but feels old

AnkiConnect is a long-lived add-on with a stable local HTTP API, but the
ecosystem around it feels dated. The original GitHub repository moved/archived,
documentation is spread across locations, and behavior sometimes needs probing
against the local installed version.

Mitigation: keep AnkiConnect behind a thin adapter so future backends can be
swapped in. Do not let the whole codebase depend directly on AnkiConnect payload
shapes.

### WSL + Windows Anki adds networking friction

When Anki runs on Windows and the CLI runs in WSL, localhost may not work unless
WSL mirrored networking is enabled. Binding AnkiConnect to `0.0.0.0` would be
convenient but has a worse security posture.

Mitigation: use WSL mirrored networking and keep AnkiConnect bound to
`127.0.0.1`.

### Statistics are not cleanly exposed as a product API

Anki's stats screen shows useful information, but there is no simple
machine-readable "give me the stats widget" endpoint. AnkiConnect exposes enough
raw data for many stats (`cardsInfo`, `getDeckStats`, `cardReviews`,
`getReviewsOfCards`), but reproducing full widget parity means reimplementing
some of Anki's calculations.

Likely easy via AnkiConnect:

- cards studied today and total review time
- answer button counts
- learn/review/relearn breakdown
- young/mature retention
- card counts
- intervals and due counts
- tag/song-batch performance

Likely harder or approximate:

- FSRS stability
- FSRS difficulty
- retrievability
- estimated total knowledge
- exact future due projections
- exact graph binning used by Anki's UI

Mitigation: start with lightweight direct API summaries if needed. Avoid a large
stats subsystem until the analysis need is clear.

### Scheduler internals are opaque

FSRS is valuable, but exact scheduler state and derived quantities are not as
easy to inspect or reproduce as ordinary card fields. A custom app would make
experimentation easier, but would also require owning scheduling correctness.

Mitigation: rely on Anki/FSRS for scheduling and only compute advisory metrics
outside Anki.

### Add-on ecosystem is powerful but uneven

Many add-ons solve narrow problems, but quality, maintenance status,
documentation, hosting, and compatibility vary. Depending on add-ons increases
setup complexity and makes the workflow feel fragile.

Mitigation: depend on as few add-ons as possible. Currently AnkiConnect is the
only live automation dependency.

## What would justify a custom app?

A custom app may become worth it if several of these become true:

- Import/export becomes the dominant time cost of maintaining the deck.
- AnkiConnect becomes unreliable or incompatible with current Anki.
- We need first-class song/text-driven learning flows that Anki cannot model
  cleanly.
- We need stats/analysis that require too much reverse engineering of Anki
  internals.
- Card template limitations block the learning UX.
- We want a custom review experience rather than just generated Anki cards.
- The project needs to own scheduling experiments rather than rely on FSRS.

## Reasons not to build a custom app yet

Building a custom app would require replacing a lot of boring but important
infrastructure:

- review scheduling
- FSRS or another scheduler
- mobile review experience
- sync and conflict handling
- backups and data recovery
- media storage
- review history
- deck/card editor UX
- statistics
- import/export

The current pain is real, but not yet large enough to justify rebuilding all of
that.

## Near-term direction

Keep using Anki, but make `anki-chinese` the control layer:

- content rebuilds through `.apkg`
- live activation through AnkiConnect
- song and future text/LLM planners that output character batches
- small direct API stats commands only when they answer concrete questions

Revisit the custom-app decision if Anki friction starts blocking learning rather
than merely annoying development.

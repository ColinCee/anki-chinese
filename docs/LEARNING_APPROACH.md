# Learning Approach

## Intent

This deck is designed as a listening-first, usage-aware extension of a character-first Heisig workflow.

Core intent:

- Keep Heisig-style character decomposition and mnemonic consistency.
- Add pronunciation as a first-class recall target (Mandarin primary, Cantonese support).
- Anchor each character in at least one common real-world phrase when possible.
- Preserve stable note identity so re-imports update existing review history.

## Why this over standard Heisig-only flow

A normal Heisig progression is excellent for fast character meaning recall, but it often delays pronunciation and usage context. This project keeps the Heisig strengths while addressing those gaps earlier.

Compared to standard Heisig-only practice:

- Listening-first front cards force direct sound recognition.
- Reading fields (`Pinyin`, `Jyutping`) drive pronunciation decisions.
- Common phrase examples provide immediate lexical context.
- Regenerable deck builds let you iterate data quality without resetting progress.

## Front-card philosophy

For listening (`recall_front`):

- Show Mandarin audio prompt.
- Do not show keyword on the front.
- Show an example phrase only when available.
- Keep pinyin as optional hint behind a reveal.

This preserves challenge while still offering a controlled fallback when needed.

## Example phrase policy

The project uses a strict priority order:

1. Manual example from `data/example_words.json`.
2. Automatic fallback: best-ranked 2-character word containing the character from Complete HSK Vocabulary frequency data.
3. If nothing is available, leave example blank.

This policy keeps iteration simple:

- You can start with broad automatic coverage.
- You can progressively override edge cases with curated examples.

## Pronunciation policy

Pronunciation and audio are reading-driven:

- Mandarin audio is generated from `Pinyin`.
- Cantonese audio is generated from `Jyutping`.
- Keyword text is not used to choose pronunciation.

For polyphonic characters with missing source readings, entries are flagged for manual review.

## Iteration loop

Recommended workflow after exporting from Anki:

1. Export deck to `data/Exported-deck.txt`.
2. Run `uv run anki-chinese init`.
3. Run `uv run anki-chinese review` and fix readings/examples via overrides.
4. Optionally run `uv run anki-chinese audio`.
5. Run `uv run anki-chinese build` and re-import.

Because note GUIDs are stable by character, updates should merge into existing notes instead of duplicating them.

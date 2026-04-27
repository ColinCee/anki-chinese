# ADR-003: Mainland Mandarin Study Target Policy

**Status:** Proposed
**Date:** 2026-04-27

## Context

The project currently mixes a mainland-simplified study goal with source
materials that sometimes use traditional characters, especially Taiwanese song
lyrics. That creates avoidable confusion for learners who want one default
target for reading, typing, and speaking Mandarin.

An empirical audit for this decision found:

- 3018 single-character notes in `data/state/enriched.json`
- 3 traditional/simplified note pairs present in the deck
- 1 clearly duplicate-like pair for the learner target: `著` / `着`
- 9 of 21 lyric files containing `著` that should normalize to `着` for the
  mainland-simplified track
- 38 such lyric occurrences in total
- 5 user-facing doc examples recommending `著` instead of `着`

The current technical behavior also matters:

- `songs/lyrics.py` extracts raw CJK characters with no script normalization
- `songs/analysis.py` plans activation from those raw characters
- Taiwanese lyric lines such as `看著` and `贪恋著` therefore surface as `著`
  instead of the learner's mainland target `着`

## Decision

Adopt **mainland Mandarin with simplified characters** as the default active
study target for this repository.

### Policy

1. **Active study**
   - Default cards, activation examples, and planned song characters should use
     mainland simplified forms.
2. **Passive recognition**
   - Traditional forms remain useful as recognition context when they appear in
     lyrics, subtitles, or reference material.
3. **Song handling**
   - Keep curated lyric text in its original form when that preserves source
     fidelity.
   - Normalize planning and activation surfaces to simplified forms by default.
4. **Context-sensitive normalization**
   - Only normalize traditional forms when the lexical usage is actually the
     mainland simplified counterpart.
   - Example: aspect-particle `著` should map to `着`; lexical words such as
     `著名`, `显著`, and `著作` should remain `著`.

## Consequences

### Benefits

- Clearer learner target
- Fewer duplicate-like study items
- Better fit for a simplified-mainland learner consuming Taiwanese songs
- User-facing examples align with the intended study track

### Costs

- Song-planning code needs normalization logic instead of raw character matching
- Some existing deck variants need explicit policy rather than ad hoc treatment
- Contributors must be careful not to auto-merge unrelated traditional and
  simplified characters that share a pronunciation

## Rollout plan

1. **Docs first**
   - Update README and guides to define the default learning target.
   - Replace activation examples that currently recommend `著`.
2. **Song-planning normalization**
   - Preserve original lyric text.
   - Add a normalized simplified character set for `songs analyze`,
     `songs next`, and `songs activate`.
   - Add regression coverage for `著 -> 着` in song planning.
3. **Deck-note policy**
   - Resolve `著` / `着` first because it is the clearest learner-facing
     duplicate-like pair.
   - Review `藉` / `借` and `覆` / `复` separately instead of auto-merging them.

## Non-goals

- Converting the entire project to a traditional-character learning track
- Rewriting all curated lyrics into simplified text
- Treating every traditional/simplified pair as interchangeable

## References

- [Mainland Mandarin study target](../guides/mainland-mandarin.md)
- [Song activation guide](../guides/song-activation.md)

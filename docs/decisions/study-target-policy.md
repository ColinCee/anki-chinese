# Decision: study target policy

## Context

The project combines a mainland Mandarin study goal with source material that
can include traditional characters, especially Taiwanese song lyrics. Without a
clear policy, song planning can surface duplicate-like or off-target forms.

## Decision

The default active study target is:

- Mandarin
- mainland China usage
- simplified characters for active study
- traditional characters for passive recognition support

Curated lyric text can preserve source fidelity, but learner-facing planning
should target mainland simplified forms when appropriate.

## Current behavior

Song planning uses normalized study characters:

| Lyric form | Study form | Notes |
| --- | --- | --- |
| `看著` | `看着` | Aspect/state particle `zhe`. |
| `带著` | `带着` | Same pronunciation, simplified study form. |
| `著名` | `著名` | Lexical `zhù`; preserve. |
| `原著` | `原著` | Lexical `zhù`; preserve. |

Study normalization and planning remain deterministic; live planning queries
AnkiConnect, while lyric fetching is a separate network action.

## Consequences

- Fewer duplicate-like study targets.
- Traditional forms remain visible as recognition context.
- Contributors must not blindly merge unrelated traditional/simplified pairs.

## Applying the policy

Inspect `src/anki_chinese/songs/lyrics.py` and `tests/songs/test_lyrics.py`:
normalization currently uses neighboring-character rules, not a complete script
converter. The loader does not consume normalization sidecars. Do not relax the
policy to match implementation limitations.

For each candidate, read the line and context, then classify it as normalize,
preserve, or unresolved. Preserve lexical `著`, including `著名`, `著作`, `专著`,
and `原著`. Leave uncertain content unchanged and report its file/context and
reason. Never globally replace `著` or treat its blanket absence as correctness.

Encode changes in supported lyric content or implemented rules, with regression
cases covering both conversion and preservation; run `songs verify` for changed
lyrics. Runtime normalization/planning must not call LLMs, translation services,
OpenCC, or pypinyin guesses. Keep the work within the requested scope and use the
[maintenance loop](../../CONTRIBUTING.md#maintaining-docs-and-skills) for guidance friction.

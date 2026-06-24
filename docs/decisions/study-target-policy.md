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

Runtime song commands remain deterministic and credential-free except for local
AnkiConnect state.

## Consequences

- Fewer duplicate-like study targets.
- Traditional forms remain visible as recognition context.
- Contributors must not blindly merge unrelated traditional/simplified pairs.

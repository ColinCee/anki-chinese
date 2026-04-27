# Mainland Mandarin study target

This project's default learning track is:

- **Mandarin**
- **Mainland China usage**
- **Simplified characters for active study**
- **Traditional characters for passive recognition only**

That policy keeps the deck coherent for a learner who wants to read, type, and
speak standard mainland Mandarin without splitting attention across two writing
systems.

## What this means in practice

### Active study

Prioritize the mainland simplified form when you review cards, add manual
activations, or decide which character to learn next from a song.

Examples:

- `着`, not `著`
- `猫`, not `貓`
- `后`, not `後` when the intended mainland word uses the simplified form

### Passive recognition

Traditional forms still matter because they appear in:

- Taiwanese songs
- subtitles
- dictionaries
- older or imported text sources

You should recognize these forms when you see them, but they are secondary
unless you intentionally switch to a traditional-character learning track later.

## Taiwanese songs vs mainland study

A popular Taiwanese lyric may use the traditional form while keeping the same
meaning and pronunciation you want in mainland simplified Chinese.

Examples:

| Lyric text | Mainland study form | Pronunciation | Meaning |
| --- | --- | --- | --- |
| `看著` | `看着` | `kàn zhe` | looking; looking at |
| `带著` | `带着` | `dài zhe` | carrying; with |
| `贪恋著` | `贪恋着` | `tān liàn zhe` | being attached to |

In these cases, you are **not** supposed to sing them differently. The change is
script only.

## Important caveat: not every `著` becomes `着`

`著` is only normalized to `着` when it is the aspect/state particle used after
a verb.

Examples:

- `看著` -> `看着`
- `笑著` -> `笑着`

But lexical words such as these keep `著`:

- `著名`
- `显著`
- `著作`

Those are different words with different readings and should not be rewritten by
rule.

## Current repo state

Today, the docs and some curated lyric files still contain traditional-script
examples such as `著`, and the song-planning code does not yet normalize them
automatically. For now:

1. Treat traditional lyric forms as recognition aids.
2. Prefer the simplified mainland form when manually activating or reviewing.
3. Use the simplified character in examples such as `uv run anki-chinese activate chars ...`.

## Long-term direction

The long-term implementation goal is:

1. Keep curated lyrics in their original form when that is useful context.
2. Normalize song-planning and activation to mainland simplified forms by default.
3. Keep traditional variants visible as recognition context rather than primary
   study targets.

See [ADR-003](../decisions/ADR-003-study-target-policy.md) for the maintainers'
decision and rollout plan.

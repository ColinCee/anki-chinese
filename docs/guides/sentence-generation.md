# Sentence generation guide

The sentence pipeline uses Gemini Flash Lite to create short, common, day-to-day Mandarin example sentences for character flashcards.

## Setup

Create or edit `.env`:

```dotenv
GEMINI_API_KEY=your-gemini-key
```

The key is used by:

- `sentences`
- `keywords`
- `sentences repair-confusers --apply`

## Generate missing sentences

```bash
uv run anki-chinese sentences
```

Useful targeting options:

```bash
uv run anki-chinese sentences --char 早
uv run anki-chinese sentences --limit 20
uv run anki-chinese sentences --from-rsh 500
uv run anki-chinese sentences --force
```

`--force` regenerates even when a sentence already exists.

## Pick candidates interactively

```bash
uv run anki-chinese sentences --char 早 --pick 3
```

This generates candidates and lets you choose, skip, or regenerate. It requires an
interactive terminal; scripts and agents should run `sentences` without `--pick`.

## Repair contextual meanings

```bash
uv run anki-chinese keywords
```

This uses Gemini to repair the `Meaning` field for notes that already have sentences, keeping definitions focused on the character's core meaning plus compound context where needed.

## Audit phonetic confusers

Listening cards are confusing when the example sentence contains another character with the same or very similar sound as the target. Audit existing sentences with:

```bash
uv run anki-chinese sentences audit
```

To include broader same-final/rhyme matches:

```bash
uv run anki-chinese sentences audit --include-same-final
```

The top-level alias still exists:

```bash
uv run anki-chinese sentences-audit
```

## Repair phonetic confusers

Preview repairs first:

```bash
uv run anki-chinese sentences repair-confusers
```

Apply repairs:

```bash
uv run anki-chinese sentences repair-confusers --apply
```

Limit or target the repair:

```bash
uv run anki-chinese sentences repair-confusers --char 享 --apply
uv run anki-chinese sentences repair-confusers --limit 10 --attempts 5 --apply
```

Repair clears stale sentence audio so `audio` can regenerate the matching file.

## Sync after changes

Sentence and meaning commands update `data/state/enriched.json` and can make
audio/build output stale. Let `sync` decide the downstream work:

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

If you only want to inspect the current recommendation in a terminal, open the
dashboard:

```bash
uv run anki-chinese
```

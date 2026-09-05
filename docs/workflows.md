# Workflows

Use the workbench for human navigation:

```bash
uv run anki-chinese
```

It recommends the next action from local state. Agents and scripts use the
commands below directly; `--help` owns the full option list.

## Sync deck output

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

`sync` decides whether `init`, `audio`, and `build` are needed, executes needed
stages in dependency order, and replans after each stage. Use `--skip-audio`
when you intentionally want a no-network rebuild. A sync plan can include
unrelated stale work: inspect it before paid generation. If audio is skipped
or blocked, report it as pending, not refreshed.
Import the resulting `data/build/decks/chinese_rsh.apkg` into Anki separately;
rebuilding is not authorization to import or activate live cards.

## Fix one card

Inspect first:

```bash
uv run anki-chinese card show 编
uv run anki-chinese card show 编 --json
```

Write the canonical source record with `card set`:

```bash
uv run anki-chinese card set 编 \
  --meaning "to compile; arrange; make up; as in 编程: programming" \
  --sentence "我最近在学编程，想自己做个小程序。" \
  --sentence-pinyin "wǒ zuì jìn zài xué biān chéng, xiǎng zì jǐ zuò ge xiǎo chéng xù" \
  --sentence-english "I’ve been learning programming recently and want to make a small app myself."
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

`card set` writes authored fields into `data/source/characters.json`. Sentence
changes require `--sentence`, `--sentence-pinyin`, and `--sentence-english`
together; they clear the cached sentence-audio field in generated state so
`sync` can regenerate matching audio.

Keep meaning and character pronunciation consistent with the sentence's sense.
Use these commands rather than patching generated JSON or live-only notes.
Before re-initializing, preserve any [accepted generated text](#generate-sentences-and-meanings).
Finish by confirming `card show` and the rebuilt APKG, or report what is blocked.

## Add a character

New characters use the same two-card Anki projection but carry explicit
curriculum provenance. Custom characters do not receive synthetic RSH numbers:

```bash
uv run anki-chinese card add 账 \
  --meaning "account; bill/check; debt; in 结账: to pay the bill" \
  --sentence "我们吃完饭后去结账。" \
  --sentence-pinyin "wǒmen chī wán fàn hòu qù jiézhàng" \
  --sentence-english "After we finish eating, we'll pay the bill." \
  --collection restaurant-vocabulary
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

Meanings should be compact but sense-aware: list the important core senses and
explain the relevant compound or sentence usage instead of using only a broad
one-word gloss. `card add` defaults to a custom record and requires `--meaning`;
if an example sentence is supplied, all three sentence fields are required.

Use `--track rsh --rsh-number N` only for a real RSH entry. `card add` never
creates a live Anki note; import the rebuilt APKG separately, then use the
backup-gated activation workflow if the character should be unsuspended.

## Replace the source

Only do this to replace the canonical dataset, not as a routine rebuild step.
Export the intended source from Anki as a native `.apkg`. Back up any uncommitted
canonical edits before replacing them; this operation is not a merge.

```bash
uv run anki-chinese source import --input "data/source/All Decks.apkg" --replace --dry-run
uv run anki-chinese source import --input "data/source/All Decks.apkg" --replace
uv run anki-chinese sync
```

This changes local content, not live Anki scheduling. The export is not an
ongoing source of live review or suspension state.

## Review deck health

```bash
uv run anki-chinese doctor
uv run anki-chinese status
uv run anki-chinese review
uv run anki-chinese radicals
```

Use `doctor --check-anki` only when Anki is open and you want to include
AnkiConnect reachability.

## Compare character frequency coverage

Rebuild the local frequency snapshot only when you want to regenerate the
derived list:

```bash
uv run anki-chinese frequency refresh
```

Then report current live Anki progress without rebuilding the list:

```bash
uv run anki-chinese frequency report
uv run anki-chinese frequency report --json
```

Coverage means at least one live card has a recorded review, not merely that it
is unsuspended. The report ranks uncovered in-deck characters by frequency.
Its HSK-style band is a rough character-recognition comparison, not an overall
proficiency measure.

## Generate sentences and meanings

Generation and applied repairs require `GEMINI_API_KEY`; audits do not.

**Generated text currently lives only in enriched state.** Sentence generation,
meaning repair, and applied sentence repairs do not update the canonical records.
Before a canonical re-initialization, inspect accepted results with `card show`
and persist them with [card set](#fix-one-card), including the sentence triplet
and any changed character meaning/pinyin. Otherwise `init` (including a
source-triggered sync) can replace those generated edits.

Once any existing generated edits are preserved, sync the source before new
generation. Choose the generation or repair operation you need:

```bash
uv run anki-chinese sync --skip-audio
uv run anki-chinese sentences --limit 20
uv run anki-chinese sentences --char 早 --pick 3
uv run anki-chinese keywords
uv run anki-chinese sentences audit
uv run anki-chinese sentences repair-confusers
uv run anki-chinese sentences repair-confusers --apply
```

`--pick` is interactive and refuses non-terminal execution. Scripts and agents
should use non-interactive generation commands.

Persist accepted results as above, then run `sync` for matching audio and the APKG.

## Generate audio

The [provider strategy](decisions/tts-provider-strategy.md) uses Google for
characters and MiniMax for sentences. These credential smoke tests generate audio
and may incur provider charges:

```bash
uv run anki-chinese test-tts --char 早 --provider google
uv run anki-chinese test-tts --word 早上 --provider minimax
```

Then generate:

```bash
uv run anki-chinese audio --limit 20
uv run anki-chinese audio
uv run anki-chinese sync
```

Cleanup is preview-first:

```bash
uv run anki-chinese audio-clean
uv run anki-chinese audio-clean --apply
```

## Learn characters from songs

`songs verify` checks local lyric files without Anki. Song analysis and next-card
planning query live AnkiConnect state; keep Anki open. An active character has
at least one unsuspended card; a studied character has a recorded review.

```bash
uv run anki-chinese doctor --check-anki
uv run anki-chinese songs verify
uv run anki-chinese songs analyze
uv run anki-chinese songs next --limit 20
```

For normal human study, prefer `songs learn`:

```bash
uv run anki-chinese songs learn --limit 20
uv run anki-chinese songs learn --limit 20 --confirm
```

Without `--confirm`, live mutation commands preview only. Confirmed activation
and resuspension write targeted undo snapshots under `data/build/anki_backups/`.
Confirmed undo writes a `restore-*.json` safety snapshot before changing live
cards or tags. Inspect the preview first and retain the reported snapshot and
exact card/note counts. A dry-run is not a backup: take a full Anki backup before
broad, uncertain, or first-time automation. Re-query live state before planning
a follow-up batch; an old APKG or previous report is not current state.

Undo song activation:

```bash
uv run anki-chinese songs undo
uv run anki-chinese songs undo --confirm
```

Lower-level commands remain available:

```bash
uv run anki-chinese songs activate 学猫叫 --limit 20 --dry-run
uv run anki-chinese activate chars 内 合 哟 着 --dry-run
uv run anki-chinese activate snapshots list
uv run anki-chinese activate undo latest
```

## Customize card templates

Edit HTML/CSS in `src/anki_chinese/cards/`; `src/anki_chinese/deck.py` assembles
the templates and shared scripts. Keep both back templates identical.

```bash
uv run anki-chinese build
```

For template-only changes, use `build`, not just `sync`: the planner currently
tracks source/enriched/audio freshness, not template files. This packages existing
enriched content and audio without regenerating them. If enriched state is absent,
first follow [First rebuild](../README.md#first-rebuild). Import the new APKG separately.

For content changes use [card set](#fix-one-card) or [card add](#add-a-character).
Vocabulary examples belong in the canonical meaning/sentence fields;
`data/manual/example_words.json` is not consumed by the current enrichment flow.
Preserve [model identity](reference.md#anki-model) and the
[study target policy](decisions/study-target-policy.md).

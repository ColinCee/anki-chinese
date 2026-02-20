# CLI Reference

This project has 5 commands:

- `init`
- `audio`
- `build`
- `status`
- `review`

Run `uv run anki-chinese <command> --help` for all options.

## `init`

Parse the source export and enrich missing fields.

```bash
uv run anki-chinese init
```

Options:

- `-i, --input PATH`: use a different source file (default: `data/Exported-deck.txt`)
- `--skip-examples`: skip example-word lookup

Outputs:

- updates `data/enriched.json`

## `audio`

Generate Mandarin/Cantonese/example audio for notes in `data/enriched.json`.

```bash
uv run anki-chinese audio
```

Options:

- `-c, --char 字`: generate audio for one character
- `-l, --limit N`: process first `N` notes only
- `-f, --force`: regenerate files even if they already exist
- `--fail-fast`: stop on first error

Notes:

- Audio generation is intentionally serial to avoid free-tier throttling.
- Free-tier Azure TTS limits are low, so large runs can take a long time.

Outputs:

- writes MP3s under `media/generated/`
- updates audio tags in `data/enriched.json`

## `build`

Build Anki package from enriched data.

```bash
uv run anki-chinese build
```

Options:

- `--full`: run full pipeline (`init` → `audio` → `build`)
- `--skip-audio`: with `--full`, skip audio generation
- `--skip-examples`: with `--full`, skip example-word lookup
- `--audio-limit N`: with `--full`, limit audio to first `N` notes

Outputs:

- writes `output/chinese_rsh.apkg`

## `status`

Check coverage and validation quality.

```bash
uv run anki-chinese status
```

## `review`

Show notes flagged by enrichment as needing manual review.

```bash
uv run anki-chinese review
```

Use `data/overrides.json` to correct entries, then rerun `init`.

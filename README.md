# anki-chinese

Build a custom Anki deck for Mandarin study with Cantonese support.

This project parses an old deck export, enriches each character with language data,
optionally generates TTS audio, and produces a clean `.apkg` for Anki.

## Project goals

- Keep a **consistent character-first learning workflow** across the RSH book.
- Train **Mandarin reading + pronunciation** while keeping Cantonese as support.
- Make the deck **regenerable** without losing Anki review history.

## Quick start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Anki desktop

### Install

```bash
git clone <repo-url> && cd anki-chinese
uv sync
```

### Minimal run (no audio)

```bash
uv run anki-chinese init
uv run anki-chinese build
```

Output: `output/chinese_rsh.apkg`

## Command order (what is required)

### Typical order

1. `init` (required)
2. `status` (recommended)
3. `audio` (optional)
4. `build` (required)

### Important notes

- `build` needs `data/enriched.json`, so run `init` first (unless already done).
- `audio` is optional; you can build and study without it.
- `audio` can be slow on free-tier Azure due to low per-minute limits.
- Example words are auto-generated when missing; manual overrides still come from `data/example_words.json`.

## Most common commands

```bash
# Parse + enrich source deck
uv run anki-chinese init

# Check data quality
uv run anki-chinese status

# Generate pronunciation audio (optional)
uv run anki-chinese audio

# Build final Anki package
uv run anki-chinese build
```

## Azure TTS setup (optional)

1. Create Azure Speech resource.
2. Copy `.env.example` to `.env`.
3. Set:

```dotenv
AZURE_SPEECH_KEY=your-key
AZURE_SPEECH_REGION=eastus
```

## Docs

- CLI details and all flags: [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)
- Customization (templates, overrides, voices): [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md)
- Project intent and roadmap notes: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

## Re-import behavior

Stable GUIDs are based on each character, so re-importing updates existing notes
instead of creating duplicates.

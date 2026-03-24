# anki-chinese

Build a custom Anki deck for Mandarin study with Cantonese support.

This project parses a deck export, enriches each character with language data,
optionally generates TTS audio, and produces a clean `.apkg` for Anki.

## Project goals

- Keep a **consistent character-first learning workflow** across the RSH book.
- Train **Mandarin reading + pronunciation** while keeping Cantonese as support.
- Reinforce each character with a **common usage phrase** on listening cards.
- Store explicit **example-word pinyin** so example audio is forced to the intended reading.
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

For development checks:

```bash
uv sync --group dev
uv run pyright
uv run pytest
uv run python _smoke_test.py
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
- Default source input is `data/All Decks.txt`.

## Most common commands

```bash
# Parse + enrich source deck (default: data/All Decks.txt)
uv run anki-chinese init

# Check data quality
uv run anki-chinese status

# Generate pronunciation audio (optional)
uv run anki-chinese audio

# Build final Anki package
uv run anki-chinese build
```

## Current code layout

The repo is now organized around a few concrete feature areas instead of one very large CLI file:

- `src/anki_chinese/cli/` — the Typer app, one file per command, plus shared Rich UI helpers
- `src/anki_chinese/notes/` — note model, parsing, enrichment, persistence, and reporting helpers
- `src/anki_chinese/audio/` — audio tags/files, Azure provider code, retry policy, and provider interface
- `src/anki_chinese/data_sources/` — pinyin/jyutping/example-word lookup data and cached lookup service
- `src/anki_chinese/deck.py` — Anki package creation

The older `models.py` and `pipeline/` modules still exist as compatibility wrappers, but the main implementation now lives in the feature modules above.

## Validation

Current validation commands:

```bash
uv run pyright
uv run pytest
uv run python _smoke_test.py
uv run anki-chinese --help
```

## Azure TTS setup (optional)

1. Create Azure Speech resource.
2. Copy `.env.example` to `.env`.
3. Set:

```dotenv
AZURE_SPEECH_KEY=your-key
AZURE_SPEECH_REGION=eastus
```

## TTS roadmap

Azure is still the current provider, but it now sits behind a provider boundary in `src/anki_chinese/audio/provider.py` and `src/anki_chinese/audio/azure.py`. That makes a future swap much smaller than before.

Current shortlist for a future pivot:

- **Amazon Polly** — strongest near-term candidate for this project because it supports Mandarin and Cantonese and has mature SSML + lexicon support
- **Google Cloud Text-to-Speech** — strong Mandarin/API maturity option; Cantonese fit still needs direct sample testing for this workflow
- **ElevenLabs** — worth evaluating for naturalness, but should be proven on exact-pronunciation Mandarin/Cantonese cases before trusting it for study audio

The next provider decision should be based on side-by-side samples from this repo's real characters and example words, not just marketing claims.

## Docs

- CLI details and all flags: [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)
- Customization (templates, overrides, voices): [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md)
- Learning intent and method rationale: [docs/LEARNING_APPROACH.md](docs/LEARNING_APPROACH.md)

## Re-import behavior

Stable GUIDs are based on each character, so re-importing updates existing notes
instead of creating duplicates.

## Current listening-card behavior

- `recall_front` is listening-first: Mandarin audio + optional example phrase.
- Keyword is intentionally removed from the listening front.
- Example phrase is shown when `ExampleWord` exists (manual entries win; otherwise auto-picked common usage).

# anki-chinese

Build a regenerable Anki deck for Mandarin study with Cantonese support.

This repo parses a deck export, enriches each character with readings and example words, optionally generates TTS audio, and builds a clean `.apkg` for Anki.

## Project goals

- Keep a **consistent character-first learning workflow** across the RSH book.
- Train **Mandarin reading + pronunciation** while keeping Cantonese as support.
- Reinforce each character with a **common usage phrase** on listening cards.
- Store explicit **example-word pinyin** so example audio is forced to the intended reading.
- Make the deck **regenerable** without losing Anki review history.

## Supported entrypoints

Use the CLI as the supported interface:

- `uv run anki-chinese ...` for normal use
- `uv run python -m anki_chinese.cli --help` for module execution and debugging

There are no separate top-level helper scripts to learn or maintain.

## Migration note

This cleanup intentionally removed undocumented compatibility surfaces:

- `anki_chinese.models`
- `anki_chinese.pipeline.*`
- old top-level helper scripts like `main.py` and `generate_test_audio.py`

If you still have local automation importing those paths, migrate to the real modules instead:

- `anki_chinese.notes` for note models, parsing, storage, and reporting
- `anki_chinese.notes.enrich` for `enrich_notes`
- `anki_chinese.audio` for TTS helpers and provider code
- `anki_chinese.deck` for deck creation
- `anki-chinese` for the supported command-line workflow

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

## Core workflow

Run the commands in this order:

1. `init` — parse the source export and enrich missing fields
2. `status` — inspect coverage and validation
3. `review` — inspect notes flagged for manual correction
4. `audio` — optionally generate Mandarin/Cantonese/example audio
5. `build` — create the final `output/chinese_rsh.apkg`

Important notes:

- `build` needs `data/enriched.json`, so `init` comes first.
- `audio` is optional; you can build and study without it.
- `audio` can be slow on free-tier Azure because of low rate limits.
- Example words are auto-generated when missing; manual overrides still come from `data/example_words.json`.
- Default source input is `data/All Decks.txt`.

### Common commands

```bash
# Parse + enrich the default source deck
uv run anki-chinese init

# Check what still needs attention
uv run anki-chinese status
uv run anki-chinese review

# Generate pronunciation audio
uv run anki-chinese audio

# Build the final Anki package
uv run anki-chinese build

# Generate one-off sample audio without touching the main workflow
uv run anki-chinese test-tts --char 早
uv run anki-chinese test-tts --word 早上
```

Use `uv run anki-chinese <command> --help` for full flags and options.

## Validation

Development checks:

```bash
uv sync --group dev
uv run pyright
uv run pytest
uv run anki-chinese --help
uv run python -m anki_chinese.cli --help
```

## Testing strategy

Keep tests in top-level `tests/` and mirror the feature layout there:

- `tests/notes/`, `tests/audio/`, `tests/cli/`, `tests/data_sources/`, and `tests/deck/` for focused feature tests
- `tests/regressions/` for real bug regressions
- `tests/integration/` for a very small number of high-level workflow and CLI orchestration checks, usually with stubbed external dependencies

Test philosophy:

- favor regression value over test count
- keep fixtures light and explicit
- test public behavior and risky seams first
- every real bug should earn a regression test

## Repo layout

The main code lives under `src/anki_chinese/`:

- `cli/` — Typer commands and shared Rich UI helpers
- `notes/` — note model, parsing, enrichment, persistence, and reporting
- `audio/` — provider code, retry policy, and audio file/tag helpers
- `data_sources/` — pinyin, jyutping, and example-word lookup data
- `deck.py` — Anki package creation
- `config.py` — paths, deck metadata, and voice defaults

The rest of the repo is kept intentionally simple:

- `tests/` — automated tests, mirrored by feature plus small `regressions/` and `integration/` areas
- `templates/` — card HTML/CSS templates
- `data/` — inputs plus derived data
  - `All Decks.txt`, `example_words.json`, and `overrides.json` are hand-maintained
  - `enriched.json` and `hsk_complete.min.json` are derived/cache artifacts
- `media/`, `output/`, and `dist/` — generated runtime/build outputs
- `docs/CUSTOMIZATION.md` — non-default tweaking only

## Learning flow

The deck stays opinionated:

- `recall_front` is listening-first: Mandarin audio + optional example phrase.
- Keyword text is intentionally removed from the listening front.
- Example selection follows a simple rule: manual example first, then automatic HSK/CEDICT fallback, then blank.
- Pronunciation decisions come from `Pinyin` and `Jyutping`, not from the English keyword.

## Re-import behavior

Stable GUIDs are based on each character, so re-importing updates existing notes instead of creating duplicates.

## Azure TTS setup (optional)

1. Create an Azure Speech resource.
2. Copy `.env.example` to `.env`.
3. Set:

```dotenv
AZURE_SPEECH_KEY=your-key
AZURE_SPEECH_REGION=eastus
```

## TTS roadmap

Azure is still the current provider, but it now sits behind `src/anki_chinese/audio/provider.py` and `src/anki_chinese/audio/azure.py`. That keeps a future provider switch much smaller than before.

Current shortlist for a future pivot:

- **Amazon Polly** — strongest near-term candidate for Mandarin + Cantonese with explicit pronunciation control
- **Google Cloud Text-to-Speech** — strong Mandarin/API maturity option; Cantonese fit still needs direct sample testing
- **ElevenLabs** — promising for naturalness, but still needs proof on exact-pronunciation Mandarin/Cantonese study audio

The next provider decision should be based on side-by-side samples from this repo's real characters and example words, not vendor marketing.

## Docs

- Non-default customization: [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md)

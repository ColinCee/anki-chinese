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

Output: `data/build/decks/chinese_rsh.apkg`

## Core workflow

Run the commands in this order:

1. `init` — parse the source export and enrich missing fields
2. `status` — inspect coverage and validation
3. `review` — inspect notes flagged for manual correction
4. `audio` — optionally generate Mandarin/Cantonese/example audio
5. `build` — create the final `data/build/decks/chinese_rsh.apkg`

Important notes:

- `build` needs `data/state/enriched.json`, so `init` comes first.
- `audio` is optional; you can build and study without it.
- `audio` is network-bound and can still take a while on larger batches.
- Example words are auto-generated when missing; manual overrides still come from `data/manual/example_words.json`.
- Default source input is `data/source/All Decks.txt`.

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

- At the root, the meaningful product folders are just `src/`, `tests/`, `data/`, and `docs/`.
- `tests/` — automated tests, mirrored by feature plus small `regressions/` and `integration/` areas
- `data/` — split by purpose
  - `source/` — deck imports such as `All Decks.txt`
  - `manual/` — hand-maintained overrides and example-word data
  - `reference/` — canonical lookup corpora kept for deterministic offline use; optional local extras like `SUBTLEX_CH.xlsx` also live here
  - `state/` — workflow state such as `enriched.json`
  - `build/` — generated audio, sample audio, and built decks
- `src/anki_chinese/cards/` — packaged card HTML/CSS files
- `dist/` — Python packaging output, ignored in normal workflow
- `docs/CUSTOMIZATION.md` — non-default tweaking only

## Learning flow

The deck stays opinionated:

- `recall_front` is listening-first: Mandarin audio + optional example phrase.
- Keyword text is intentionally removed from the listening front.
- Example selection follows a simple rule: manual example first, then automatic HSK/CEDICT fallback, then blank.
- Pronunciation decisions come from `Pinyin` and `Jyutping`, not from the English keyword.

## Re-import behavior

Stable GUIDs are based on each character, so re-importing updates existing notes instead of creating duplicates.

## MiniMax TTS setup (optional)

1. Create a MiniMax API key in the console.
2. Copy `.env.example` to `.env`.
3. Set:

```dotenv
MINIMAX_API_KEY=your-key
```

The repo default model and voice IDs live in `src/anki_chinese/audio/minimax.py`, not in `.env`.

Only add env overrides when you intentionally need them:

- `MINIMAX_API_HOST=https://api.minimaxi.com` for mainland-region keys
- `MINIMAX_TTS_MODEL=...` if you want a different MiniMax speech model
- `MINIMAX_MANDARIN_VOICE_ID=...` or `MINIMAX_CANTONESE_VOICE_ID=...` if you want different voices

You can then smoke-test audio generation with:

```bash
uv run anki-chinese test-tts --char 一
```

## TTS provider

The repo now ships one runtime TTS implementation: MiniMax `speech-2.8-turbo`, wired behind the narrow `src/anki_chinese/audio/provider.py` boundary.

- `audio` and `test-tts` now use provider-neutral CLI wording.
- `test-tts` uses the configured provider defaults instead of reaching into provider internals.
- The public CLI/runtime path is provider-agnostic, but intentionally narrow: it covers the exact Mandarin, Cantonese, example, preview, and file-tag operations this repo needs.
- Secrets stay in `.env`; stable repo defaults stay in code.

For the migration rationale, workload math, and account setup notes, see [docs/TTS_RESEARCH.md](docs/TTS_RESEARCH.md).

## Docs

- Non-default customization: [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md)

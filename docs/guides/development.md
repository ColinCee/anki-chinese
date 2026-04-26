# Development guide

Everything you need to work on **anki-chinese**: setup, layout, testing, and migration notes.

## Quick setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

### Install

```bash
git clone <repo-url> && cd anki-chinese
uv sync --group dev
```

### Validate

Run these four checks before pushing any change:

```bash
uv run pyright          # type checking
uv run pytest           # test suite
uv run anki-chinese --help                # CLI entrypoint (package)
uv run python -m anki_chinese.cli --help  # CLI entrypoint (module)
```

Both entrypoint checks must print help text without error.

## Repo layout

### Source code — `src/anki_chinese/`

| Path | Purpose |
|------|---------|
| `cli/` | Typer commands and shared Rich UI helpers |
| `notes/` | Note model, parsing, enrichment, persistence, and reporting |
| `audio/` | Provider code, retry policy, and audio file/tag helpers |
| `data_sources/` | Pinyin, jyutping, and example-word lookup data |
| `deck.py` | Anki package creation |
| `config.py` | Paths, deck metadata, and voice defaults |
| `cards/` | Packaged card HTML/CSS files |

### Top-level directories

| Path | Purpose |
|------|---------|
| `src/` | All production code |
| `tests/` | Automated tests, mirrored by feature (see [Testing](#testing)) |
| `data/` | Runtime data, split by purpose (see below) |
| `docs/` | Guides and reference documentation |
| `dist/` | Python packaging output; ignored in normal workflow |

### `data/` subdirectories

| Path | Purpose |
|------|---------|
| `source/` | Deck imports such as `All Decks.apkg` (native Anki package export) |
| `manual/` | Hand-maintained overrides and example-word data |
| `reference/` | Canonical lookup corpora for deterministic offline use; optional local extras like `SUBTLEX_CH.xlsx` also live here |
| `songs/` | Curated song lyric markdown files used by `anki-chinese songs` analysis and activation commands |
| `state/` | Workflow state such as `enriched.json` |
| `build/` | Generated audio, sample audio, and built decks |

## Testing

### Directory structure

Tests live in top-level `tests/` and mirror the feature layout:

- `tests/notes/`, `tests/audio/`, `tests/cli/`, `tests/data_sources/`, `tests/deck/` — focused feature tests
- `tests/regressions/` — real bug regressions
- `tests/integration/` — a small number of high-level workflow and CLI orchestration checks, usually with stubbed external dependencies

### Philosophy

- Favor regression value over test count.
- Keep fixtures light and explicit.
- Test public behavior and risky seams first.
- Every real bug should earn a regression test.

## Migration notes

This cleanup intentionally removed undocumented compatibility surfaces:

- `anki_chinese.models`
- `anki_chinese.pipeline.*`
- Old top-level helper scripts like `main.py` and `generate_test_audio.py`

If you still have local automation importing those paths, migrate to the real modules:

| Removed path | Replacement |
|--------------|-------------|
| `anki_chinese.models` | `anki_chinese.notes` — note models, parsing, storage, and reporting |
| `anki_chinese.pipeline.*` | `anki_chinese.notes.enrich` for `enrich_notes`; `anki_chinese.audio` for TTS; `anki_chinese.deck` for deck creation |
| `main.py` / `generate_test_audio.py` | `anki-chinese` CLI (see `uv run anki-chinese --help`) |

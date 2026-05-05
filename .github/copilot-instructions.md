# Copilot Instructions for anki-chinese

## Project overview

A Python CLI tool that builds regenerable Anki flashcard decks for Mandarin study with Cantonese support, following the Heisig RSH (Remembering Simplified Hanzi) character order. Parses an Anki `.apkg` export, enriches each character with readings, example words, and sentences, optionally generates TTS audio, and outputs a clean `.apkg`.

## Architecture

```
src/anki_chinese/
├── cli/          # Typer commands + Rich UI helpers
├── notes/        # CharacterNote model, .apkg parsing, enrichment, persistence, reporting
├── activation/   # Live Anki activation via AnkiConnect (unsuspend/tag existing cards)
├── songs/        # Lyric parsing, song analysis, and song-to-character planning
├── audio/        # TTSProvider protocol, Google/MiniMax implementations, retry, rate limiting
├── sentences/    # Gemini Flash Lite sentence generation + self-validation pipeline
├── data_sources/ # Pinyin, jyutping, CEDICT, HSK lookups
├── cards/        # HTML/CSS card templates
├── config.py     # Paths, deck metadata, field order, voice defaults
├── deck.py       # genanki .apkg creation
└── pipeline/     # Pipeline orchestration
```

### Key patterns

- **Provider-neutral boundaries**: `audio/provider.py` defines a `TTSProvider` Protocol. Concrete implementations (Google, MiniMax) are deep and contained.
- **Factory pattern**: `audio/factory.py` builds providers by name. Default is Google.
- **Narrow CLI surface**: All user interaction goes through `uv run anki-chinese <command>`.
- **Stable GUIDs**: genanki IDs are based on character identity — re-importing updates notes, never duplicates.
- **Two-lane Anki workflow**: `.apkg` import/export is for rebuildable content (fields, audio, sentences, templates). Live activation is separate and uses AnkiConnect to unsuspend/tag existing cards in the open Anki collection.
- **Activation is general infrastructure**: `activate` commands are not song-specific. Songs are one planner/source that produces character batches and then calls the shared activation layer.

## Data flow

```
data/source/All Decks.apkg  →  init (parse + enrich)  →  data/state/enriched.json
                                                              ↓
                                                     audio (optional TTS)
                                                              ↓
                                                     build  →  data/build/decks/chinese_rsh.apkg
```

Live activation flow:

```
manual chars / song planner / future recommender  →  activation service  →  AnkiConnect  →  live Anki cards
```

## TTS strategy

- **Google Cloud TTS WaveNet**: Single characters — SSML `<phoneme>` tags force exact pinyin/jyutping pronunciation.
- **MiniMax speech-2.8-turbo**: Sentences and example words — context disambiguates polyphonic characters, natural prosody.
- Provider choice is via `--provider` flag or factory default in `audio/factory.py`.

## Sentence generation

Uses Gemini Flash Lite with a lean 7-rule prompt + same-model self-validation (7-point grammar checklist). Documented in `docs/decisions/ADR-001-sentence-generation.md`.

## Key data files

| Path | Purpose |
|------|---------|
| `data/source/All Decks.apkg` | Native Anki package export (input) |
| `data/manual/overrides.json` | Per-character field overrides |
| `data/manual/example_words.json` | Manual example word definitions |
| `data/reference/hsk_complete.min.json` | HSK vocabulary corpus for auto-picking examples |
| `data/songs/lyrics/` | Curated lyric markdown files for song-based planning |
| `data/state/enriched.json` | Enriched notes (workflow state) |
| `data/build/decks/chinese_rsh.apkg` | Final output deck |

## Commands

```bash
uv run anki-chinese init        # Parse source deck + enrich
uv run anki-chinese status      # Coverage and validation report
uv run anki-chinese review      # Inspect notes flagged for correction
uv run anki-chinese audio       # Generate TTS audio
uv run anki-chinese sentences   # Generate example sentences (Gemini)
uv run anki-chinese build       # Create final .apkg
uv run anki-chinese activate    # Unsuspend/tag existing live Anki cards
uv run anki-chinese songs       # Analyze lyrics and plan song character batches
uv run anki-chinese test-tts    # Smoke-test audio generation
```

### Song subcommands

```bash
uv run anki-chinese songs analyze          # Greedy sequence + stats
uv run anki-chinese songs fetch "天后"     # Fetch lyrics from lyrics.net.cn
uv run anki-chinese songs verify           # Validate all lyric files
uv run anki-chinese songs next 学猫叫     # Preview next chars for a song
uv run anki-chinese songs activate 学猫叫 # Unsuspend cards for a song
```

Activation uses AnkiConnect at `http://127.0.0.1:8765` by default. If Anki runs on Windows and the CLI runs in WSL, prefer WSL mirrored networking so localhost reaches Windows Anki while AnkiConnect remains bound to 127.0.0.1.

## Development

```bash
uv sync --group dev     # Install dev dependencies
uv run pyright          # Type checking (standard mode, Python 3.13)
uv run pytest           # Tests
uv run ruff check       # Linting (E, F, I, UP, B, SIM rules)
```

### Conventions

- Python 3.13+, managed with `uv`
- Type annotations everywhere; `pyright` in standard mode
- `ruff` for linting and formatting (line length 100)
- Tests mirror feature layout: `tests/notes/`, `tests/audio/`, `tests/cli/`, etc.
- `tests/regressions/` for real bug regressions; `tests/integration/` for workflow checks
- Favor regression value over test count; test public behavior and risky seams first
- The `meaning` field contains rich definitions: core CEDICT meaning + compound context (e.g., "silver; in 银行: bank")
- `__all__: list[str] = []` marks internal modules — import from the package instead

## Documentation

Docs live in `docs/` organized by purpose:

- `docs/decisions/` — Architecture Decision Records (ADRs)
- `docs/guides/` — How-to guides (customization, development, TTS setup)
- `docs/research/` — Exploratory research and provider comparisons

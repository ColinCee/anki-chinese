# Copilot Instructions for anki-chinese

## Project overview

`anki-chinese` is a Python CLI that rebuilds an Anki deck for Mandarin study with Cantonese support. It parses an Anki `.apkg` export, enriches character notes, optionally generates Gemini sentences and TTS audio, and builds a regenerated `.apkg`. Live suspended-state changes are handled separately through AnkiConnect.

For current user-facing setup and command docs, prefer:

- `docs/start.md`
- `docs/workflows.md`
- `docs/reference.md`
- `docs/architecture.md`

## Architecture map

```text
src/anki_chinese/
├── cli/          # Typer commands + Rich UI helpers
├── tui/          # Textual dashboard and recommendation/guidance model
├── workflows/    # Shared sync planning, pipeline fingerprints, workflow state
├── notes/        # CharacterNote model, .apkg parsing, enrichment, persistence, reporting
├── activation/   # Live Anki activation via AnkiConnect
├── songs/        # Lyric parsing, study normalization, song analysis, activation planning
├── audio/        # TTSProvider protocol, Google/MiniMax providers, retry, rate limiting
├── sentences/    # Gemini sentence generation + contextual meaning repair
├── data_sources/ # Pinyin, jyutping, CEDICT, HSK, optional SUBTLEX lookups
├── cards/        # HTML/CSS card templates
├── config.py     # Paths, deck metadata, stable IDs, field order
└── deck.py       # genanki .apkg creation
```

## Core patterns

- Keep the CLI surface narrow: user workflows go through `uv run anki-chinese ...`.
- Human workflow navigation starts with the Textual dashboard; agents/scripts should use deterministic CLI commands.
- Preserve stable Anki identity: do not change `MODEL_ID`, `DECK_ID`, field order, or GUID behavior without an explicit migration.
- Keep rebuild and live activation separate:
  - `.apkg` import/export is for rebuildable content.
  - AnkiConnect is for live suspended state and tags.
- Keep provider-specific code behind `audio/provider.py` and `audio/factory.py`.
- Keep AnkiConnect details behind `activation/`.
- Treat generated files under `data/build/` and `data/state/enriched.json` as generated artifacts.

## Current workflows

```bash
uv sync --group dev
uv run ruff check
uv run pyright
uv run pytest
uv run anki-chinese --help
uv run python -m anki_chinese.cli --help
```

Core CLI families:

- `init`, `status`, `review`, `build`
- `dashboard`, `doctor`, `sync`
- `card`
- `sentences`, `keywords`
- `audio`, `audio-clean`, `test-tts`
- `songs`
- `activate`

Use `uv run anki-chinese <command> --help` as the authoritative command reference.

Dashboard behavior:

- `uv run anki-chinese` opens the dashboard only in an interactive terminal.
- The dashboard recommends one workflow from local state but does not replace scriptable commands.
- Keep dashboard logic presentational; reuse workflow/domain functions instead of duplicating sync, audio, song, or activation logic.
- `doctor` is read-only; `--check-anki` performs an AnkiConnect version probe only.

## TTS and AI setup

- Google Cloud Text-to-Speech uses ADC/service-account auth. Use `GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default login`; do not document an API-key setup path for Google TTS.
- MiniMax uses `MINIMAX_API_KEY` and optional region/model/voice overrides.
- Gemini sentence and keyword commands use `GEMINI_API_KEY`.
- AnkiConnect can use `ANKICONNECT_API_KEY` only if the local add-on requires it.

## Study target and songs

The default learner target is mainland Mandarin with simplified characters for active study and traditional characters as recognition support. Song planning uses normalized study characters: particle `著` can map to `着`, while lexical `著` words such as `著名` and `原著` remain valid.

Do not add LLM calls, network translation, OpenCC passes, or pypinyin guessing to runtime song planning. Keep `songs analyze`, `songs next`, `songs learn`, and `songs activate` deterministic apart from local AnkiConnect state.

## Documentation

Docs are organized by purpose:

- `docs/start.md` — first setup and first rebuild
- `docs/workflows.md` — common task workflows
- `docs/reference.md` — stable command/config/data/model facts
- `docs/architecture.md` — system overview
- `docs/decisions/` — durable decisions and tradeoffs

Update docs when setup, CLI behavior, environment variables, or data layout changes.

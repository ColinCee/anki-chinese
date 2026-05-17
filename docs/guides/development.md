# Development guide

Everything needed to work on **anki-chinese** locally.

## Setup

```bash
git clone https://github.com/ColinCee/anki-chinese.git
cd anki-chinese
uv sync --group dev
```

## Validation

Run these before opening a PR:

```bash
uv run ruff check
uv run pyright
uv run pytest
uv run anki-chinese --help
uv run python -m anki_chinese.cli --help
```

`pyright`, `pytest`, and CLI entrypoint checks run in CI. `ruff` is the project linter and should stay clean for local changes.

## Source layout

| Path | Purpose |
| --- | --- |
| `src/anki_chinese/cli/` | Typer commands and Rich UI helpers. |
| `src/anki_chinese/notes/` | Character note model, `.apkg` parsing, enrichment, storage, reporting. |
| `src/anki_chinese/deck.py` | `genanki` package creation. |
| `src/anki_chinese/cards/` | Packaged Anki card templates and CSS. |
| `src/anki_chinese/audio/` | TTS provider protocol, Google/MiniMax implementations, retry/rate limiting. |
| `src/anki_chinese/sentences/` | Gemini sentence generation and contextual meaning repair. |
| `src/anki_chinese/songs/` | Lyric parsing, study normalization, analysis, activation planning. |
| `src/anki_chinese/activation/` | AnkiConnect client and live activation service. |
| `src/anki_chinese/data_sources/` | CEDICT, HSK, pinyin, jyutping, SUBTLEX helpers. |
| `src/anki_chinese/config.py` | Paths, deck metadata, stable IDs, field order. |

## Data layout

See [data layout](../reference/data-layout.md) for the full reference. Generated state and build outputs should not be edited by hand.

## Testing conventions

Tests live in top-level `tests/` and mirror feature areas:

- `tests/notes/`
- `tests/audio/`
- `tests/cli/`
- `tests/songs/`
- `tests/sentences/`
- `tests/activation/`
- `tests/integration/`
- `tests/regressions/`

Prefer high-signal tests that cover public behavior, risky seams, and real regressions.

## Code conventions

- Python 3.13+
- Type annotations for production code
- `pyright` in standard mode
- `ruff` for linting/import ordering
- Internal modules can mark `__all__: list[str] = []`; import through package boundaries when possible
- Keep provider-specific behavior behind narrow boundaries such as `TTSProvider`
- Keep AnkiConnect behavior inside `activation/` and CLI orchestration, not scattered ad hoc scripts

## Documentation conventions

- Update public docs when CLI behavior, setup, environment variables, or data layout changes.
- Keep README concise and link to canonical docs for details.
- Keep ADRs focused on decisions and historical context; use guides/reference for current setup.
- Label research as point-in-time when it includes pricing or provider capabilities.

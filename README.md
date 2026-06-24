# anki-chinese

Build a regenerable Anki deck for Mandarin study with Cantonese support, AI-generated example sentences, controlled pronunciation audio, and song-driven card activation.

The project is optimized for a mainland Mandarin learner using simplified characters while still keeping Cantonese readings and traditional-script song exposure useful as support.

## Why this exists

Anki is excellent at scheduling reviews, but maintaining a high-quality Chinese deck by hand is slow. `anki-chinese` keeps Anki as the review engine and automates the rebuildable parts:

- parse an existing Anki `.apkg` export
- enrich each character with Mandarin pinyin, Cantonese jyutping, meanings, and metadata
- generate short, common Mandarin example sentences with Gemini
- generate single-character and sentence audio with provider-specific TTS
- rebuild a clean `.apkg` with stable IDs so imports update notes instead of duplicating them
- use AnkiConnect to unsuspend/tag specific live cards, manually or from song lyric plans

## Quick start

```bash
git clone https://github.com/ColinCee/anki-chinese.git
cd anki-chinese
uv sync
uv run anki-chinese doctor
uv run anki-chinese
```

The dashboard is the human entrypoint: it inspects local state, recommends the
next workflow, and shows the equivalent CLI commands. `doctor` is read-only and
checks local readiness.

Prerequisites and setup details are in [Start](docs/start.md).

## Core workflow

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

`sync` is the state-aware rebuild planner. It decides whether parsing,
enrichment, audio, and deck building are needed, then writes the generated deck
to `data/build/decks/chinese_rsh.apkg`.

Use `card set` for one-card fixes, `sentences`/`keywords` for Gemini-backed
content generation, `audio` for TTS, and `songs learn` for preview-first
song-driven activation. See [Workflows](docs/workflows.md) for examples.

## Safety notes

- Do not change `MODEL_ID` or `DECK_ID` after first import; Anki will treat the next import as a different model/deck.
- `.apkg` rebuilds update note content. They are not the source of truth for live suspended state after AnkiConnect changes.
- `activate`, `songs learn`, `songs activate`, `songs resuspend`, and undo commands mutate the open Anki collection only with `--confirm`. Preview first; confirmed live mutations write safety snapshots under `data/build/anki_backups/`.
- Keep `.env`, API keys, Google service-account files, generated audio, and generated deck outputs out of commits.

## Documentation

Start with:

- [Start](docs/start.md)
- [Workflows](docs/workflows.md)
- [Reference](docs/reference.md)
- [Architecture](docs/architecture.md)
- [Decisions](docs/decisions/)

## Development

```bash
uv sync --group dev
uv run pyright
uv run pytest
uv run ruff check
uv run anki-chinese --help
uv run python -m anki_chinese.cli --help
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor setup and PR expectations.

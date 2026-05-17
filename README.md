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
- use AnkiConnect to unsuspend/tag existing live cards from song lyric plans

## Quick start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Anki desktop
- A source Anki export at `data/source/All Decks.apkg`

### Install

```bash
git clone https://github.com/ColinCee/anki-chinese.git
cd anki-chinese
uv sync
```

### Build without optional network features

```bash
uv run anki-chinese init
uv run anki-chinese status
uv run anki-chinese build
```

Import the generated package into Anki:

```text
data/build/decks/chinese_rsh.apkg
```

See [Getting started](docs/getting-started.md) for export/import details and optional credentials.

## Main workflows

### Rebuild deck content

```bash
uv run anki-chinese init
uv run anki-chinese sentences       # optional, requires GEMINI_API_KEY
uv run anki-chinese audio           # optional, requires TTS credentials
uv run anki-chinese build
```

For one-command rebuilds:

```bash
uv run anki-chinese build --full --skip-audio
uv run anki-chinese build --full --audio-limit 50
```

### Generate and audit sentences

```bash
uv run anki-chinese sentences --limit 20
uv run anki-chinese sentences --char 早 --pick 3
uv run anki-chinese keywords
uv run anki-chinese sentences audit
uv run anki-chinese sentences repair-confusers --apply
```

### Generate audio

```bash
uv run anki-chinese test-tts --char 早 --provider google
uv run anki-chinese test-tts --word 早上 --provider minimax
uv run anki-chinese audio --limit 20
uv run anki-chinese audio-clean
```

Current provider split:

- **Google Cloud Text-to-Speech** for single-character Mandarin/Cantonese audio
- **MiniMax** for sentence audio

### Activate cards from songs

Live activation uses AnkiConnect while Anki is open. Always dry-run first.

```bash
uv run anki-chinese songs analyze
uv run anki-chinese songs next --limit 20
uv run anki-chinese songs activate --limit 20 --dry-run
uv run anki-chinese songs activate --limit 20
```

Lyrics live in `data/songs/lyrics/` and can be fetched from lyrics.net.cn:

```bash
uv run anki-chinese songs fetch "天后"
uv run anki-chinese songs verify
uv run anki-chinese songs verify --online
```

## Safety notes

- Do not change `MODEL_ID` or `DECK_ID` after first import; Anki will treat the next import as a different model/deck.
- `.apkg` rebuilds update note content. They are not the source of truth for live suspended state after AnkiConnect changes.
- `activate` and `songs activate` mutate the open Anki collection. Use `--dry-run` first and keep an Anki backup or targeted undo path.
- Keep `.env`, API keys, Google service-account files, generated audio, and generated deck outputs out of commits.

## Documentation

Start with [docs/](docs/README.md):

- [Getting started](docs/getting-started.md)
- [Architecture overview](docs/architecture/overview.md)
- [Deck rebuild workflow](docs/guides/deck-rebuild.md)
- [TTS setup](docs/guides/tts-setup.md)
- [Sentence generation](docs/guides/sentence-generation.md)
- [Song activation](docs/guides/song-activation.md)
- [CLI reference](docs/reference/cli.md)
- [Configuration reference](docs/reference/configuration.md)
- [Development guide](docs/guides/development.md)

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

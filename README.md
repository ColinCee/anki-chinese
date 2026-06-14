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

For the state-aware rebuild planner:

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync --skip-audio
```

Import the generated package into Anki:

```text
data/build/decks/chinese_rsh.apkg
```

See [Getting started](docs/getting-started.md) for export/import details and optional credentials.

## Main workflows

### Rebuild deck content

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

Optional generated content can still be run directly, then `sync` can refresh
anything downstream:

```bash
uv run anki-chinese sentences       # requires GEMINI_API_KEY
uv run anki-chinese audio           # requires TTS credentials
uv run anki-chinese sync
```

For primitive one-command rebuilds:

```bash
uv run anki-chinese build --full --skip-audio
uv run anki-chinese build --full --audio-limit 50
```

### Inspect saved deck state

```bash
uv run anki-chinese status
uv run anki-chinese review
uv run anki-chinese radicals
uv run anki-chinese radicals --scope learned
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

Audio generation records local provenance so `sync`, `status`, and `build` can
detect files generated with stale text, readings, provider models, voices, or
settings.

### Unsuspend specific characters

Manual activation mutates the open Anki collection through AnkiConnect. Keep Anki desktop open, dry-run first, then rerun with `--confirm` after checking the requested, missing, already-active, card-count, and note-count output. Confirmed activation writes a targeted undo snapshot under `data/build/anki_backups/`.

```bash
uv run anki-chinese activate chars 内 合 哟 着 --dry-run
uv run anki-chinese activate chars 内 合 哟 着 --confirm
uv run anki-chinese activate chars 内 合 哟 着 --tag batch::manual --confirm
```

See [Song activation](docs/guides/song-activation.md#manual-activation) for AnkiConnect setup and recovery notes.

### Activate cards from songs

Live activation uses AnkiConnect while Anki is open. Always dry-run first; real
activation commands write targeted undo snapshots under `data/build/anki_backups/`.

```bash
uv run anki-chinese songs analyze
uv run anki-chinese songs next --limit 20
uv run anki-chinese songs activate --limit 20 --dry-run
uv run anki-chinese songs activate --limit 20 --confirm
```

If a song activation was a mistake, dry-run the tag-based recovery command
before resuspending:

```bash
uv run anki-chinese songs resuspend 学猫叫 --dry-run
uv run anki-chinese songs resuspend 学猫叫 --confirm
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
- `activate`, `songs activate`, and `songs resuspend` mutate the open Anki collection. Use `--dry-run` first; real activation/resuspension commands write targeted undo snapshots under `data/build/anki_backups/`.
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

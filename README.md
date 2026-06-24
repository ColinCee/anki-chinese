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

### Check local readiness

```bash
uv run anki-chinese doctor
```

`doctor` is read-only. It checks local files, generated state, sync planning,
audio health, credential presence, and optionally AnkiConnect reachability with
`--check-anki`.

### Open the human dashboard

```bash
uv run anki-chinese
# or
uv run anki-chinese dashboard
```

The dashboard inspects local state, recommends the next workflow, and shows the
equivalent CLI commands. It is for human navigation; scripts and agents should
use deterministic commands directly.

### First rebuild without audio credentials

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync --skip-audio
```

For the full state-aware rebuild planner, including audio when credentials are
configured:

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
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

`sync` decides whether `init`, `audio`, and `build` are needed. Optional
generated content can still be run directly, then `sync` refreshes anything
downstream:

```bash
uv run anki-chinese sentences       # requires GEMINI_API_KEY
uv run anki-chinese audio           # requires TTS credentials
uv run anki-chinese sync
```

### Inspect saved deck state

```bash
uv run anki-chinese doctor
uv run anki-chinese status
uv run anki-chinese review
uv run anki-chinese radicals
uv run anki-chinese radicals --scope learned
```

For one-card fixes, use the card workflow instead of editing JSON by hand:

```bash
uv run anki-chinese card show 编
uv run anki-chinese card set 编 \
  --sentence "我最近在学编程，想自己做个小程序。" \
  --sentence-pinyin "wǒ zuì jìn zài xué biān chéng, xiǎng zì jǐ zuò ge xiǎo chéng xù" \
  --sentence-english "I’ve been learning programming recently and want to make a small app myself."
uv run anki-chinese sync
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
uv run anki-chinese songs learn --limit 20
uv run anki-chinese songs learn --limit 20 --confirm
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
- `activate`, `songs learn`, `songs activate`, `songs resuspend`, and undo commands mutate the open Anki collection only with `--confirm`. Preview first; confirmed live mutations write safety snapshots under `data/build/anki_backups/`.
- Keep `.env`, API keys, Google service-account files, generated audio, and generated deck outputs out of commits.

## Documentation

Start with [docs/](docs/README.md):

- [Getting started](docs/getting-started.md)
- [Architecture overview](docs/architecture/overview.md)
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

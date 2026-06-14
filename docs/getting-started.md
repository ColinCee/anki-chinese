# Getting started

This guide takes you from an existing Anki export to a regenerated deck package.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Anki desktop
- An Anki `.apkg` export containing the source notes you want to rebuild

Optional features need additional local services or API credentials:

| Feature | Requirement |
| --- | --- |
| Sentence generation and meaning repair | `GEMINI_API_KEY` |
| Audio generation | Google Cloud Text-to-Speech auth and/or `MINIMAX_API_KEY` |
| Live activation and song planning | Anki desktop open with AnkiConnect installed |

## Install

```bash
git clone https://github.com/ColinCee/anki-chinese.git
cd anki-chinese
uv sync
```

For development, install dev dependencies:

```bash
uv sync --group dev
```

## Add the source deck export

Export your current Anki deck as a native Anki package and place it at:

```text
data/source/All Decks.apkg
```

In Anki, use **File -> Export**, choose an Anki package (`.apkg`), and include the notes/cards needed by the `Chinese RSH` note type. The default path is configured in `src/anki_chinese/config.py`.

## Build without optional network features

```bash
uv run anki-chinese init
uv run anki-chinese status
uv run anki-chinese build
```

You can also let the workflow planner decide what is stale:

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync --skip-audio
```

The generated package is:

```text
data/build/decks/chinese_rsh.apkg
```

Import that file into Anki. The deck and model IDs are stable, so re-importing updates existing notes instead of creating duplicate notes, as long as the IDs are not changed.

## Optional: generate sentences

Set a Gemini API key:

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY
```

Then run:

```bash
uv run anki-chinese sentences
uv run anki-chinese sentences audit
uv run anki-chinese build
```

See [sentence generation](guides/sentence-generation.md) for candidate picking, confuser repair, and meaning repair.

## Optional: generate audio

Audio uses Google Cloud Text-to-Speech for single-character audio and MiniMax for sentence audio. See [TTS setup](guides/tts-setup.md) before running a full audio job.

```bash
uv run anki-chinese test-tts --char 早 --provider google
uv run anki-chinese audio --limit 20
uv run anki-chinese build
```

After audio generation, future `sync` and `status` runs use local audio
provenance to detect stale files if text, readings, provider models, voices, or
settings change.

## Optional: activate live Anki cards from songs

Live activation changes the open Anki collection through AnkiConnect. It does not rebuild note content.

```bash
uv run anki-chinese songs analyze
uv run anki-chinese songs next --limit 20
uv run anki-chinese songs activate --limit 20 --dry-run
```

After checking the preview, add `--confirm` for the real activation. Confirmed
activation commands write targeted undo snapshots under
`data/build/anki_backups/`; see [song activation](guides/song-activation.md).

## Common checks

```bash
uv run anki-chinese --help
uv run anki-chinese status
uv run anki-chinese songs verify
```

For the full command map, see the [CLI reference](reference/cli.md).

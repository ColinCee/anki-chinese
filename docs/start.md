# Start

Use this when setting up the project or rebuilding a deck for the first time.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Anki desktop
- The canonical source records at `data/source/characters.json`
- A native Anki export at `data/source/All Decks.apkg` for bootstrap/migration

Optional features need credentials or local services:

| Feature | Requirement |
| --- | --- |
| Sentence generation / keyword repair | `GEMINI_API_KEY` |
| Character audio | Google Cloud Text-to-Speech ADC or service-account auth |
| Sentence audio | `MINIMAX_API_KEY` |
| Song learning / live activation | Anki open with AnkiConnect installed |

## Install

```bash
git clone https://github.com/ColinCee/anki-chinese.git
cd anki-chinese
uv sync
```

For development:

```bash
uv sync --group dev
```

## Export from Anki

In Anki, use **File -> Export**, choose a native `.apkg`, and save it as:

```text
data/source/All Decks.apkg
```

Import a new export into the canonical source explicitly:

```bash
uv run anki-chinese source import --input "data/source/All Decks.apkg" --replace
```

The export is retained as a legacy/bootstrap input for rebuildable note content;
The canonical source after migration is `data/source/characters.json`; neither
file is reliable as current live suspended state after AnkiConnect changes.

## Check readiness

```bash
uv run anki-chinese doctor
```

`doctor` is read-only. It checks local files, generated state, sync planning,
audio health, and optional credential presence. When Anki is open, add:

```bash
uv run anki-chinese doctor --check-anki
```

That performs an AnkiConnect version probe only; it does not mutate Anki.

## Open the workbench

```bash
uv run anki-chinese
# or
uv run anki-chinese workbench
```

The workbench is the human entrypoint. It inspects local state, recommends one
next action, previews safe workflows in-place, can run sync/doctor/card-edit
and song-preview actions, and keeps equivalent CLI commands behind Advanced.
`dashboard` remains a compatibility alias. Agents and scripts should use
deterministic commands directly.

## First rebuild

Without audio credentials:

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync --skip-audio
```

With audio credentials configured:

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync
```

The generated package is:

```text
data/build/decks/chinese_rsh.apkg
```

Import that file into Anki. Stable deck/model IDs and character-based GUIDs let
imports update existing notes instead of duplicating them.

## Next

- [Workflows](workflows.md) — common day-to-day tasks.
- [Reference](reference.md) — commands, environment variables, data layout, and model facts.
- [Architecture](architecture.md) — how the rebuild and live activation lanes fit together.

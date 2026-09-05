# anki-chinese

Maintain a Mandarin Anki deck with Cantonese support: character recognition,
vocabulary in context, example sentences, pronunciation audio, and song-driven
study. Anki handles reviews; this project handles rebuildable content and
separate, preview-first live card activation.

## Start

You need Python 3.13+, [uv](https://docs.astral.sh/uv/), and Anki desktop for
import/review. Canonical character records are included; no Anki export or
source replacement is needed for a normal first rebuild.

```bash
git clone https://github.com/ColinCee/anki-chinese.git
cd anki-chinese
uv sync
uv run anki-chinese doctor
uv run anki-chinese
```

The terminal workbench guides human workflows. Agents and scripts use
`uv run anki-chinese <command> --help` and deterministic commands directly.
`doctor` is read-only: it checks readiness and credential presence, not provider
authentication. `doctor --check-anki` adds only a local AnkiConnect version probe.

## First rebuild

Without paid generation or audio credentials:

```bash
uv run anki-chinese sync --dry-run
uv run anki-chinese sync --skip-audio
```

Import `data/build/decks/chinese_rsh.apkg` into Anki. Existing audio may be
included, but missing audio is not generated. For full audio, configure
[credentials](docs/reference.md#environment-variables) and run `sync`.
Sentence generation is [separate](docs/workflows.md#generate-sentences-and-meanings).

Stable [Anki identity](docs/reference.md#anki-model) lets imports update notes
instead of duplicating them. Rebuilding alone does not change the open collection.
AnkiConnect is needed for live-state workflows, not APKG rebuilding.
To use a different dataset, follow [Replace the source](docs/workflows.md#replace-the-source).

## Find the right guide

- [Workflows](docs/workflows.md): edit content, generate audio, rebuild templates,
  and learn from songs.
- [Reference](docs/reference.md): configuration, data ownership, and Anki model.
- [Decisions](docs/decisions/): why the study target and providers were chosen.
- [Contributing](CONTRIBUTING.md): code map, development, and documentation maintenance.
- [Security](SECURITY.md): private data and vulnerability reporting.

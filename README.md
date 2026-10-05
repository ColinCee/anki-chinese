# anki-chinese

Maintain a Mandarin Anki deck with Cantonese support.

[![CI](https://github.com/ColinCee/anki-chinese/actions/workflows/ci.yml/badge.svg?branch=master&event=push)](https://github.com/ColinCee/anki-chinese/actions/workflows/ci.yml?query=branch%3Amaster)

## What it does

- Builds character recognition, vocabulary-in-context, and example-sentence cards
- Generates Mandarin and Cantonese pronunciation audio
- Plans study targets from curated song lyrics
- Leaves reviews to Anki; keeps rebuildable content separate from preview-first
  live card activation

## Stack

| Area | Tooling |
| --- | --- |
| CLI / workbench | Python 3.13, uv, Typer, Textual |
| Deck output | genanki APKG, AnkiConnect for live state |
| Text | jieba, pypinyin, pycantonese, wordfreq |
| Generation | Gemini (sentences), Google TTS or MiniMax (audio) |

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

## How it works

Canonical records in `data/source/` are enriched, given audio, and rebuilt into
an APKG for manual import; live suspension and review state change only through
AnkiConnect. See [Data layout](docs/reference.md#data-layout) and
[Workflows](docs/workflows.md).

## Find the right guide

- [Workflows](docs/workflows.md): edit content, generate audio, rebuild templates,
  and learn from songs.
- [Reference](docs/reference.md): configuration, data ownership, and Anki model.
- [Decisions](docs/decisions/): why the study target and providers were chosen.
- [Contributing](CONTRIBUTING.md): code map, development, and documentation maintenance.
- [Security](SECURITY.md): private data and vulnerability reporting.

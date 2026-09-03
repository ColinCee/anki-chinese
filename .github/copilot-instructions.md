# Copilot Instructions for anki-chinese

## Project overview

`anki-chinese` is a Python CLI that rebuilds an Anki deck for Mandarin study
with Cantonese support. Live suspended-state changes are handled separately
through AnkiConnect.

Read only the canonical document relevant to the task:

- `docs/start.md`: setup and first rebuild
- `docs/workflows.md`: user tasks
- `docs/reference.md`: stable commands, configuration, and data layout
- `docs/architecture.md`: boundaries and data flow
- `docs/decisions/`: rationale for durable choices
- `CONTRIBUTING.md`: contribution and documentation policy

Use `uv run anki-chinese <command> --help` as the authoritative command
reference.

## Invariants

- Keep the CLI surface narrow: user workflows go through `uv run anki-chinese ...`.
- Human navigation starts with the Textual workbench; agents and scripts use
  deterministic CLI commands.
- Preserve stable Anki identity: do not change `MODEL_ID`, `DECK_ID`, field order, or GUID behavior without an explicit migration.
- Keep rebuildable `.apkg` content separate from live suspended state and tags.
- Keep provider-specific code behind `audio/provider.py` and `audio/factory.py`.
- Keep AnkiConnect details behind `activation/`.
- Treat generated files under `data/build/` and `data/state/enriched.json` as generated artifacts.
- Keep the workbench presentational; reuse workflow and domain functions.
- `doctor` is read-only; `--check-anki` only probes AnkiConnect.

## Development

```bash
uv sync --group dev
uv run ruff check
uv run pyright
uv run pytest
uv run anki-chinese --help
uv run python -m anki_chinese.cli --help
```

## Non-obvious constraints

- Google Cloud TTS uses ADC or service-account authentication, not an API key.
- The study target is mainland Mandarin simplified for active study and
  traditional for recognition. Particle `著` can map to `着`; lexical uses such
  as `著名` and `原著` remain valid.
- Runtime song planning must remain deterministic: no LLM calls, network
  translation, OpenCC passes, or pypinyin guessing.

## Documentation

Follow the ownership and consolidation rules in `CONTRIBUTING.md`. Prefer
editing or deleting existing material; do not add a new page or repeat canonical
content merely to explain a change.

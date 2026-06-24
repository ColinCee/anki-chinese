# Contributing

Thanks for helping improve `anki-chinese`.

## Setup

```bash
git clone https://github.com/ColinCee/anki-chinese.git
cd anki-chinese
uv sync --group dev
```

For a first deck build, follow [Start](docs/start.md).

## Before opening a PR

Run:

```bash
uv run ruff check
uv run pyright
uv run pytest
uv run anki-chinese --help
uv run python -m anki_chinese.cli --help
```

If you change song lyrics, also run:

```bash
uv run anki-chinese songs verify
```

## Pull request checklist

- Keep changes focused, avoid committing generated artifacts from `data/build/`, and do not include unintended churn in tracked generated state such as `data/state/enriched.json`.
- Update docs when setup, CLI behavior, environment variables, data layout, or safety expectations change.
- Add or update tests for behavior changes and regressions.
- Do not change `MODEL_ID`, `DECK_ID`, note fields, or card template field references without an explicit migration plan.
- For live Anki activation changes, preserve dry-run behavior, undo snapshots before real mutations, and clear affected note/card counts.

## Documentation structure

- README: public overview and shortest successful path.
- `docs/start.md`: first setup and first rebuild.
- `docs/workflows.md`: common day-to-day tasks.
- `docs/reference.md`: commands, config, data layout, model facts, and development commands.
- `docs/architecture.md`: system overview.
- `docs/decisions/`: durable decisions and tradeoffs.

## Secrets and generated files

Never commit `.env`, API keys, Google service-account files, generated audio, built decks, or local Anki backups.

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

- Keep changes focused, avoid committing generated artifacts from `data/build/` or derived local state under `data/state/`.
- Update docs when setup, CLI behavior, environment variables, data layout, or safety expectations change.
- Add or update tests for behavior changes and regressions.
- Do not change `MODEL_ID`, `DECK_ID`, note fields, or card template field references without an explicit migration plan.
- For live Anki activation changes, preserve dry-run behavior, undo snapshots before real mutations, and clear affected note/card counts.

## Documentation ownership

Each kind of information has one canonical home:

| Location | Owns |
| --- | --- |
| `README.md` | Public overview and links to the shortest successful path. |
| `docs/start.md` | First setup and first rebuild. |
| `docs/workflows.md` | Goal-oriented, day-to-day procedures. |
| `docs/reference.md` | Stable command, configuration, data-layout, and model facts. CLI `--help` remains authoritative for options. |
| `docs/architecture.md` | Current system boundaries, data flow, and package responsibilities. |
| `docs/decisions/` | The context and consequences of durable decisions. Supersede old decisions rather than silently rewriting their history. |
| `CONTRIBUTING.md` | Contributor workflow and documentation policy. |
| `SECURITY.md` | Security reporting and repository-specific secret handling. |
| `.github/copilot-instructions.md` | Only non-obvious repository invariants and pointers needed on most agent tasks. |
| `.agents/skills/` | Task-specific procedures loaded on demand; they must not duplicate general project documentation. |

Before adding documentation, search these locations for the concept and edit its
canonical home. Prefer replacing, consolidating, or deleting stale text over
appending another explanation. Add a new document only when it has a distinct
purpose or records a durable decision that does not fit an existing page.

Documentation changes should keep the repository's knowledge model coherent:

- Link to canonical detail instead of copying it into README, contributor, agent,
  and skill files.
- Document behavior in code, tests, schemas, or CLI help when those can be the
  executable source of truth.
- In the same change, remove instructions made obsolete by the new behavior.
- Review the complete affected section, not only the paragraph being added.
- Keep temporary plans and implementation notes in issues or pull requests, not
  as permanent repository documents.

## Secrets and generated files

Never commit `.env`, API keys, Google service-account files, generated audio, built decks, or local Anki backups.

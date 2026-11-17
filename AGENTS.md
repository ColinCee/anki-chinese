# Agent instructions

## Find the owner

Read only the matching section, not the whole documentation set.
`uv run anki-chinese <command> --help` owns commands/options.

Checks: `uv run ruff check && uv run ruff format --check && uv run ty check && uv run pytest && uv run anki-chinese songs verify && uv run anki-chinese --help && uv run python -m anki_chinese.cli --help`

| Task | Start here |
| --- | --- |
| Setup / first import | [README](README.md#start) |
| Locate code / checks | [Contributor code map](CONTRIBUTING.md#where-to-make-a-change) / [checks](CONTRIBUTING.md#development) |
| Edit or add card content | [Card workflow](docs/workflows.md#fix-one-card) |
| Change card HTML/CSS | [Template rebuild](docs/workflows.md#customize-card-templates) |
| Configuration / data / identity | [Reference](docs/reference.md) |
| Curate lyrics / change normalization | [Apply the study policy](docs/decisions/study-target-policy.md#applying-the-policy) |
| Chinese chat practice | [Tutor skill](.agents/skills/chinese-tutor/SKILL.md) |
| Live state / mutations | [Live safety skill](.agents/skills/anki-live-activation-safety/SKILL.md) |
| Docs / skill maintenance | [Maintenance skill](.agents/skills/documentation-maintenance/SKILL.md) |

## Guardrails

- Humans use the presentational workbench; agents use deterministic CLI commands.
- Keep rebuildable content separate from live suspension, review state, and tags.
- Follow the [study policy](docs/decisions/study-target-policy.md) for song planning.
- [`test_guardrails.py`](tests/regressions/test_guardrails.py) pins Anki identity
  (changes need a migration), the workbench/audio/AnkiConnect boundaries, read-only
  `doctor`, and deterministic song planning. Fix the code, not the test.
- Use only task-relevant skills. Read-only tasks do not inherit mutation gates;
  template-only changes do not require content edits or audio regeneration.

When a task reveals guidance friction, apply the
[maintenance loop](CONTRIBUTING.md#maintaining-docs-and-skills) once in the
owning file. Prefer correction, deletion, or a better pointer over new prose.

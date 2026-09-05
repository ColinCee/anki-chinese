# Copilot instructions

## Find the owner

Read only the matching section, not the whole documentation set.
`uv run anki-chinese <command> --help` owns commands/options.

| Task | Start here |
| --- | --- |
| Setup / first import | [README](../README.md#start) |
| Locate code / checks | [Contributor code map](../CONTRIBUTING.md#where-to-make-a-change) / [checks](../CONTRIBUTING.md#development) |
| Edit or add card content | [Card workflow](../docs/workflows.md#fix-one-card) |
| Change card HTML/CSS | [Template rebuild](../docs/workflows.md#customize-card-templates) |
| Configuration / data / identity | [Reference](../docs/reference.md) |
| Curate lyrics / change normalization | [Apply the study policy](../docs/decisions/study-target-policy.md#applying-the-policy) |
| Live state / mutations | [Live safety skill](../.agents/skills/anki-live-activation-safety/SKILL.md) |
| Docs / skill maintenance | [Maintenance skill](../.agents/skills/documentation-maintenance/SKILL.md) |

## Guardrails

- Humans use the workbench; agents use deterministic CLI commands.
- Do not change `MODEL_ID`, `DECK_ID`, field order, or GUID behavior without an explicit migration.
- Keep rebuildable content separate from live suspension, review state, and tags.
- Keep the workbench presentational, provider details behind `audio/provider.py`
  and `audio/factory.py`, and AnkiConnect access behind `activation/`.
- `doctor` is read-only; `--check-anki` is only a version probe.
- Runtime song planning stays deterministic: no LLM, translation, OpenCC, or
  pypinyin guessing. Follow the [study policy](../docs/decisions/study-target-policy.md).
- Use only task-relevant skills. Read-only tasks do not inherit mutation gates;
  template-only changes do not require content edits or audio regeneration.

When a task reveals guidance friction, apply the
[maintenance loop](../CONTRIBUTING.md#maintaining-docs-and-skills) once in the
owning file. Prefer correction, deletion, or a better pointer over new prose.

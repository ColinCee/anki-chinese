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

- Humans use the workbench; agents use deterministic CLI commands.
- Keep rebuildable content separate from live suspension, review state, and tags.
- Use only task-relevant skills. Read-only tasks do not inherit mutation gates;
  template-only changes do not require content edits or audio regeneration.

[`test_guardrails.py`](tests/regressions/test_guardrails.py) checks the rules below
from source imports and calls; fix the code, not the test. It reads each module
directly and matches names, so these are on you: code reached through a helper,
a mutation under a new name (it checks name prefixes and a client-call allowlist),
`doctor` writing via `Path.open("w")`, `.rename` or `.replace`, and
`config.ANKICONNECT_URL` read through a module import.

- Change `MODEL_ID`, `DECK_ID`, field order, or GUID behavior only with an
  explicit migration (pinned).
- Keep the workbench presentational (judgment). Tested: it imports no activation
  mutations and calls only read methods on the AnkiConnect client.
- Keep provider details behind `audio/provider.py` and `audio/factory.py` (others
  may also import `state` and `files`; neutral `audio/` modules import no
  third-party code), and AnkiConnect access behind `activation/` (both tested).
- `doctor` is read-only; `--check-anki` is only a version probe. Tested: it calls
  only `version()` on the client and has no direct file writes or mutation imports.
- Runtime song planning stays deterministic: no LLM, translation, OpenCC,
  pypinyin, or network. `songs/analysis.py` and `lyrics.py` may import only an
  allowlist; it does not check logic. Follow the [study policy](docs/decisions/study-target-policy.md).

When a task reveals guidance friction, apply the
[maintenance loop](CONTRIBUTING.md#maintaining-docs-and-skills) once in the
owning file. Prefer correction, deletion, or a better pointer over new prose.

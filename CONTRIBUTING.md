# Contributing

Follow [Start](README.md#start) to install the project, then install development
dependencies with `uv sync --group dev`.

## Development

Use the smallest existing checks that cover the change. Before opening a PR
with code changes, run:

```bash
uv run ruff check
uv run pyright
uv run pytest
uv run anki-chinese --help
uv run python -m anki_chinese.cli --help
```

For lyric changes, also run `uv run anki-chinese songs verify`. Documentation-only
changes need link, command, and factual review, not unrelated builds or test runs.
CI configuration lives in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Preserve [Anki identity](docs/reference.md#anki-model) and the
[live activation safety boundary](docs/workflows.md#learn-characters-from-songs).
Do not commit secrets, private study data, or generated artifacts; see
[Security](SECURITY.md) and [data ownership](docs/reference.md#data-layout).

## Where to make a change

Paths below are relative to `src/anki_chinese/`. Tests generally mirror these areas.

| Concern | Entry points / boundary |
| --- | --- |
| CLI / workbench | `cli/`, `tui/`: presentation; reuse domain/workflow functions. |
| Sync | `workflows/sync.py`, `workflows/pipeline_state.py`: stage planning/fingerprints. |
| Authored content | `notes/source.py`, `cli/card.py`: canonical records and validation. |
| Anki projection | `config.py`, `notes/model.py`, `deck.py`: IDs, field order, GUIDs, template assembly. |
| Card appearance | `cards/`: four faces, CSS, and shared scripts; [rebuild procedure](docs/workflows.md#customize-card-templates). |
| Readings | `data_sources/`, `notes/enrich.py`: missing-reading lookup. |
| Generated text | `sentences/`, `cli/sentences.py`, `cli/keywords.py`: Gemini generation/repair. |
| Audio | `audio/provider.py`, `audio/factory.py`, `audio/state.py`: protocol, construction, provenance; vendor details stay in implementations. |
| Lyrics / planning | `songs/lyrics.py`, `songs/analysis.py`: [study policy](docs/decisions/study-target-policy.md#applying-the-policy); fetching is a separate network action. |
| Live collection | `activation/`: all AnkiConnect access, mutation services, and safety snapshots. |
| Reading coverage | `character_frequency.py`: cached frequency data plus live review state. |

Card regressions start in `tests/regressions/test_card_template_sync.py` and
`tests/deck/`; shared runtime fixtures live in `tests/conftest.py`.
[Workflows](docs/workflows.md) owns content/live-state procedures and current
pipeline limitations; [Reference](docs/reference.md) owns paths and model constraints.

## Documentation ownership

| Location | Owns |
| --- | --- |
| `README.md` | Introduction, installation, first rebuild/import, and navigation. |
| `docs/workflows.md` | Day-to-day tasks and recovery steps. |
| `docs/reference.md` | Configuration, data ownership, and model constraints. |
| `docs/decisions/` | Historical rationale and consequences, not current runbooks. |
| `CONTRIBUTING.md` | Code map, contributor checks, and this maintenance policy. |
| `SECURITY.md` | Private-data handling and security reporting. |
| `.github/copilot-instructions.md` | Always-needed agent guardrails and routing. |
| `.agents/skills/*/SKILL.md` | Trigger-specific safeguards and non-obvious workflow traps. |

CLI help owns commands/options. Code, schemas, and tests own implementation
details. Link to those sources rather than maintaining parallel catalogues.
Issue and PR templates collect evidence; they do not restate these policies.

## Maintaining docs and skills

Apply this loop when a task exposes stale, missing, hard-to-find, duplicated, or
obstructive guidance. It is a bounded part of that task, not a mandatory new audit.

1. **Trace the friction.** Identify the failed lookup or misleading instruction
   and verify it against current code, CLI help, or a reproducible observation.
   Separate intended policy from actual behavior; report disagreements rather
   than silently weakening safety rules.
2. **Find the owner.** Search the locations above. Prefer a better heading or
   link when the answer already exists. Replace, merge, or delete stale text
   before adding prose.
3. **Keep only durable guidance.** Add information only when it is not already
   discoverable at its authoritative source and prevents a recurring mistake.
   A new file needs a distinct audience or purpose that no existing owner fits.
   Do not retain task logs, transient failures, copied options, or speculative rules.
4. **Keep skills conditional.** State the trigger, safety gates, and stop condition.
   Exclude adjacent tasks that need no special handling. Do not demand setup,
   interviews, new documents, tools, or recursive skill calls unrelated to the job.
   Preserve dry-runs, backups, identity constraints, and human approval boundaries.
5. **Close once.** Review the whole affected section, resolve its links, and
   check examples through help without executing mutations or paid operations.
   Search for superseded copies. Explain meaningful corrections and any net growth;
   there is no quota to create a doc change after every task.

This loop applies to itself and every repository skill. Make local, reviewable
edits; do not silently rewrite installed third-party skills or store personal
information. Keep policy changes explicit. Preserve historical decision rationale;
mark superseded decisions rather than rewriting history. If no durable fix is
needed, leave the guidance alone.

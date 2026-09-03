---
name: documentation-maintenance
description: Use when adding, rewriting, reorganizing, or reviewing anki-chinese documentation or agent instructions. Prevents append-only documentation by requiring canonical placement, consolidation, and deletion of stale material.
when_to_use: Trigger on changes to README.md, CONTRIBUTING.md, SECURITY.md, docs/, .github/copilot-instructions.md, pull request documentation, or another project skill.
argument-hint: "[topic-or-files]"
---

# Documentation Maintenance

Keep the repository's knowledge base coherent rather than merely adding text.

1. Read the documentation ownership table in `CONTRIBUTING.md`.
2. Search all canonical locations for the concept before editing.
3. Choose one canonical home based on audience and purpose.
4. Edit that source in place. Replace, merge, move, or delete stale material in
   the same change.
5. Link to canonical detail from other surfaces instead of copying it.
6. Add a file only for a genuinely distinct purpose or a durable decision that
   cannot fit an existing page.
7. Keep command options in Typer help and code-derived facts in code, tests, or
   schemas; documentation should explain tasks, stable facts, boundaries, and
   rationale.
8. Before finishing, review the full affected sections and search again for
   contradictions or obsolete instructions.

Preserve historical decision records. If a decision changes, add or clearly
mark a superseding decision instead of rewriting the original rationale as
though the old decision never existed.

For agent guidance, retain only non-inferable invariants, safety rules, and
pointers needed for its trigger. Remove architecture summaries, command
catalogues, and workflows already owned by canonical docs or CLI help.

Report which source became canonical and what was consolidated or removed.

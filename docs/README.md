# Documentation

This is the canonical documentation map for **anki-chinese**. The README is the public landing page; these docs hold the detailed setup, workflows, reference material, architecture notes, and historical decisions.

## Start here

- [Getting started](getting-started.md) — first-run setup from an Anki export to a rebuilt `.apkg`
- [Architecture overview](architecture/overview.md) — how the content rebuild and live activation lanes fit together

For day-to-day human use, start with:

```bash
uv run anki-chinese
```

The Textual dashboard inspects local state, recommends the next workflow, and
shows equivalent CLI commands. Agents and scripts should use the deterministic
commands documented in the CLI reference.

## Guides

Task-oriented docs for common workflows.

- [Deck rebuild workflow](guides/deck-rebuild.md) — dashboard/sync-first rebuilds, card edits, generated content, build, and import
- [TTS setup](guides/tts-setup.md) — Google Cloud ADC/service-account auth, MiniMax setup, and smoke tests
- [Sentence generation](guides/sentence-generation.md) — Gemini setup, sentence generation, meaning repair, and confuser audits
- [Song activation](guides/song-activation.md) — AnkiConnect setup and song-driven unsuspending
- [Mainland Mandarin study target](guides/mainland-mandarin.md) — simplified-first policy and traditional recognition notes
- [Customization](guides/customization.md) — overrides, templates, deck settings, and manual data
- [Development](guides/development.md) — contributor setup, tests, linting, and project layout

## Reference

Stable facts that should match the current code.

- [CLI reference](reference/cli.md) — command map and when to use each command
- [Configuration reference](reference/configuration.md) — environment variables and credentials
- [Data layout](reference/data-layout.md) — committed inputs, generated state, and ignored build outputs
- [Anki model reference](reference/anki-model.md) — stable IDs, fields, card templates, and import behavior

## Decisions

Architecture Decision Records explain why major choices were made. They may include historical context; use the guides and reference docs for current setup instructions.

- [ADR-001: Sentence generation strategy](decisions/ADR-001-sentence-generation.md)
- [ADR-002: TTS provider strategy](decisions/ADR-002-tts-provider-strategy.md)
- [ADR-003: Mainland Mandarin study target policy](decisions/ADR-003-study-target-policy.md)

## Research

Research docs are point-in-time notes, not setup instructions.

- [Research index](research/README.md)
- [Anki ecosystem pain points](research/anki-ecosystem-pain-points.md)
- [TTS providers](research/tts-providers.md)

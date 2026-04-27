# Documentation

## Decisions

Architecture Decision Records for major technical choices.

- [ADR-001: Sentence Generation Strategy](decisions/ADR-001-sentence-generation.md) — Gemini Flash Lite generation with self-validation pipeline (v6, production)
- [ADR-002: TTS Provider Strategy](decisions/ADR-002-tts-provider-strategy.md) — Hybrid Google + MiniMax approach for character vs sentence audio
- [ADR-003: Mainland Mandarin Study Target Policy](decisions/ADR-003-study-target-policy.md) — Proposed default track: mainland Mandarin, simplified-first, traditional recognition support

## Guides

How-to docs for using and developing the project.

- [Customization](guides/customization.md) — Character overrides, card templates, deck settings, example words
- [Development](guides/development.md) — Repo layout, testing strategy, validation, migration notes
- [Mainland Mandarin Study Target](guides/mainland-mandarin.md) — Default learner target, traditional recognition policy, Taiwanese lyric handling
- [Song Activation](guides/song-activation.md) — AnkiConnect setup and song-based unsuspending workflow
- [TTS Setup](guides/tts-setup.md) — Google Cloud and MiniMax API key setup, smoke testing, env vars

## Research

Exploratory research and provider comparisons.

- [Anki Ecosystem Pain Points](research/anki-ecosystem-pain-points.md) — Running notes on Anki friction and custom-app triggers
- [TTS Providers](research/tts-providers.md) — Full comparison of 6 TTS providers for Chinese pronunciation

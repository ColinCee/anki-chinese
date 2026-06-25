# Architecture

`anki-chinese` rebuilds a Mandarin-focused Anki deck with Cantonese support. It
parses an Anki `.apkg` export, enriches character notes, optionally generates
sentences/audio, and writes a regenerated `.apkg`.

## Two lanes

| Lane | Commands | Source of truth | What changes |
| --- | --- | --- | --- |
| Human navigation | `dashboard`, `doctor` | Local files, workflow state, optional AnkiConnect probe | Recommendations, safe previews, readiness checks. |
| Content rebuild | `sync`, `card`, `sentences`, `keywords`, `audio`, `build` | Exported `.apkg` plus manual overrides | Fields, sentences, audio references, templates, generated package. |
| Live activation | `songs learn`, `activate`, `songs activate` | Open Anki collection through AnkiConnect | Suspended state and optional tags. |

Do not treat `data/source/All Decks.apkg` as current live state after
AnkiConnect mutations unless it was exported immediately beforehand.

## Rebuild flow

```text
data/source/All Decks.apkg
  -> dashboard / doctor
  -> sync / init
  -> data/state/enriched.json
  -> optional card / sentences / keywords / audio
  -> sync / build
  -> data/build/decks/chinese_rsh.apkg
```

Stable deck/model IDs and character-based GUIDs let repeated imports update
existing Anki notes instead of duplicating them.

## Workflow state

| State | Path | Purpose |
| --- | --- | --- |
| Enriched notes | `data/state/enriched.json` | Ignored rebuildable note content and generated field references. |
| Pipeline fingerprints | `data/state/pipeline.json` | Local record of successful stages and their inputs/outputs. |
| Audio provenance | `data/state/audio_manifest.json` | Local record of provider/model/voice/settings used for valid generated audio. |

`sync`, `status`, `doctor`, `build`, and the dashboard use the same state model
to explain what is stale and why.

## Live activation flow

```text
song planner or explicit chars
  -> activation service
  -> AnkiConnect
  -> live Anki cards
```

Confirmed activation/resuspension writes targeted undo snapshots under
`data/build/anki_backups/`. Confirmed undo writes restore safety snapshots before
changing live cards or tags.

## Main packages

| Path | Purpose |
| --- | --- |
| `src/anki_chinese/cli/` | Typer commands and Rich output. |
| `src/anki_chinese/tui/` | Textual dashboard and recommendation/guidance model. |
| `src/anki_chinese/workflows/` | Shared sync planning and pipeline fingerprints. |
| `src/anki_chinese/notes/` | Note model, `.apkg` parsing, enrichment, reporting, JSON persistence. |
| `src/anki_chinese/audio/` | TTS provider protocol, Google/MiniMax implementations, state, retry/rate limits. |
| `src/anki_chinese/sentences/` | Gemini sentence generation and meaning repair. |
| `src/anki_chinese/songs/` | Lyric parsing, study normalization, analysis, activation planning. |
| `src/anki_chinese/activation/` | AnkiConnect client and activation service. |
| `src/anki_chinese/data_sources/` | CEDICT, HSK, pinyin, jyutping, and lookup helpers. |
| `src/anki_chinese/cards/` | Packaged Anki card templates and CSS. |
| `src/anki_chinese/config.py` | Paths, deck metadata, stable IDs, field order. |

## Boundaries

- CLI/TUI present choices; workflow/domain code decides what should happen.
- Agents and scripts use deterministic CLI commands, not the dashboard.
- Provider-specific TTS behavior stays behind `TTSProvider`.
- AnkiConnect behavior stays behind `activation/`.
- Runtime song planning stays deterministic: no LLM calls, network translation,
  OpenCC passes, or pypinyin guessing.

## Study target

The default learner target is mainland Mandarin with simplified characters for
active study and traditional characters as recognition support. Song planning
maps contextual particle `著` to `着`, while preserving lexical `著` words such
as `著名` and `原著`.

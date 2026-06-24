# Architecture overview

`anki-chinese` is a Python CLI that rebuilds a Mandarin-focused Anki deck with Cantonese support. It parses an Anki `.apkg` export, enriches each character note, optionally generates AI sentences and TTS audio, and writes a regenerated `.apkg`.

## Two lanes

The project intentionally separates content rebuilds from live study-state changes.

| Lane | Commands | Source of truth | What changes |
| --- | --- | --- | --- |
| Human navigation | `dashboard`, `doctor` | Local files, workflow state, optional AnkiConnect probe | Recommendations and readiness checks only. |
| Content rebuild | `sync`, `card`, `init`, `sentences`, `keywords`, `audio`, `build` | Exported `.apkg` plus `data/state/enriched.json` | Fields, sentences, audio references, templates, generated package |
| Live activation | `songs learn`, `activate`, `songs activate` | Open Anki collection through AnkiConnect | Suspended state and optional tags |

Do not treat `data/source/All Decks.apkg` as current live state after AnkiConnect mutations unless you exported it immediately beforehand.

## Content rebuild flow

```text
data/source/All Decks.apkg
  -> dashboard / doctor
  -> sync / init
  -> data/state/enriched.json
  -> optional card / sentences / keywords / audio
  -> sync / build
  -> data/build/decks/chinese_rsh.apkg
```

The generated package can be imported into Anki repeatedly. Stable deck/model IDs and stable note GUIDs let Anki update existing notes instead of duplicating them.

## State-aware rebuild planning

The rebuild lane keeps local workflow metadata so commands can decide what needs
to run instead of relying only on timestamps or note fields.

| State | Path | Purpose |
| --- | --- | --- |
| Enriched notes | `data/state/enriched.json` | Rebuildable note content and generated field references. This file is tracked so the repo has a useful baseline. |
| Pipeline fingerprints | `data/state/pipeline.json` | Local-only record of successful `init`, content-generation, `audio`, and `build` stages. `sync` uses it to explain whether recorded stages still match current inputs/outputs. |
| Audio provenance | `data/state/audio_manifest.json` | Local-only record of which provider/model/voice/settings produced each valid generated audio file. `sync`, `status`, and `build` use the same audio-state logic to detect missing, stale, or orphaned audio. |

Audio provenance is not a separate source of truth and does not require a
separate diagnostic command for normal use. Its purpose is to make existing
workflow commands state-aware: if a MiniMax model, voice, Google voice, sentence,
reading, or referenced file changes, `sync` can plan audio regeneration and
`build` can warn before packaging stale media.

The dashboard consumes the same planning/readiness logic. It recommends one
workflow from local state but does not duplicate or replace the deterministic
CLI commands used by agents and scripts.

## Live activation flow

```text
manual chars or song planner
  -> activation service
  -> AnkiConnect
  -> live Anki cards
```

Activation is general infrastructure. The song `learn` workflow is the preferred
human path for song batches, while `songs activate` and `activate chars` remain
lower-level primitives.

Song planning uses live Anki active state: a character counts as active when any
card for its `Chinese RSH` note is unsuspended. Real activation and resuspension
commands write targeted undo snapshots under `data/build/anki_backups/` before
mutating live cards or tags.

## Main packages

| Path | Purpose |
| --- | --- |
| `src/anki_chinese/cli/` | Typer commands and Rich output, including read-only readiness checks through `doctor` |
| `src/anki_chinese/tui/` | Textual dashboard app plus workflow guidance model |
| `src/anki_chinese/notes/` | Note model, `.apkg` parsing, enrichment, reporting, JSON persistence |
| `src/anki_chinese/deck.py` | `genanki` package creation |
| `src/anki_chinese/cards/` | Card HTML/CSS templates |
| `src/anki_chinese/audio/` | TTS provider protocol, Google/MiniMax implementations, file helpers, retry/rate limits |
| `src/anki_chinese/sentences/` | Gemini sentence generation and meaning repair |
| `src/anki_chinese/songs/` | Lyric parsing, study normalization, song analysis, activation planning |
| `src/anki_chinese/activation/` | AnkiConnect client and activation service |
| `src/anki_chinese/data_sources/` | CEDICT, HSK, pinyin, jyutping, and local lookup helpers |
| `src/anki_chinese/config.py` | Paths, deck metadata, stable IDs, field order |

## Provider boundaries

Audio generation is provider-neutral at the CLI and note-pipeline level. `audio/provider.py` defines the `TTSProvider` protocol; `audio/factory.py` builds concrete providers by name.

Current default behavior:

- Google Cloud Text-to-Speech is the default provider for single-character Mandarin and Cantonese audio.
- MiniMax is used for sentence audio by the application runtime.
- Providers expose a generation profile for each audio kind so state-aware
  planning can distinguish current files from files generated with old provider
  settings.

## Study target policy

The default learner track is mainland Mandarin with simplified characters for active study and traditional characters for passive recognition. Song planning uses `LyricSong.study_characters`, which conservatively maps contextual particle `著` to `着` while preserving lexical `著` words such as `著名` and `原著`.

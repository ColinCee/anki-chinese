# Reference

Run `uv run anki-chinese --help` and `uv run anki-chinese <command> --help` for
the authoritative option list.

## Core commands

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese` | Open the workbench in an interactive terminal; show help otherwise. |
| `uv run anki-chinese workbench` | Open the Textual workbench explicitly. |
| `uv run anki-chinese dashboard` | Compatibility alias for `workbench`. |
| `uv run anki-chinese doctor` | Read-only local readiness checks. |
| `uv run anki-chinese sync --dry-run` | Preview stale rebuild stages. |
| `uv run anki-chinese sync` | Execute needed `init`, `audio`, and `build` stages. |
| `uv run anki-chinese status` | Show coverage, validation, learned-character, and audio health. |
| `uv run anki-chinese frequency report` | Compare reviewed characters with the cached frequency list and show high-frequency deck gaps. |
| `uv run anki-chinese frequency refresh` | Explicitly build and cache the wordfreq-derived character list. |
| `uv run anki-chinese review` | Inspect notes flagged for manual correction. |
| `uv run anki-chinese card show 水` | Show saved note state. |
| `uv run anki-chinese card set 水 ...` | Write fields into the source deck export. |
| `uv run anki-chinese sentences` | Generate missing Gemini example sentences. |
| `uv run anki-chinese keywords` | Repair contextual meanings with Gemini. |
| `uv run anki-chinese audio` | Generate missing/stale audio. |
| `uv run anki-chinese audio-clean` | Preview orphaned generated audio cleanup. |
| `uv run anki-chinese build` | Primitive deck package build from enriched state. |
| `uv run anki-chinese songs learn` | Preferred human song-learning activation workflow. |
| `uv run anki-chinese activate chars ...` | Lower-level explicit live card activation. |

Legacy/primitives such as `init`, `build --full`, `songs activate`, and
top-level sentence audit aliases remain for compatibility, but day-to-day use
should start with the workbench, `doctor`, `sync`, `card`, and `songs learn`.

## Environment variables

| Variable | Required for | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | `sentences`, `keywords`, `sentences repair-confusers --apply` | Gemini API key. |
| `MINIMAX_API_KEY` | MiniMax audio | Sentence/audio API key. |
| `MINIMAX_API_HOST` | Optional MiniMax override | Use `https://api.minimaxi.com` for mainland-region keys. |
| `MINIMAX_TTS_MODEL` | Optional MiniMax override | Override the speech model. |
| `MINIMAX_MANDARIN_VOICE_ID` | Optional MiniMax override | Override Mandarin voice. |
| `MINIMAX_CANTONESE_VOICE_ID` | Optional MiniMax override | Override Cantonese voice. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google audio with service account | Path to service-account JSON. |
| `GOOGLE_TTS_ENDPOINT` | Optional Google override | Override REST endpoint. |
| `GOOGLE_TTS_MANDARIN_VOICE` | Optional Google override | Override Mandarin voice. |
| `GOOGLE_TTS_CANTONESE_VOICE` | Optional Google override | Override Cantonese voice. |
| `ANKICONNECT_API_KEY` | Optional AnkiConnect auth | Only if your local add-on requires a key. |

Google TTS uses Application Default Credentials, not an API-key environment
variable:

```bash
gcloud auth application-default login
# or
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

## Data layout

| Path | Purpose |
| --- | --- |
| `data/source/All Decks.apkg` | Source deck export parsed by `init`/`sync`; `card set` writes per-character edits here. |
| `data/manual/example_words.json` | Manual example-word data for enrichment. |
| `data/reference/` | Compact corpora such as HSK and CEDICT. |
| `data/songs/lyrics/` | Curated lyric markdown files. |
| `data/state/enriched.json` | Ignored generated note state used by status/generation/audio/build. |
| `data/state/pipeline.json` | Ignored local stage fingerprints used by `sync`, the workbench, and `doctor`. |
| `data/state/audio_manifest.json` | Ignored local audio provenance used for freshness checks. |
| `data/state/character_frequency.json` | Ignored local snapshot of the wordfreq-derived character-frequency list. |
| `data/build/decks/chinese_rsh.apkg` | Generated deck package. |
| `data/build/audio/` | Generated and sample audio. |
| `data/build/anki_backups/` | Live Anki activation/undo safety snapshots. |

Generated files under `data/build/` and derived state under `data/state/` are
ignored. Use `card set` or manual files under `data/manual/` for reviewable
content changes, then run `sync` to regenerate state.

The frequency snapshot is derived from `wordfreq`'s large Chinese word list,
which combines multiple sources and represents usage through approximately
2021. The snapshot scores each Hanzi occurrence in the top 100,000 Chinese
words. Reports never rebuild it automatically; use `frequency refresh`
explicitly when you want to regenerate it.

## Anki model

Stable identity lives in `src/anki_chinese/config.py`:

| Setting | Purpose |
| --- | --- |
| `DECK_ID` | Stable genanki deck ID. |
| `MODEL_ID` | Stable genanki note type/model ID. |
| `DECK_NAME` | Display name in Anki. |
| `MODEL_NAME` | Anki note type name. |
| `FIELDS` | Field order used by genanki and card templates. |

Do not change `DECK_ID`, `MODEL_ID`, note GUID behavior, or field order without
an explicit migration plan. Anki uses these to update existing notes instead of
creating duplicates.

Fields:

```text
Hanzi, Meaning, Pinyin, Jyutping,
MandarinAudio, CantoneseAudio, StrokeOrder, HeisigNum,
Lesson, Story, SentenceAudio, Sentence, SentencePinyin, SentenceEnglish
```

Card templates live in `src/anki_chinese/cards/`.

## Development

```bash
uv sync --group dev
uv run ruff check
uv run pyright
uv run pytest
uv run anki-chinese --help
uv run python -m anki_chinese.cli --help
```

If lyrics change, also run:

```bash
uv run anki-chinese songs verify
```

Keep provider-specific behavior behind `audio/provider.py` and
`audio/factory.py`; keep AnkiConnect behavior behind `activation/`.

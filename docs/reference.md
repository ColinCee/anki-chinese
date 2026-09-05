# Reference

`uv run anki-chinese <command> --help` owns commands and options;
[Workflows](workflows.md) owns task examples. `workbench` is the human entrypoint;
`dashboard` is its compatibility alias.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Sentence generation, meaning repair, and applied sentence repairs. |
| `MINIMAX_API_KEY` | MiniMax audio authentication. |
| `MINIMAX_API_HOST` | MiniMax endpoint override; use the endpoint matching your key's region. |
| `MINIMAX_TTS_MODEL` | Speech model override. |
| `MINIMAX_MANDARIN_VOICE_ID` | Mandarin voice override. |
| `MINIMAX_CANTONESE_VOICE_ID` | Cantonese voice override. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service-account JSON path, as an alternative to local ADC. |
| `GOOGLE_TTS_ENDPOINT` | Google TTS endpoint override. |
| `GOOGLE_TTS_MANDARIN_VOICE` | Mandarin voice override. |
| `GOOGLE_TTS_CANTONESE_VOICE` | Cantonese voice override. |
| `ANKICONNECT_API_KEY` | Local AnkiConnect key, when the add-on requires one. |

Provider defaults live in `src/anki_chinese/audio/google_tts.py` and `minimax.py`.
Google TTS uses Application Default Credentials or service-account authentication,
not a TTS API key:

```bash
gcloud auth application-default login
# or
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

The [provider decision](decisions/tts-provider-strategy.md) explains the default
Google-character/MiniMax-sentence split. Keep credentials private; see
[Security](../SECURITY.md).

## Data layout

Paths are defined in `src/anki_chinese/config.py`.

| Path | Owner / lifecycle |
| --- | --- |
| `data/source/characters.json` | Canonical authored RSH/custom records; edit with `card set` / `card add`. |
| `data/source/All Decks.apkg` | Legacy bootstrap/import input, not current live scheduling state. |
| `data/reference/` | Dictionary and vocabulary corpora. |
| `data/songs/lyrics/` | Curated lyric data, not repository documentation. |
| `data/state/enriched.json` | Working generated notes for generation/audio/build; not the canonical source. |
| `data/state/pipeline.json` | Local stage fingerprints. |
| `data/state/audio_manifest.json` | Audio provider/model/voice provenance. |
| `data/state/character_frequency.json` | Explicitly refreshed wordfreq-derived cache. |
| `data/build/decks/chinese_rsh.apkg` | Rebuilt package for manual Anki import. |
| `data/build/audio/` | Generated and sample audio. |
| `data/build/anki_backups/` | Live mutation/undo safety snapshots. |

Generated output and the listed state files are gitignored. Do not confuse
"generated" with "safe to discard": accepted generated text needs
[promotion into canonical records](workflows.md#generate-sentences-and-meanings),
and live undo snapshots may still be needed for recovery.

Frequency reports use cached wordfreq estimates plus current live review state,
not APKG suspension flags. `frequency refresh` rebuilds the cache explicitly;
reports do not refresh it implicitly. This is an estimate, not a proficiency score.

## Anki model

`src/anki_chinese/config.py` owns `DECK_ID`, `MODEL_ID`, and `FIELDS`;
`notes/model.py` projects records into that order, and `deck.py` owns note GUIDs
and template assembly. **Do not change IDs, GUID behavior, or field order without
an explicit migration.** This is what lets imports update rather than duplicate.

Each note produces Recognition and Listening cards. Recognition presents the
character and an optional unaided reading sentence. Listening withholds written
Chinese until the answer. Both backs prioritize the character followed by the
reading sentence. Meaning and usage sit below it, collapsed by default alongside
the other optional aids: sentence pinyin/translation, story, and stroke order.
Revealed vocabulary examples stay enlarged. Vocabulary and sentence practice
remain within these two cards, not separately scheduled notes.

Templates use authored content, not inferred word segmentation or generated
compound pronunciations. See [Customize card templates](workflows.md#customize-card-templates)
for the rebuild path and [Contributor code map](../CONTRIBUTING.md#where-to-make-a-change)
for code and test entry points.

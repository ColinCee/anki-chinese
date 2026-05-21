# CLI reference

Run `uv run anki-chinese --help` and `uv run anki-chinese <command> --help` for the authoritative option list. This page explains the command map and intended workflow.

## Core rebuild commands

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese init` | Parse `data/source/All Decks.apkg`, enrich notes, restore cached generated fields, and save `data/state/enriched.json`. |
| `uv run anki-chinese status` | Show field coverage, learned-character sentence/audio coverage, and validation issues. |
| `uv run anki-chinese review` | Inspect notes flagged for manual correction. |
| `uv run anki-chinese build` | Build `data/build/decks/chinese_rsh.apkg` from `data/state/enriched.json`. |
| `uv run anki-chinese build --full` | Run `init -> audio -> build` in one command. |
| `uv run anki-chinese build --full --skip-audio` | Run `init -> build` without audio generation. |

## Sentence and meaning commands

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese sentences` | Generate missing example sentences with Gemini. |
| `uv run anki-chinese sentences --char 早` | Generate for one character. |
| `uv run anki-chinese sentences --pick 3` | Generate candidates interactively and choose one. |
| `uv run anki-chinese sentences audit` | Report sentences with audio-confusing phonetic neighbors. |
| `uv run anki-chinese sentences repair-confusers` | Dry-run repair plan for sentences with phonetic confusers. |
| `uv run anki-chinese sentences repair-confusers --apply` | Regenerate and save replacements. |
| `uv run anki-chinese sentences-audit` | Backward-compatible top-level alias for `sentences audit`. |
| `uv run anki-chinese keywords` | Use Gemini to repair contextual meanings for notes that already have sentences. |

Sentence and keyword commands require `GEMINI_API_KEY`.

## Audio commands

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese test-tts --char 早 --provider google` | Smoke-test character audio using a provider. |
| `uv run anki-chinese test-tts --word 早上 --provider minimax` | Smoke-test arbitrary Mandarin text. |
| `uv run anki-chinese audio` | Generate missing audio for notes. |
| `uv run anki-chinese audio --limit 20` | Process the first 20 pending notes. |
| `uv run anki-chinese audio --start-rsh 500` | Start at a Heisig/RSH number. |
| `uv run anki-chinese audio --force` | Regenerate valid existing files. |
| `uv run anki-chinese audio-clean` | Dry-run removal of orphaned generated audio. |
| `uv run anki-chinese audio-clean --apply` | Delete orphaned generated audio files. |

The app default is Google for single-character audio and MiniMax for sentence audio. `test-tts` defaults to MiniMax unless `--provider` is passed.

## Song commands

Song analysis and activation query live Anki through AnkiConnect. A character
counts as active when any card for its live note is unsuspended.

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese songs analyze` | Analyze curated lyrics against live active characters and deck characters. |
| `uv run anki-chinese songs analyze --chars` | Include new-character lists in the output. |
| `uv run anki-chinese songs next` | Auto-select the first analyzed song with remaining in-deck characters. |
| `uv run anki-chinese songs next 学猫叫 --limit 20` | Preview next characters for a specific song. |
| `uv run anki-chinese songs activate --limit 20 --dry-run` | Preview live unsuspension for the auto-selected next song. |
| `uv run anki-chinese songs activate 学猫叫 --limit 20` | Write an undo snapshot, then unsuspend the selected song batch. |
| `uv run anki-chinese songs activate 学猫叫 --all --dry-run` | Preview all remaining in-deck characters for a song. |
| `uv run anki-chinese songs resuspend 学猫叫 --dry-run` | Preview resuspending cards from a mistaken song activation tag. |
| `uv run anki-chinese songs resuspend 学猫叫` | Resuspend tagged song cards and write an undo snapshot. |
| `uv run anki-chinese songs fetch "天后"` | Search lyrics.net.cn and save a selected lyric file. |
| `uv run anki-chinese songs fetch --url https://lyrics.net.cn/lyrics/58445` | Fetch a known lyrics.net.cn URL. |
| `uv run anki-chinese songs verify` | Verify frontmatter, numbering, duplicates, and local lyric integrity. |
| `uv run anki-chinese songs verify --online` | Also compare local lyrics to lyrics.net.cn. |

Run dry-runs before any real activation/resuspension. Real activation and resuspension commands write targeted undo snapshots under `data/build/anki_backups/`.

## Live activation commands

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese activate chars 内 合 哟 着 --dry-run` | Preview matching live Anki notes/cards for explicit characters. |
| `uv run anki-chinese activate chars 内 合 哟 着` | Write an undo snapshot, then unsuspend matching cards. |
| `uv run anki-chinese activate chars 内 合 哟 着 --tag batch::example` | Add a custom tag to activated notes. |

Activation requires Anki desktop to be open with AnkiConnect installed.

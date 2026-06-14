# CLI reference

Run `uv run anki-chinese --help` and `uv run anki-chinese <command> --help` for the authoritative option list. This page explains the command map and intended workflow.

## Core rebuild commands

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese init` | Parse `data/source/All Decks.apkg`, enrich notes, restore cached generated fields, and save `data/state/enriched.json`. |
| `uv run anki-chinese status` | Show field coverage, learned-character sentence/audio coverage, and validation issues. |
| `uv run anki-chinese review` | Inspect notes flagged for manual correction. |
| `uv run anki-chinese radicals` | Show primary-radical exposure from saved notes, with nicknames and examples. |
| `uv run anki-chinese radicals --min-seen 3` | Focus on radicals already seen often enough to study deliberately. |
| `uv run anki-chinese radicals --scope learned` | Analyze only learned characters from the source deck export. |
| `uv run anki-chinese build` | Build `data/build/decks/chinese_rsh.apkg` from `data/state/enriched.json`. |
| `uv run anki-chinese build --full` | Run `init -> audio -> build` in one command. |
| `uv run anki-chinese build --full --skip-audio` | Run `init -> build` without audio generation. |

## Card override commands

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese card show 水` | Show saved note state and any manual override for one character. |
| `uv run anki-chinese card show 水 --json` | Print the note and override as machine-readable JSON. |
| `uv run anki-chinese card set 水 --meaning "water; liquid"` | Write a manual meaning override. |
| `uv run anki-chinese card set 水 --sentence "我喝水。" --sentence-pinyin "wǒ hē shuǐ." --sentence-english "I drink water."` | Write manual sentence overrides and clear stale sentence audio. |

## Sentence and meaning commands

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese sentences` | Generate missing example sentences with Gemini. |
| `uv run anki-chinese sentences --char 早` | Generate for one character. |
| `uv run anki-chinese sentences --pick 3` | Generate candidates interactively and choose one; requires a terminal. |
| `uv run anki-chinese sentences audit` | Report sentences with audio-confusing phonetic neighbors. |
| `uv run anki-chinese sentences audit-pinyin` | Report sentence pinyin that disagrees with local pypinyin readings. |
| `uv run anki-chinese sentences repair-confusers` | Dry-run repair plan for sentences with phonetic confusers. |
| `uv run anki-chinese sentences repair-confusers --apply` | Regenerate and save replacements. |
| `uv run anki-chinese sentences-audit` | Backward-compatible top-level alias for `sentences audit`. |
| `uv run anki-chinese sentences-pinyin-audit` | Top-level alias for `sentences audit-pinyin`. |
| `uv run anki-chinese keywords` | Use Gemini to repair contextual meanings for notes that already have sentences. |

Sentence generation, repair, and keyword commands require `GEMINI_API_KEY`;
sentence audit commands run locally.

## Radical command

`radicals` uses the local HSK vocabulary metadata to group saved notes by each
character's primary radical. It is an exposure summary, not full component
decomposition. `--scope learned` uses learned characters from the source deck
export, so re-export the deck first if you need it to reflect recent live Anki
activation changes.

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
counts as active when any card for its live note is unsuspended. In
`songs analyze`, `Known` and `Learn` are study-progress columns based on
studied/reviewed characters, so activated but unseen cards still count as
characters to learn. `Activate` is the live activation delta: how many inactive
in-deck characters would be unsuspended for that song after earlier songs in the
displayed sequence.

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese songs analyze` | Analyze curated lyrics against live active, studied, and deck characters. |
| `uv run anki-chinese songs analyze --chars` | Include new-character lists in the output. |
| `uv run anki-chinese songs next` | Auto-select the first song with inactive in-deck characters. |
| `uv run anki-chinese songs next 学猫叫 --limit 20` | Preview next characters for a specific song. |
| `uv run anki-chinese songs activate --limit 20 --dry-run` | Preview live unsuspension for the auto-selected next song. |
| `uv run anki-chinese songs activate 学猫叫 --limit 20 --confirm` | Write an undo snapshot, then unsuspend the selected song batch. |
| `uv run anki-chinese songs activate 学猫叫 --all --dry-run` | Preview all remaining in-deck characters for a song. |
| `uv run anki-chinese songs resuspend 学猫叫 --dry-run` | Preview resuspending cards from a mistaken song activation tag. |
| `uv run anki-chinese songs resuspend 学猫叫 --confirm` | Resuspend tagged song cards and write an undo snapshot. |
| `uv run anki-chinese songs fetch "天后"` | Search lyrics.net.cn and save a selected lyric file. |
| `uv run anki-chinese songs fetch --url https://lyrics.net.cn/lyrics/58445` | Fetch a known lyrics.net.cn URL. |
| `uv run anki-chinese songs verify` | Verify frontmatter, numbering, duplicates, and local lyric integrity. |
| `uv run anki-chinese songs verify --online` | Also compare local lyrics to lyrics.net.cn. |

Run dry-runs before any real activation/resuspension. Live mutations require `--confirm`; without it, activation and resuspension commands preview only. Confirmed activation and resuspension commands write targeted undo snapshots under `data/build/anki_backups/`.

## Live activation commands

| Command | Purpose |
| --- | --- |
| `uv run anki-chinese activate chars 内 合 哟 着 --dry-run` | Preview matching live Anki notes/cards for explicit characters. |
| `uv run anki-chinese activate chars 内 合 哟 着 --confirm` | Write an undo snapshot, then unsuspend matching cards. |
| `uv run anki-chinese activate chars 内 合 哟 着 --tag batch::example --confirm` | Add a custom tag to activated notes. |

Activation requires Anki desktop to be open with AnkiConnect installed.

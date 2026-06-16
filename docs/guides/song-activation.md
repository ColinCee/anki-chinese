# Song activation guide

Use this workflow when you want the CLI to pick characters from curated song lyrics and unsuspend matching cards in your live Anki collection.

## Content rebuild vs live activation

| Workflow | Commands | What changes |
| --- | --- | --- |
| Content rebuild | `init`, `sentences`, `audio`, `build` | Note fields, generated audio, sentences, templates, generated `.apkg`. |
| Live activation | `activate`, `songs activate` | Suspended/unsuspended state and optional tags in the open Anki collection. |

Song planning and activation use live Anki state through AnkiConnect. Keep Anki open while running these commands.

## AnkiConnect setup

1. Open Anki desktop.
2. Go to **Tools -> Add-ons -> Get Add-ons...**.
3. Enter add-on code `2055492159`.
4. Restart Anki.
5. Keep Anki open while running activation commands.

Check AnkiConnect:

```bash
curl http://127.0.0.1:8765
```

Default AnkiConnect does not need an API key. If you configure one:

```bash
export ANKICONNECT_API_KEY="your-key"
```

## WSL with Windows Anki

If Anki runs on Windows and the CLI runs in WSL, `127.0.0.1` in WSL may not reach Windows Anki unless WSL uses mirrored networking.

First verify from Windows PowerShell:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765
```

If PowerShell works but WSL does not, enable mirrored networking in:

```text
%UserProfile%\.wslconfig
```

```ini
[wsl2]
networkingMode=mirrored
```

Restart WSL:

```powershell
wsl --shutdown
```

Leave AnkiConnect bound to `127.0.0.1` unless you intentionally expose it and have configured firewall/API-key protections.

## Safety workflow

Live activation mutates the open Anki collection.

1. Make sure Anki has a recent backup or you have another undo path.
2. Run the command with `--dry-run`.
3. Check requested characters, missing characters, already-active characters, card counts, and note counts.
4. Rerun with `--confirm` only when the preview is correct; the CLI writes a targeted undo snapshot before the real mutation.
5. If planning another song immediately afterward, query live Anki again instead of relying on an old `.apkg` export.

Dry-runs are previews, not backups. Without `--confirm`, live activation and resuspension commands preview only. Confirmed activation and resuspension commands write undo snapshots under `data/build/anki_backups/`.

## Study target and lyric variants

The default learner target is **mainland Mandarin with simplified characters**. Lyrics may contain traditional-script forms, especially from Taiwanese songs. Song planning uses normalized study characters so common particle uses such as `看著` plan against the mainland study form `着`.

This is context-sensitive:

| Lyric form | Study form | Notes |
| --- | --- | --- |
| `看著` | `看着` | Aspect/state particle `zhe`. |
| `带著` | `带着` | Same pronunciation, simplified study form. |
| `著名` | `著名` | Lexical `zhù`; simplified also uses `著`. |
| `原著` | `原著` | Lexical `zhù`; preserve. |

Runtime song commands remain deterministic and credential-free except for their local AnkiConnect query.

## Add or verify songs

Fetch lyrics from lyrics.net.cn:

```bash
uv run anki-chinese songs fetch "天后"
uv run anki-chinese songs fetch "我会等" --pick 1
uv run anki-chinese songs fetch --url https://lyrics.net.cn/lyrics/58445
```

Verify local lyric files:

```bash
uv run anki-chinese songs verify
```

Also compare against lyrics.net.cn:

```bash
uv run anki-chinese songs verify --online
```

`verify` checks frontmatter, numbering, duplicate titles, obvious markup/timestamps, and traditional characters in lyric text. Warnings do not fail the command; errors do.

The current curated corpus contains 30 lyric markdown files.

## Analyze the corpus

```bash
uv run anki-chinese songs analyze
```

This queries live Anki for:

- active characters, where any unsuspended card for a note counts as active
- studied characters, where any unsuspended non-new card for a note counts as studied
- all deck characters
- deck order

Then it computes a greedy song sequence and estimates remaining unstudied
in-deck characters. `Known` and `Learn` start from studied characters, not
merely active ones, so cards that have been unsuspended but not reviewed yet
still count as characters to learn. `Activate` shows the live activation delta
for each row after earlier songs in the displayed sequence.

Show character lists:

```bash
uv run anki-chinese songs analyze --chars
```

## Preview next characters

Auto-select the next song with inactive in-deck characters:

```bash
uv run anki-chinese songs next --limit 20
```

Preview a specific song:

```bash
uv run anki-chinese songs next 学猫叫 --limit 20
```

## Activate cards

Dry-run first:

```bash
uv run anki-chinese songs activate 学猫叫 --limit 20 --dry-run
uv run anki-chinese songs activate --limit 20 --dry-run
```

Activate after checking the preview:

```bash
uv run anki-chinese songs activate 学猫叫 --limit 20 --confirm
uv run anki-chinese songs activate --limit 20 --confirm
```

Activate all remaining in-deck characters for a song:

```bash
uv run anki-chinese songs activate 学猫叫 --all --dry-run
uv run anki-chinese songs activate 学猫叫 --all --confirm
```

The command:

- skips already-active characters
- skips non-RSH characters by default
- finds live Anki notes by the `Hanzi` field
- writes an undo snapshot under `data/build/anki_backups/` before real mutations
- unsuspends all cards for matching notes
- tags activated notes with `activated::song::<song title>` unless `--tag` is passed

## Recover from a mistaken song activation

If a song activation was a mistake, reverse it by the activation tag instead of
recomputing "new" characters. After activation, those cards are already active in
live Anki, so activation planning can no longer distinguish them from
intentionally active cards.

Dry-run first:

```bash
uv run anki-chinese songs resuspend 学猫叫 --dry-run
```

Resuspend after checking the preview:

```bash
uv run anki-chinese songs resuspend 学猫叫 --confirm
```

The command resolves the song the same way as `songs activate` and defaults to
the tag `activated::song::<song title>`. It writes an undo snapshot under
`data/build/anki_backups/` before any real mutation, suspends currently active
cards on the tagged notes, and removes the activation tag. Use `--keep-tag` to
leave the tag in place, or `--tag` to reverse a custom activation tag.

You can also undo from the saved snapshot directly. For song workflows, prefer
the high-level wrapper:

```bash
uv run anki-chinese songs undo 学猫叫
uv run anki-chinese songs undo 学猫叫 --confirm
```

Omit the song name to target the latest song activation/resuspension snapshot:

```bash
uv run anki-chinese songs undo
uv run anki-chinese songs undo --confirm
```

`songs undo` previews by default and queries current live suspended state, so
it skips cards that are already in the target state. A confirmed undo writes a
new `restore-*.json` safety snapshot before changing live Anki. By default it
also reverses the snapshot tag change: activation undo removes the activation
tag, and resuspension undo restores it when the original resuspend removed it.
Use `--keep-tag` to leave tags unchanged.

`activate undo` remains available as the lower-level form when you need to pick
a specific snapshot filename or path:

```bash
uv run anki-chinese activate snapshots list
uv run anki-chinese activate undo activation-YYYYMMDD-HHMMSS
```

## Inspect undo snapshots

Snapshot inspection reads local JSON files only; it does not connect to Anki or
mutate live cards.

```bash
uv run anki-chinese activate snapshots list
uv run anki-chinese activate snapshots show activation-YYYYMMDD-HHMMSS
uv run anki-chinese activate snapshots list --json
```

Use this after activation/resuspension to confirm the recorded operation,
characters, note/card counts, tag, and affected card IDs before deciding on any
manual recovery step.

## Manual activation

```bash
uv run anki-chinese activate chars 内 合 哟 着 --dry-run
uv run anki-chinese activate chars 内 合 哟 着 --confirm
uv run anki-chinese activate chars 内 合 哟 着 --tag batch::song-1 --confirm
```

## Troubleshooting

If activation fails, check:

- Anki desktop is open.
- AnkiConnect is installed and Anki was restarted.
- `curl http://127.0.0.1:8765` reaches AnkiConnect.
- WSL mirrored networking is enabled when using WSL with Windows Anki.
- `ANKICONNECT_API_KEY` is set if your AnkiConnect config requires it.

If `songs next` recommends characters that are already active, ensure AnkiConnect is talking to the collection you are studying and rerun the command.

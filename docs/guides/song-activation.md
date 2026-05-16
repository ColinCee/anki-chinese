# Song activation guide

Use this workflow when you want the CLI to pick characters from song lyrics and
unsuspend the matching cards in your live Anki collection.

## Two lanes

`anki-chinese` now has two separate workflows:

| Workflow | Command family | What it changes |
| --- | --- | --- |
| Content rebuild | `init`, `sentences`, `audio`, `build` | Fields, audio, sentences, templates, generated `.apkg` content |
| Live activation | `activate`, `songs activate` | Suspended/unsuspended state and optional tags in your open Anki collection |

Keep using `.apkg` export/import for rebuilding audio and sentences. Use
AnkiConnect only when you want to activate existing cards without manually
searching in Anki.

## One-time AnkiConnect setup

1. Open Anki desktop.
2. Go to **Tools -> Add-ons -> Get Add-ons...**.
3. Enter add-on code `2055492159`.
4. Restart Anki.
5. Keep Anki open while running activation commands.

Check it is running:

```bash
curl http://127.0.0.1:8765
```

Expected output:

```text
AnkiConnect
```

If you configure an AnkiConnect API key, expose it to the CLI:

```bash
export ANKICONNECT_API_KEY="your-key"
```

No API key is needed with the default AnkiConnect configuration.

## WSL with Windows Anki

If Anki runs on Windows and the CLI runs inside WSL, `127.0.0.1` in WSL may not
reach Windows Anki unless WSL uses mirrored networking. First verify AnkiConnect
works from Windows PowerShell:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765
```

If PowerShell works but WSL does not:

```bash
curl http://127.0.0.1:8765
```

enable WSL mirrored networking. Create or edit this Windows file:

```text
%UserProfile%\.wslconfig
```

Add:

```ini
[wsl2]
networkingMode=mirrored
```

Then restart WSL from Windows PowerShell:

```powershell
wsl --shutdown
```

Reopen your WSL shell and test again:

```bash
curl http://127.0.0.1:8765
```

Expected output:

```json
{"apiVersion": "AnkiConnect v.6"}
```

Leave AnkiConnect bound to its default `127.0.0.1`. Do not set
`webBindAddress` to `0.0.0.0` unless you explicitly want to expose it beyond
localhost and have configured firewall/API-key protections.

## Song workflow, study target, and lyric variants

This repo's default learner target is **mainland Mandarin with simplified
characters**.

That matters because some popular Taiwanese songs in `data/songs/lyrics/` use
traditional-script forms such as `著` inside otherwise familiar Mandarin lines.
For mainland study, prioritize the simplified form when you activate or review
cards.

Examples:

| Lyric form | Mainland study form | Pronunciation |
| --- | --- | --- |
| `看著` | `看着` | `kàn zhe` |
| `带著` | `带着` | `dài zhe` |
| `贪恋著` | `贪恋着` | `tān liàn zhe` |

The pronunciation does **not** change in those cases. Only the written form
changes for your default study target.

Important: this is context-sensitive. Lexical words such as `著名`, `显著`, and
`著作` keep `著` and should not be rewritten blindly.

Song planning now normalizes the common aspect-particle use `著 -> 着`, so
planning and activation target the mainland simplified form by default. That
normalization is conservative: lexical words such as `著名`, `显著`, and `著作`
are left untouched.

Analyze all lyric files against your latest exported deck snapshot:

```bash
uv run anki-chinese songs analyze
```

## Adding new songs

Fetch lyrics directly from lyrics.net.cn:

```bash
# Search by song name
uv run anki-chinese songs fetch "天后"

# Pick from multiple results
uv run anki-chinese songs fetch "我会等" --pick 1

# Direct URL (if you already found the page)
uv run anki-chinese songs fetch --url https://lyrics.net.cn/lyrics/58445
```

After adding songs, validate and re-analyze:

```bash
# Check all lyrics for correctness (simplified Chinese, no HTML, no duplicates)
uv run anki-chinese songs verify

# Re-run greedy analysis to see new optimal order
uv run anki-chinese songs analyze

# Renumber files to match the new greedy sequence
```

Preview the next characters for the next song in the greedy analysis sequence:

```bash
uv run anki-chinese songs next
```

Omitting the song skips any analyzed songs with `0` new in-deck characters and
selects the first song that still needs new RSH cards.

Preview the next characters for a specific song:

```bash
uv run anki-chinese songs next 学猫叫 --limit 20
```

This queries live Anki through AnkiConnect to decide which characters are already
active and which characters exist in the RSH deck.

Dry-run the live Anki activation:

```bash
uv run anki-chinese songs activate 学猫叫 --limit 20 --dry-run
```

Or dry-run the auto-selected next song:

```bash
uv run anki-chinese songs activate --limit 20 --dry-run
```

Actually unsuspend those cards:

```bash
uv run anki-chinese songs activate 学猫叫 --limit 20
```

For the auto-selected next song:

```bash
uv run anki-chinese songs activate --limit 20
```

The command:

- skips characters already active in live Anki
- skips Non-RSH characters by default
- finds matching live Anki notes by the `Hanzi` field
- unsuspends all cards for those notes
- tags activated notes with `activated::song::<song title>` unless you pass `--tag`

Activate all remaining in-deck characters for a song:

```bash
uv run anki-chinese songs activate 学猫叫 --all --dry-run
uv run anki-chinese songs activate 学猫叫 --all
```

## Manual activation

If you already know exactly which characters to activate:

```bash
uv run anki-chinese activate chars 内 合 哟 着 --dry-run
uv run anki-chinese activate chars 内 合 哟 着
```

Add a custom tag:

```bash
uv run anki-chinese activate chars 内 合 哟 着 --tag batch::song-1
```

## Recommended routine

1. Open Anki with AnkiConnect running.
2. Run `uv run anki-chinese songs analyze`.
3. Run `uv run anki-chinese songs next --limit 20`.
4. Run `uv run anki-chinese songs activate --limit 20 --dry-run`.
5. If the dry-run looks right and you have a backup/undo path, rerun without `--dry-run`.

## Troubleshooting

If activation fails with an AnkiConnect availability error, check:

- Anki desktop is open.
- The AnkiConnect add-on is installed and Anki has been restarted.
- `curl http://127.0.0.1:8765` prints `AnkiConnect`.
- If using Windows Anki from WSL, mirrored networking is enabled and WSL has been restarted.
- If you enabled an API key in AnkiConnect, `ANKICONNECT_API_KEY` is set.

If `songs next` recommends characters that are already active in live Anki,
check that AnkiConnect is talking to the collection you are studying and rerun
the planning command.

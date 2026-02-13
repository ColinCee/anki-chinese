# anki-chinese

Generate Anki decks for learning Mandarin + Cantonese Chinese using the
**Heisig "Remembering Simplified Hanzi"** (RSH) method.

Parses an old Anki deck export, enriches it with pinyin, jyutping, and
Azure TTS audio, then builds a clean `.apkg` file you can import into Anki.

---

## Quick start

### 1. Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
- **Anki** desktop app (to import the generated deck)

### 2. Install

```bash
git clone <repo-url> && cd anki-chinese
uv sync
```

### 3. Generate your deck

```bash
# Parse + enrich your old deck export
uv run anki-chinese init

# Build the .apkg file
uv run anki-chinese build
```

The deck is written to `output/chinese_rsh.apkg`.
Open it in Anki to import.

---

## Commands

There are only 4 commands. Run any command with `--help` to see its options.

### `init` — Parse & enrich

Parses `data/All Decks.txt` (old Anki text export) and fills in missing
pinyin, jyutping, and example words. Saves structured data to
`data/enriched.json`.

```bash
uv run anki-chinese init
```

| Flag | What it does |
| --- | --- |
| `-i`, `--input PATH` | Use a different source file (default: `data/All Decks.txt`) |
| `--skip-examples` | Don't look up example words |

### `audio` — Generate pronunciation audio

Generates Mandarin and Cantonese audio using Azure Speech Service.
Requires Azure credentials in `.env` (see [Azure setup](#azure-tts-setup)
below).

```bash
# Generate audio for all notes
uv run anki-chinese audio

# Test with just 10 notes first
uv run anki-chinese audio --limit 10

# Regenerate audio for one character
uv run anki-chinese audio --char 早 --force
```

| Flag | What it does |
| --- | --- |
| `-c`, `--char 字` | Only generate for this one character |
| `-l`, `--limit N` | Process only the first N notes |
| `-f`, `--force` | Regenerate files that already exist |

### `build` — Build the .apkg deck

Builds the Anki package from `data/enriched.json`.

```bash
# Just build from existing enriched data
uv run anki-chinese build

# Or run the full pipeline in one shot (init → audio → build)
uv run anki-chinese build --full --skip-audio
```

| Flag | What it does |
| --- | --- |
| `--full` | Run the complete pipeline: init → audio → build |
| `--skip-audio` | With `--full`, skip audio generation |
| `--skip-examples` | With `--full`, skip example-word lookup |
| `--audio-limit N` | With `--full`, generate audio for only N notes |

### `status` — Coverage & validation

Shows how complete your data is and checks for problems.

```bash
uv run anki-chinese status
```

No flags — just run it.

---

## Azure TTS setup

Audio generation is **optional**. The deck works fine without it.
If you want pronunciation audio:

1. Create an [Azure Speech Service](https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices)
   resource (free tier gives 500K characters/month)
1. Copy your key and region:

```bash
cp .env.example .env
```

1. Edit `.env`:

```dotenv
AZURE_SPEECH_KEY=your-actual-key
AZURE_SPEECH_REGION=eastus
```

1. Generate audio:

```bash
# Start small to verify it works
uv run anki-chinese audio --limit 5

# Then do everything
uv run anki-chinese audio
```

Audio files are saved to `media/generated/` and bundled into the `.apkg`
on the next `build`.

---

## Typical workflow

```bash
1.  uv run anki-chinese init          # parse + enrich
2.  uv run anki-chinese status        # check coverage
3.  edit data/overrides.json           # fix any flagged characters
4.  uv run anki-chinese init          # re-run to apply fixes
5.  uv run anki-chinese audio         # generate TTS (optional)
6.  uv run anki-chinese build         # produce .apkg
7.  open output/chinese_rsh.apkg      # import into Anki
```

Or, do it all in one shot:

```bash
uv run anki-chinese build --full --skip-audio
```

---

## Customization

Everything is designed to be easily changed.

### Change a character's data

Edit `data/overrides.json`. Any field can be overridden per character:

```json
{
  "行": { "pinyin": "xíng", "jyutping": "haang4", "keyword": "go" },
  "了": { "pinyin": "le" }
}
```

Then re-run `init` to apply.

### Change card appearance

Edit the files in `templates/`:

| File | Purpose |
| --- | --- |
| `style.css` | Colors, fonts, layout |
| `recognition_front.html` | Recognition card front (shows hanzi) |
| `recognition_back.html` | Recognition card back (shows everything) |
| `recall_front.html` | Recall card front (shows keyword) |
| `recall_back.html` | Recall card back (shows hanzi + everything) |

Then re-run `build`.

### Change fields or deck settings

Edit `src/anki_chinese/config.py`:

- `FIELDS` — add/remove/reorder note fields
- `DECK_NAME` — change the deck name in Anki
- `MANDARIN_VOICE` / `CANTONESE_VOICE` — change Azure TTS voices

> ⚠️ Do not change `MODEL_ID` or `DECK_ID` after your first Anki import —
> it will create duplicates.

### Add example words

Populate `data/example_words.json`:

```json
{
  "早": { "word": "早上", "meaning": "morning" },
  "大": { "word": "大学", "meaning": "university" }
}
```

---

## Project structure

```text
anki-chinese/
├── data/
│   ├── All Decks.txt          # Old Anki export (input)
│   ├── enriched.json          # Enriched data (generated)
│   ├── overrides.json         # Manual corrections
│   └── example_words.json     # Example word data
├── media/
│   └── generated/             # TTS audio files (generated)
├── output/
│   └── chinese_rsh.apkg       # The Anki deck (generated)
├── templates/                 # Card HTML/CSS/JS
├── src/anki_chinese/          # Python source
│   ├── cli.py                 # CLI commands
│   ├── config.py              # Paths, IDs, field order
│   ├── models.py              # CharacterNote dataclass
│   ├── parser.py              # Old deck parser
│   ├── enrich.py              # Enrichment pipeline
│   ├── pinyin_lookup.py       # Pinyin via pypinyin
│   ├── jyutping_lookup.py     # Jyutping via ToJyutping
│   ├── examples.py            # Example word lookup
│   ├── tts.py                 # Azure TTS with SSML
│   └── deck.py                # genanki deck builder
├── .env                       # Azure credentials (not committed)
└── pyproject.toml
```

---

## Re-importing into Anki

The deck uses **stable GUIDs** based on each character. This means you can
regenerate and re-import the `.apkg` as many times as you want — Anki will
**update existing notes** instead of creating duplicates. Your review
history is preserved.

# anki-chinese

Build a regenerable Anki deck for Mandarin study with Cantonese support.

Parses an Anki `.apkg` export, enriches each character with readings and example words, optionally generates TTS audio, and outputs a clean `.apkg` for Anki.

## Project goals

- **Character-first learning** across the RSH book
- **Mandarin reading + pronunciation** with Cantonese as support
- **Common usage phrase** on each listening card
- **Explicit example-word pinyin** so audio uses the intended reading
- **Regenerable deck** without losing Anki review history

## Quick start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Anki desktop

### Install

```bash
git clone <repo-url> && cd anki-chinese
uv sync
```

### Minimal run (no audio)

```bash
uv run anki-chinese init
uv run anki-chinese build
```

Output: `data/build/decks/chinese_rsh.apkg`

## Core workflow

```bash
uv run anki-chinese init       # 1. Parse source export + enrich
uv run anki-chinese status     # 2. Inspect coverage and validation
uv run anki-chinese review     # 3. Inspect notes flagged for correction
uv run anki-chinese audio      # 4. Generate TTS audio (optional)
uv run anki-chinese build      # 5. Create final .apkg
```

- `init` must run before `build` (produces `data/state/enriched.json`)
- `audio` is optional and network-bound
- Default source: `data/source/All Decks.apkg`
- Example words auto-generate when missing; manual overrides from `data/manual/example_words.json`
- Stable GUIDs per character — re-importing updates notes, never duplicates

```bash
# Smoke-test audio
uv run anki-chinese test-tts --char 早
uv run anki-chinese test-tts --word 早上
```

## Song learning and activation

The `.apkg` import/export workflow remains the source of truth for rebuildable card
content. Live study-state changes, such as unsuspending a batch of existing cards, use
AnkiConnect while Anki is running.

Default learner target: **mainland Mandarin with simplified characters**.
Traditional forms that appear in Taiwanese songs are useful recognition context,
but they are not the primary study target for this repo.
Song planning now normalizes the common lyric particle `著` to the mainland
study form `着`, and the audited lyric files have been cleaned accordingly.

```bash
uv run anki-chinese songs analyze
uv run anki-chinese songs next 学猫叫 --limit 20
uv run anki-chinese songs activate 学猫叫 --limit 20 --dry-run
uv run anki-chinese songs activate 学猫叫 --limit 20

uv run anki-chinese songs fetch "天后"              # search lyrics.net.cn
uv run anki-chinese songs fetch --url https://lyrics.net.cn/lyrics/58445
uv run anki-chinese songs verify                    # validate all lyric files

uv run anki-chinese activate chars 内 合 哟 着 --dry-run
uv run anki-chinese activate chars 内 合 哟 着
```

Install the AnkiConnect add-on in Anki with code `2055492159`, keep Anki open, then run
activation commands. Lyrics live in `data/songs/lyrics/`. See the
[Song Activation guide](docs/guides/song-activation.md) for setup and the full workflow.

Use `uv run anki-chinese <command> --help` for full flags and options.

## Learning flow

The deck is opinionated:

- `recall_front` is listening-first: Mandarin audio + optional example phrase
- Keyword text intentionally removed from the listening front
- Example selection: manual first → HSK/CEDICT auto-pick → blank
- Pronunciation from `Pinyin` and `Jyutping`, not the English keyword

## Docs

See [docs/](docs/README.md) for full documentation:

- **[Development](docs/guides/development.md)** — repo layout, testing strategy, validation
- **[Customization](docs/guides/customization.md)** — overrides, card templates, example words
- **[Mainland Mandarin Study Target](docs/guides/mainland-mandarin.md)** — simplified-first policy, traditional recognition, Taiwanese song handling
- **[Song Activation](docs/guides/song-activation.md)** — AnkiConnect setup and song-based unsuspending
- **[TTS Setup](docs/guides/tts-setup.md)** — Google Cloud + MiniMax API setup
- **[ADR-001: Sentences](docs/decisions/ADR-001-sentence-generation.md)** — Gemini generation pipeline
- **[ADR-002: TTS Strategy](docs/decisions/ADR-002-tts-provider-strategy.md)** — hybrid provider approach
- **[ADR-003: Study Target Policy](docs/decisions/ADR-003-study-target-policy.md)** — mainland Mandarin, simplified-first rollout plan
- **[TTS Research](docs/research/tts-providers.md)** — full provider comparison

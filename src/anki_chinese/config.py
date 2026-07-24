"""
Central configuration — change IDs, paths, field order here.

Model and deck IDs are hardcoded random integers. genanki uses these to track
identity across regenerations. Do NOT change them after your first import or
Anki will treat the next import as a brand new deck/model.
"""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent.parent

CARDS_DIR = PACKAGE_DIR / "cards"

DATA_DIR = PROJECT_ROOT / "data"
SOURCE_DATA_DIR = DATA_DIR / "source"
MANUAL_DATA_DIR = DATA_DIR / "manual"
REFERENCE_DATA_DIR = DATA_DIR / "reference"
STATE_DATA_DIR = DATA_DIR / "state"
BUILD_DATA_DIR = DATA_DIR / "build"
SONG_DATA_DIR = DATA_DIR / "songs"
BUILD_AUDIO_DIR = BUILD_DATA_DIR / "audio"
ANKI_BACKUP_DIR = BUILD_DATA_DIR / "anki_backups"
GENERATED_AUDIO_DIR = BUILD_AUDIO_DIR / "generated"
SAMPLE_AUDIO_DIR = BUILD_AUDIO_DIR / "samples"
DECK_OUTPUT_DIR = BUILD_DATA_DIR / "decks"

SOURCE_DECK_PATH = SOURCE_DATA_DIR / "All Decks.apkg"
CANONICAL_SOURCE_PATH = SOURCE_DATA_DIR / "characters.json"
ENRICHED_PATH = STATE_DATA_DIR / "enriched.json"
PIPELINE_STATE_PATH = STATE_DATA_DIR / "pipeline.json"
AUDIO_MANIFEST_PATH = STATE_DATA_DIR / "audio_manifest.json"
CHARACTER_FREQUENCY_PATH = STATE_DATA_DIR / "character_frequency.json"
SONG_LYRICS_DIR = SONG_DATA_DIR / "lyrics"
ANKICONNECT_URL = "http://127.0.0.1:8765"

# ── Data sources ─────────────────────────────────────────────────────
HSK_VOCAB_PATH = REFERENCE_DATA_DIR / "hsk_complete.min.json"
# CC-CEDICT: auto-downloaded on first use by data_sources._cedict
CEDICT_PATH = REFERENCE_DATA_DIR / "cedict_1_0_ts_utf-8_mdbg.txt"
# SUBTLEX-CH: optional — place SUBTLEX_CH.xlsx in data/reference/ to enable frequency scoring
# Download: https://crr.ugent.be/subtlex-ch/SUBTLEX_CH_131_30.zip
SUBTLEX_PATH = REFERENCE_DATA_DIR / "SUBTLEX_CH.xlsx"

# ── genanki IDs (generated once, never change) ────────────────────────
MODEL_ID = 1_704_328_571  # Unique ID for the note type
DECK_ID = 1_704_328_572  # Unique ID for the deck

# ── Deck metadata ─────────────────────────────────────────────────────
DECK_NAME = "Chinese"
MODEL_NAME = "Chinese RSH"

# ── Field order (index into the fields list) ──────────────────────────
# If you add/remove/reorder fields, update this AND the FIELDS list AND
# the card files under `src/anki_chinese/cards/`. The CLI will catch mismatches.
FIELDS = [
    "Hanzi",
    "Meaning",
    "Pinyin",
    "Jyutping",
    "MandarinAudio",
    "CantoneseAudio",
    "StrokeOrder",
    "HeisigNum",
    "Lesson",
    "Story",
    "SentenceAudio",
    "Sentence",
    "SentencePinyin",
    "SentenceEnglish",
]

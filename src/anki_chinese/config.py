"""
Central configuration — change IDs, paths, field order here.

Model and deck IDs are hardcoded random integers. genanki uses these to track
identity across regenerations. Do NOT change them after your first import or
Anki will treat the next import as a brand new deck/model.
"""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MEDIA_DIR = PROJECT_ROOT / "media"
GENERATED_MEDIA_DIR = MEDIA_DIR / "generated"
TEST_MEDIA_DIR = MEDIA_DIR / "test"
TEMPLATE_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "output"

SOURCE_DECK_PATH = DATA_DIR / "Exported-deck.txt"
# Backward-compatible alias for existing imports.
OLD_DECK_PATH = SOURCE_DECK_PATH
OVERRIDES_PATH = DATA_DIR / "overrides.json"
ENRICHED_PATH = DATA_DIR / "enriched.json"

# ── genanki IDs (generated once, never change) ────────────────────────
MODEL_ID = 1_704_328_571  # Unique ID for the note type
DECK_ID = 1_704_328_572  # Unique ID for the deck

# ── Deck metadata ─────────────────────────────────────────────────────
DECK_NAME = "Chinese"
MODEL_NAME = "Chinese RSH"

# ── Field order (index into the fields list) ──────────────────────────
# If you add/remove/reorder fields, update this AND the FIELDS list AND
# the card templates.  The CLI 'validate' command will catch mismatches.
FIELDS = [
    "Hanzi",
    "Keyword",
    "Pinyin",
    "Jyutping",
    "MandarinAudio",
    "CantoneseAudio",
    "ExampleWord",
    "ExampleMeaning",
    "ExampleAudio",
    "StrokeOrder",
    "HeisigNum",
    "Lesson",
    "Mnemonic",
]

# ── Azure TTS ─────────────────────────────────────────────────────────
MANDARIN_VOICE = "zh-CN-XiaoyiNeural"
CANTONESE_VOICE = "zh-HK-HiuGaaiNeural"

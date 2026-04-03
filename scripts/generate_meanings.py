"""
One-off script: generate full meaning definitions for all notes.

Composes rich meanings from CEDICT core definitions + Gemini contextual analysis.
Output format examples:
  - Simple:   "big, large"
  - Compound:  "silver; in 银行: bank"
  - Particle:  "aspect particle (-ing); marks ongoing action"
  - Phonetic:  "phonetic; in 俄罗斯: Russia"

Usage:
    python scripts/generate_meanings.py [--limit N] [--offset N] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

MODEL = "gemini-3.1-flash-lite-preview"
BATCH_SIZE = 20
RATE_LIMIT_SLEEP = 15
INTER_REQUEST_DELAY = 0.5

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED_PATH = PROJECT_ROOT / "data" / "state" / "enriched.json"
CEDICT_PATH = PROJECT_ROOT / "data" / "reference" / "cedict_1_0_ts_utf-8_mdbg.txt"

# Add src/ to path so we can import the shared CEDICT module
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from anki_chinese.data_sources._cedict import lookup_char_defs  # noqa: E402


# -- Pydantic schemas --------------------------------------------------------


class _MeaningEntry(BaseModel):
    hanzi: str = Field(description="The Chinese character")
    meaning: str = Field(
        description="Full English meaning: core dictionary definition + "
        "contextual usage if different. Examples: "
        "'big, large' or 'silver; in 银行: bank' or "
        "'aspect particle (-ing); marks ongoing action'"
    )
    english: str = Field(
        description="The English translation of the sentence, corrected for "
        "grammar. Fix articles (a/an), verb forms, prepositions, "
        "subject-verb agreement. Do NOT translate measure words literally. "
        "Return the original if it is already correct."
    )


class _MeaningBatchSchema(BaseModel):
    entries: list[_MeaningEntry]


# -- Gemini helpers -----------------------------------------------------------

SYSTEM_INSTRUCTION = """\
You are a Mandarin Chinese expert creating flashcard definitions for an adult learner.

For each character below you receive:
- The character
- Its dictionary definitions (from CC-CEDICT)
- The sentence it appears in
- The English translation of that sentence

Your job: write a concise English meaning for the CHARACTER (not the compound word).

FORMAT RULES:
1. If the character's core meaning matches its usage in the sentence:
   → Just give the core meaning: "big, large" or "water, liquid"

2. If the character appears in a compound where the compound meaning differs from
   the character's core meaning:
   → "core meaning; in [compound]: compound meaning"
   → Example: "silver; in 银行: bank" or "west; in 西瓜: watermelon"
   → The compound meaning should be the natural English translation of the
     compound word, NOT an explanation of why the character contributes to it.
   → NEVER cite the character itself as a compound. Wrong: "in 包: bag". 
     Instead list both meanings directly: "to wrap; bag"

3. For grammatical particles and function words:
   → Describe the function: "aspect particle (-ing); marks ongoing action"

4. For purely phonetic uses (transliterations):
   → "phonetic; in [compound]: transliterated word"
   → Example: "phonetic; in 俄罗斯: Russia"

5. If the character has multiple meanings at this pronunciation, list the most
   relevant ones separated by semicolons: "to trap; sleepy"

GUIDELINES:
- Keep it concise (under 60 characters ideally)
- Use the character's CORE meaning first, then contextual if needed
- Only use dictionary definitions that match the given pinyin pronunciation
- Don't repeat the sentence translation
- Lowercase except proper nouns
"""


def call_gemini(
    client: genai.Client,
    contents: list[types.Content],
    config: types.GenerateContentConfig,
) -> str | None:
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model=MODEL, contents=contents, config=config,
            )
            time.sleep(INTER_REQUEST_DELAY)
            return resp.text or None
        except Exception as exc:
            if "429" in str(exc):
                logger.warning("  Rate limited, sleeping %ds (attempt %d)", RATE_LIMIT_SLEEP, attempt + 1)
                time.sleep(RATE_LIMIT_SLEEP)
                continue
            logger.error("  Gemini API error: %s", exc)
            return None
    return None


def process_batch(
    client: genai.Client,
    batch: list[dict],
) -> dict[str, str]:
    """Send a batch to Gemini, return {hanzi: meaning}."""
    lines = []
    for i, note in enumerate(batch, 1):
        h = note["hanzi"]
        pinyin = note.get("pinyin", "")
        defs = lookup_char_defs(h, CEDICT_PATH, pinyin=pinyin)
        defs_str = "; ".join(defs[:5]) if defs else "(no dictionary entry)"
        lines.append(
            f"{i}. {h} (pinyin: {pinyin})\n"
            f"   Dictionary: {defs_str}\n"
            f"   Sentence: {note['sentence']}\n"
            f"   English: {note['sentence_english']}"
        )
    prompt = "\n".join(lines)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=_MeaningBatchSchema,
        temperature=0.0,
    )
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

    resp = call_gemini(client, contents, config)
    if not resp:
        return {}

    parsed = _MeaningBatchSchema.model_validate_json(resp)
    return {e.hanzi: (e.meaning, e.english) for e in parsed.entries}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate full meaning definitions")
    parser.add_argument("--limit", type=int, default=0, help="Max notes to process")
    parser.add_argument("--offset", type=int, default=0, help="Start from note N")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    notes = json.loads(ENRICHED_PATH.read_text(encoding="utf-8"))
    targets = [n for n in notes if n.get("sentence")]

    if args.offset:
        targets = targets[args.offset:]
    if args.limit:
        targets = targets[: args.limit]

    logger.info("Processing %d notes ...\n", len(targets))

    updated_meaning = 0
    updated_english = 0
    note_map = {n["hanzi"]: n for n in notes}

    for start in range(0, len(targets), BATCH_SIZE):
        batch = targets[start : start + BATCH_SIZE]
        end = min(start + BATCH_SIZE, len(targets))
        logger.info("[%d/%d] Processing batch ...", end, len(targets))

        results = process_batch(client, batch)

        for note in batch:
            hanzi = note["hanzi"]
            if hanzi not in results:
                continue
            new_meaning, new_english = results[hanzi]
            real_note = note_map[hanzi]

            old_meaning = real_note.get("meaning", "")
            if new_meaning and new_meaning != old_meaning:
                logger.info("  %s: meaning '%s' → '%s'", hanzi, old_meaning, new_meaning)
                real_note["meaning"] = new_meaning
                updated_meaning += 1

            old_english = real_note.get("sentence_english", "")
            if new_english and new_english != old_english:
                logger.info("  %s: english '%s' → '%s'", hanzi, old_english[:40], new_english[:40])
                real_note["sentence_english"] = new_english
                updated_english += 1

    logger.info("\nUpdated %d meanings, %d English translations", updated_meaning, updated_english)

    if not args.dry_run:
        ENRICHED_PATH.write_text(
            json.dumps(notes, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info("Saved → %s", ENRICHED_PATH)
    else:
        logger.info("(dry run — not saved)")


if __name__ == "__main__":
    main()

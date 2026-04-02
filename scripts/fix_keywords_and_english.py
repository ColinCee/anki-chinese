"""
One-off script: regenerate keyword + English translation for all notes.

Sends batches of (hanzi, sentence, sentence_pinyin) to Gemini asking for
the contextual keyword and an English translation that incorporates it.
For any result where the keyword doesn't appear in the English, does a
multi-turn follow-up asking Gemini to fix the translation.

Usage:
    GEMINI_API_KEY=... python scripts/fix_keywords_and_english.py [--limit N] [--dry-run]
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

ENRICHED_PATH = Path(__file__).resolve().parents[1] / "data" / "state" / "enriched.json"


# -- Pydantic schemas --------------------------------------------------------

class _NoteEntry(BaseModel):
    hanzi: str = Field(description="The Chinese character")
    keyword: str = Field(
        description="The contextual English meaning of the character "
        "as used in the sentence (1-3 words, lowercase)"
    )
    english: str = Field(
        description="Natural English translation of the full sentence. "
        "Must contain the keyword word."
    )
    character_pinyin: str = Field(
        description="The pinyin of the target character as used in this "
        "sentence (single syllable with tone mark, e.g. 'shuǐ', 'xiāo')"
    )


class _BatchSchema(BaseModel):
    entries: list[_NoteEntry]


class _FixEntry(BaseModel):
    hanzi: str
    english: str


class _FixBatchSchema(BaseModel):
    entries: list[_FixEntry]


# -- Gemini helpers -----------------------------------------------------------

SYSTEM_INSTRUCTION = (
    "You are a Mandarin Chinese expert creating flashcard data for an adult learner.\n\n"
    "For each character below you will receive the character, its sentence, and pinyin.\n"
    "Return:\n"
    "1. keyword: the English meaning of the target character as used in this sentence "
    "(1-3 words, lowercase)\n"
    "2. english: a natural English translation of the full sentence that contains "
    "the keyword word\n\n"
    "The keyword MUST appear literally as a word in the English translation."
)


def call_gemini(
    client: genai.Client,
    contents: list[types.Content],
    config: types.GenerateContentConfig,
) -> str | None:
    """Make a Gemini API call with rate-limit retry."""
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
) -> dict[str, tuple[str, str, str]]:
    """Send a batch to Gemini, return {hanzi: (keyword, english, character_pinyin)}."""
    lines = []
    for i, note in enumerate(batch, 1):
        lines.append(
            f"{i}. {note['hanzi']} — sentence: {note['sentence']} "
            f"(pinyin: {note['sentence_pinyin']})"
        )
    prompt = "\n".join(lines)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=_BatchSchema,
        temperature=0.0,
    )
    history = [types.Content(role="user", parts=[types.Part(text=prompt)])]

    resp = call_gemini(client, history, config)
    if not resp:
        return {}

    parsed = _BatchSchema.model_validate_json(resp)
    results = {e.hanzi: (e.keyword, e.english, e.character_pinyin) for e in parsed.entries}
    history.append(types.Content(role="model", parts=[types.Part(text=resp)]))

    # Check for mismatches and fix via follow-up turn
    mismatches = []
    for entry in parsed.entries:
        if entry.keyword.lower() not in entry.english.lower():
            mismatches.append(entry)

    if mismatches:
        fix_lines = []
        for m in mismatches:
            fix_lines.append(
                f"- {m.hanzi}: keyword '{m.keyword}' is NOT in the English "
                f"'{m.english}'. Rewrite the English translation so it "
                f"naturally contains the word '{m.keyword}'."
            )
        fix_prompt = (
            "Some translations don't contain their keyword. "
            "Fix ONLY these English translations:\n" + "\n".join(fix_lines)
        )
        history.append(types.Content(role="user", parts=[types.Part(text=fix_prompt)]))

        fix_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_FixBatchSchema,
            temperature=0.0,
        )
        fix_resp = call_gemini(client, history, fix_config)
        if fix_resp:
            fixed = _FixBatchSchema.model_validate_json(fix_resp)
            for entry in fixed.entries:
                if entry.hanzi in results:
                    old_kw, _, old_py = results[entry.hanzi]
                    results[entry.hanzi] = (old_kw, entry.english, old_py)
                    logger.info("  Fixed: %s → %s", entry.hanzi, entry.english)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix keywords and English translations")
    parser.add_argument("--limit", type=int, default=0, help="Max notes to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    parser.add_argument("--offset", type=int, default=0, help="Start from note N")
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

    logger.info("Processing %d notes ...", len(targets))

    updated_kw = 0
    updated_en = 0
    updated_py = 0
    fixed_mismatches = 0
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
            new_kw, new_en, new_py = results[hanzi]

            real_note = note_map[hanzi]
            if new_kw and new_kw != real_note.get("keyword"):
                logger.info("  %s: keyword '%s' → '%s'", hanzi, real_note.get("keyword"), new_kw)
                real_note["keyword"] = new_kw
                updated_kw += 1
            if new_en and new_en != real_note.get("sentence_english"):
                real_note["sentence_english"] = new_en
                updated_en += 1
            if new_py and new_py != real_note.get("pinyin"):
                logger.info("  %s: pinyin '%s' → '%s'", hanzi, real_note.get("pinyin"), new_py)
                real_note["pinyin"] = new_py
                updated_py += 1

            # Final check
            if new_kw and new_kw.lower() not in (new_en or "").lower():
                logger.warning("  ⚠ %s: keyword '%s' still not in English '%s'", hanzi, new_kw, new_en)
                fixed_mismatches += 1

    logger.info("")
    logger.info("Updated %d keywords, %d English translations, %d pinyin readings", updated_kw, updated_en, updated_py)
    if fixed_mismatches:
        logger.warning("%d still have keyword not in English", fixed_mismatches)

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

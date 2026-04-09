#!/usr/bin/env python3
"""Regenerate sentences that have phonetic confusers.

Usage:
    uv run python scripts/fix_confusers.py --dry-run                # preview all confusers
    uv run python scripts/fix_confusers.py --exact-only --dry-run   # preview exact homophones only
    uv run python scripts/fix_confusers.py --exact-only             # fix exact homophones
    uv run python scripts/fix_confusers.py --limit 5                # fix first 5
    uv run python scripts/fix_confusers.py                          # fix all (exact + same-base)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from anki_chinese.notes.pronunciation import find_phonetic_confusers
from anki_chinese.sentences.generator import SentenceGenerator

ENRICHED_PATH = Path(__file__).resolve().parents[1] / "data" / "state" / "enriched.json"
MAX_ATTEMPTS = 3


def load_notes() -> list[dict]:
    with open(ENRICHED_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_notes(notes: list[dict]) -> None:
    with open(ENRICHED_PATH, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(notes)} notes to {ENRICHED_PATH}")


def find_problem_notes(
    notes: list[dict], *, exact_only: bool = False
) -> list[tuple[int, dict, list]]:
    """Return (index, note, confusers) for notes with phonetic confusers."""
    problems = []
    for i, n in enumerate(notes):
        hanzi = n["hanzi"]
        pinyin = n.get("pinyin", "")
        sentence = n.get("sentence", "")
        sent_pinyin = n.get("sentence_pinyin", "")
        if not sentence or not sent_pinyin or not pinyin:
            continue
        confusers = find_phonetic_confusers(hanzi, pinyin, sentence, sent_pinyin)
        if exact_only:
            confusers = [(ch, py, sev) for ch, py, sev in confusers if sev == "exact"]
        if confusers:
            problems.append((i, n, confusers))
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix phonetic confusers in sentences")
    parser.add_argument("--dry-run", action="store_true", help="Just list problems, don't fix")
    parser.add_argument("--limit", type=int, default=0, help="Max notes to fix (0 = all)")
    parser.add_argument(
        "--exact-only",
        action="store_true",
        help="Only fix exact homophones (same syllable + same tone)",
    )
    args = parser.parse_args()

    notes = load_notes()
    problems = find_problem_notes(notes, exact_only=args.exact_only)
    label = "exact homophone" if args.exact_only else "phonetic confuser"
    print(f"Found {len(problems)} sentences with {label}s\n")

    if args.dry_run:
        for _, n, confusers in problems:
            labels = ", ".join(f"{ch}({py})[{sev}]" for ch, py, sev in confusers)
            print(f"  {n['hanzi']} ({n['pinyin']}): {labels}")
            print(f"    {n['sentence']}")
            print(f"    {n['sentence_english']}\n")
        return

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    generator = SentenceGenerator(api_key=api_key)

    to_fix = problems[: args.limit] if args.limit > 0 else problems
    fixed = 0
    failed = 0

    for idx, (note_idx, note, old_confusers) in enumerate(to_fix, 1):
        hanzi = note["hanzi"]
        pinyin = note.get("pinyin", "")
        old_labels = ", ".join(f"{ch}({py})[{sev}]" for ch, py, sev in old_confusers)
        print(f"[{idx}/{len(to_fix)}] {hanzi} ({pinyin}) — confusers: {old_labels}")
        print(f"  OLD: {note['sentence']}")

        success = False
        for attempt in range(1, MAX_ATTEMPTS + 1):
            result = generator.generate(hanzi, pinyin=pinyin)
            if not result.sentence:
                print(f"  attempt {attempt}: no sentence generated")
                continue

            new_confusers = find_phonetic_confusers(
                hanzi, result.character_pinyin or pinyin, result.sentence, result.pinyin
            )
            if new_confusers:
                labels = ", ".join(f"{ch}({py})[{sev}]" for ch, py, sev in new_confusers)
                print(f"  attempt {attempt}: still has confusers: {labels}")
                continue

            # Clean — apply it
            notes[note_idx]["sentence"] = result.sentence
            notes[note_idx]["sentence_pinyin"] = result.pinyin
            notes[note_idx]["sentence_english"] = result.english
            notes[note_idx]["sentence_audio"] = ""  # clear stale audio
            if result.meaning:
                notes[note_idx]["meaning"] = result.meaning
            if result.character_pinyin:
                notes[note_idx]["pinyin"] = result.character_pinyin
            print(f"  NEW: {result.sentence} — {result.english}")
            fixed += 1
            success = True
            break

        if not success:
            print(f"  FAILED after {MAX_ATTEMPTS} attempts")
            failed += 1

        # Save incrementally every 10
        if fixed > 0 and fixed % 10 == 0:
            save_notes(notes)

    if fixed > 0:
        save_notes(notes)

    print(f"\nDone: {fixed} fixed, {failed} failed out of {len(to_fix)}")


if __name__ == "__main__":
    main()

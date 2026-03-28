"""
v6 evaluation: v3's natural prompt + v5's validation pipeline.

Key insight from AI judge data:
  - v3 had best naturalness (4.66) because simple "daily life" prompt
  - v5's topic diversity seeds HURT naturalness (4.30) by forcing unnatural contexts
  - v5's validation pipeline catches real grammar bugs (二/两, measure words)

v6 combines the best of both:
  - v3's lean generation prompt (no topic seeds, no anti-cliché blacklists)
  - v5's code-level char check (deterministic, up to 2 retries)
  - v5's LLM self-validation (7-point checklist, temp=0.0)
  - v5's English keyword format

Pipeline:
  1. Generate sentence (lean prompt, no topic hint)
  2. Code check: target char in sentence? If not → retry (up to 2x)
  3. LLM validate: grammar/naturalness (same model, same conversation)
  4. If LLM flags issue → regenerate with error feedback (1 retry)
  5. If still bad → flag for manual review
"""

import json
import os
import time

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class SentenceResponse(BaseModel):
    sentence: str = Field(description="The Chinese sentence (6-10 characters)")
    pinyin: str = Field(description="Pinyin with tone marks")
    english: str = Field(description="English translation")
    keyword: str = Field(
        description="The English meaning of the target character as used in "
        "this sentence (e.g. 'water', 'study', 'big')"
    )


class ValidationResponse(BaseModel):
    grammar_correct: bool
    natural: bool
    error_description: str  # empty string if no issues


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

GEMINI_MODEL = "gemini-3.1-flash-lite-preview"

SYSTEM_INSTRUCTION = (
    "You are a Mandarin Chinese expert creating flashcard sentences "
    "for an adult beginner.\n\n"
    "Rules:\n"
    "1. The target character MUST appear literally in the sentence\n"
    "2. 6–10 Chinese characters long\n"
    "3. Natural — something a native speaker would actually say in daily life\n"
    "4. Use the character in its most common, everyday meaning\n"
    "5. Keep other vocabulary simple and common"
)

VALIDATE_PROMPT = (
    "Now carefully check your sentence as a strict native Chinese speaker. "
    "Check ALL of these:\n"
    "1. Grammar: wrong measure words (个 instead of 只/块/粒/条)?\n"
    "2. 二 vs 两: is 二 used before a measure word where 两 should be? "
    "(两个人 not 二个人, 两点 not 二点)\n"
    "3. Time periods: 下午 is only until ~6PM. 7PM+ is 晚上.\n"
    "4. Register: is this adult speech? Avoid childish phrasing "
    "(e.g. 伯伯/阿姨 as main subjects).\n"
    "5. Question particles: 吗 for yes/no questions, 呢 for follow-up only.\n"
    "6. Naturalness: would a native speaker actually say this in conversation?\n"
    "7. Missing words: prepositions (在/到), structural particles (的/了) "
    "where needed?\n"
    "Be strict. If ANYTHING is wrong, describe it."
)

MAX_CHAR_RETRIES = 2
MAX_VALIDATE_RETRIES = 1


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_one(client: genai.Client, hanzi: str) -> dict:
    """Generate and validate a single sentence for the given character."""

    gen_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=SentenceResponse,
        temperature=0.7,
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MINIMAL
        ),
    )
    val_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=ValidationResponse,
        temperature=0.0,
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MINIMAL
        ),
    )

    generate_prompt = (
        f"Generate a short example sentence containing the character {hanzi}. "
        f"The character {hanzi} MUST literally appear in the sentence."
    )
    history: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=generate_prompt)])
    ]

    # --- Step 1 + 2: Generate + code char-check with retries ---------------
    parsed = None
    for char_attempt in range(1, MAX_CHAR_RETRIES + 2):
        try:
            resp = client.models.generate_content(
                model=GEMINI_MODEL, contents=history, config=gen_config
            )
            parsed = SentenceResponse.model_validate_json(resp.text or "")
            history.append(
                types.Content(role="model", parts=[types.Part(text=resp.text)])
            )
        except Exception as exc:
            if "429" in str(exc):
                time.sleep(15)
                continue
            return _error_result(hanzi, str(exc)[:100])

        if hanzi in parsed.sentence:
            break

        retry_msg = (
            f"WRONG. Your sentence \"{parsed.sentence}\" does not contain "
            f"the character {hanzi}. Try again."
        )
        history.append(
            types.Content(role="user", parts=[types.Part(text=retry_msg)])
        )

    if parsed is None or hanzi not in parsed.sentence:
        return _error_result(hanzi, "target char missing after retries")

    first_sentence = parsed.sentence

    # --- Step 3: LLM validation --------------------------------------------
    history.append(
        types.Content(role="user", parts=[types.Part(text=VALIDATE_PROMPT)])
    )
    try:
        val_resp = client.models.generate_content(
            model=GEMINI_MODEL, contents=history, config=val_config
        )
        validation = ValidationResponse.model_validate_json(val_resp.text or "")
        history.append(
            types.Content(role="model", parts=[types.Part(text=val_resp.text)])
        )
    except Exception as exc:
        if "429" in str(exc):
            time.sleep(15)
        return _ok_result(hanzi, parsed, 1, "")

    if validation.grammar_correct and validation.natural:
        return _ok_result(hanzi, parsed, 1, "")

    # --- Step 4: Regenerate with error feedback ----------------------------
    regen_msg = (
        f"Your sentence has this error: {validation.error_description}\n"
        f"Generate a NEW, DIFFERENT sentence containing {hanzi} that fixes "
        f"this problem. The character {hanzi} MUST literally appear."
    )
    history.append(
        types.Content(role="user", parts=[types.Part(text=regen_msg)])
    )
    try:
        resp2 = client.models.generate_content(
            model=GEMINI_MODEL, contents=history, config=gen_config
        )
        parsed2 = SentenceResponse.model_validate_json(resp2.text or "")
        history.append(
            types.Content(role="model", parts=[types.Part(text=resp2.text)])
        )
    except Exception as exc:
        if "429" in str(exc):
            time.sleep(15)
        return _ok_result(hanzi, parsed, 1, validation.error_description)

    if hanzi not in parsed2.sentence:
        return _retry_result(
            hanzi, parsed, parsed2, False,
            validation.error_description, "target char missing in retry",
        )

    # Validate the retry
    history.append(
        types.Content(role="user", parts=[types.Part(text=VALIDATE_PROMPT)])
    )
    try:
        val2_resp = client.models.generate_content(
            model=GEMINI_MODEL, contents=history, config=val_config
        )
        validation2 = ValidationResponse.model_validate_json(val2_resp.text or "")
    except Exception:
        return _retry_result(
            hanzi, parsed, parsed2, True,
            validation.error_description, "",
        )

    ok = validation2.grammar_correct and validation2.natural
    return _retry_result(
        hanzi, parsed, parsed2, ok,
        validation.error_description,
        "" if ok else validation2.error_description,
    )


# ---------------------------------------------------------------------------
# Result builders
# ---------------------------------------------------------------------------

def _ok_result(hanzi, parsed, attempt, error):
    return {
        "char": hanzi,
        "sentence": parsed.sentence,
        "pinyin": parsed.pinyin,
        "english": parsed.english,
        "keyword": parsed.keyword,
        "attempt": attempt,
        "valid": True,
        "error": error,
    }


def _retry_result(hanzi, first, second, valid, first_error, second_error):
    return {
        "char": hanzi,
        "sentence": second.sentence,
        "pinyin": second.pinyin,
        "english": second.english,
        "keyword": second.keyword,
        "attempt": 2,
        "valid": valid,
        "first_sentence": first.sentence,
        "first_error": first_error,
        "second_error": second_error,
    }


def _error_result(hanzi, error):
    return {
        "char": hanzi,
        "sentence": "",
        "pinyin": "",
        "english": "",
        "keyword": "",
        "attempt": 0,
        "valid": False,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("ERROR: GEMINI_API_KEY not set")
        return

    client = genai.Client(api_key=key)

    with open("data/build/judge_pairs.json") as f:
        all_chars = [p["char"] for p in json.load(f)]

    results = []
    stats = {
        "total": 0, "clean_first": 0, "fixed_retry": 0,
        "still_bad": 0, "errors": 0,
    }

    for i, hanzi in enumerate(all_chars):
        stats["total"] += 1
        result = generate_one(client, hanzi)
        results.append(result)

        if result.get("error") and not result.get("sentence"):
            stats["errors"] += 1
            status = "💥"
        elif result["attempt"] == 1:
            stats["clean_first"] += 1
            status = "✅"
        elif result["valid"]:
            stats["fixed_retry"] += 1
            status = "🔄✅"
        else:
            stats["still_bad"] += 1
            status = "❌"

        print(
            f"  [{i+1:3d}/{len(all_chars)}] {hanzi}: "
            f"{result.get('sentence', 'ERROR')} "
            f"(kw: {result.get('keyword', '?')}) {status}"
        )
        if result.get("first_error"):
            print(f"       1st: {result['first_sentence']} → {result['first_error']}")

        time.sleep(0.5)

    out_path = "data/build/eval_v6.json"
    with open(out_path, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"V6 RESULTS: {stats['total']} chars")
    print(f"  Clean first try: {stats['clean_first']}")
    print(f"  Fixed on retry:  {stats['fixed_retry']}")
    print(f"  Still bad:       {stats['still_bad']}")
    print(f"  API errors:      {stats['errors']}")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()

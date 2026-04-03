"""
Sentence generator using Gemini Flash Lite with self-validation.

This is the v6 pipeline (ADR-001): lean 5-rule prompt, code-level character
check, LLM self-validation with 7-point grammar checklist, single retry on
failure.

Usage:
    generator = SentenceGenerator(api_key="...")
    result = generator.generate("一")
    # result.sentence = "我喝一杯热咖啡。"
    # result.meaning = "one; 1"
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from ..config import CEDICT_PATH
from ..data_sources import lookup_char_defs

logger = logging.getLogger(__name__)

MODEL = "gemini-3.1-flash-lite-preview"

SYSTEM_INSTRUCTION = (
    "You are a Mandarin Chinese expert creating flashcard sentences "
    "for an adult beginner.\n\n"
    "Rules:\n"
    "1. The target character MUST appear literally in the sentence\n"
    "2. 6–10 Chinese characters long\n"
    "3. Natural — something a native speaker would actually say in daily life\n"
    "4. Use the character in its most common, everyday meaning\n"
    "5. Keep other vocabulary simple and common\n"
    "6. For the meaning field: give the character's CORE dictionary meaning first. "
    "If the character appears in a compound with a different meaning, add "
    "'; in [compound]: compound meaning' (e.g. 'silver; in 银行: bank'). "
    "For grammatical particles, describe the function. "
    "For phonetic uses, write 'phonetic; in [compound]: word'."
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

_MAX_CHAR_RETRIES = 2
_RATE_LIMIT_SLEEP = 15
_INTER_REQUEST_DELAY = 0.5


# -- Structured output schemas for Gemini ----------------------------------

class _SentenceSchema(BaseModel):
    sentence: str = Field(description="The Chinese sentence (6-10 characters)")
    pinyin: str = Field(description="Pinyin with tone marks for the full sentence")
    english: str = Field(description="English translation")
    meaning: str = Field(
        description="Full English meaning of the target character: core dictionary "
        "meaning plus contextual usage if different (e.g. 'silver; in 银行: bank')"
    )
    character_pinyin: str = Field(
        description="The pinyin of the target character as used in this sentence "
        "(e.g. 'shuǐ', 'xuē', 'xiāo') — just the single syllable"
    )


class _ValidationSchema(BaseModel):
    grammar_correct: bool
    natural: bool
    error_description: str


# -- Public interface -------------------------------------------------------

@dataclass(frozen=True)
class SentenceResult:
    """Output of sentence generation for one character."""
    sentence: str
    pinyin: str
    english: str
    meaning: str
    character_pinyin: str
    valid: bool
    error: str = ""


class SentenceGenerator:
    """Generate validated example sentences using Gemini Flash Lite.

    Deep module: call ``generate(hanzi)`` and get back a validated sentence.
    Everything else (prompting, validation, retries) is hidden.
    """

    def __init__(self, api_key: str, *, model: str = MODEL) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, hanzi: str, *, pinyin: str = "") -> SentenceResult:
        """Generate a validated example sentence for *hanzi*."""
        return self._generate_one(hanzi, pinyin=pinyin)

    def generate_candidates(self, hanzi: str, count: int = 3, *, pinyin: str = "") -> list[SentenceResult]:
        """Generate *count* independent candidate sentences for *hanzi*."""
        candidates: list[SentenceResult] = []
        for _ in range(count):
            result = self._generate_one(hanzi, pinyin=pinyin)
            if result.sentence:
                candidates.append(result)
        return candidates

    def _generate_one(self, hanzi: str, *, pinyin: str = "") -> SentenceResult:
        """Generate a single validated example sentence for *hanzi*.

        Flow (max 2 API calls):
        1. Generate sentence + code-level char check (with retries)
        2. LLM self-validation — flags issues but does NOT retry
        """
        gen_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_SentenceSchema,
            temperature=0.7,
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL
            ),
        )
        val_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_ValidationSchema,
            temperature=0.0,
        )

        prompt = (
            f"Generate a short example sentence containing the character {hanzi}. "
            f"The character {hanzi} MUST literally appear in the sentence."
        )
        cedict_defs = lookup_char_defs(hanzi, CEDICT_PATH, pinyin=pinyin)
        if cedict_defs:
            defs_str = "; ".join(cedict_defs[:5])
            prompt += f"\nDictionary definitions for {hanzi}: {defs_str}"
        if pinyin:
            prompt += (
                f"\nUse the character with pronunciation {pinyin} "
                f"(not a different reading of the same character)."
            )
        history: list[types.Content] = [
            types.Content(role="user", parts=[types.Part(text=prompt)])
        ]

        # Step 1: generate + code char-check with retries (1 API call usually)
        parsed = self._generate_with_char_check(hanzi, history, gen_config)
        if parsed is None:
            return SentenceResult("", "", "", "", "", valid=False,
                                  error="target char missing after retries")

        # Step 2: LLM self-validation (1 API call) — flag but don't retry
        validation = self._validate(history, val_config)
        if validation is None or (validation.grammar_correct and validation.natural):
            return self._to_result(parsed, valid=True)

        # Validation found issues — return the sentence but flag it for review
        logger.warning("%s: validation flagged: %s", hanzi, validation.error_description)
        return self._to_result(parsed, valid=False, error=validation.error_description)

    # -- Private helpers (all hidden behind generate()) --------------------

    def _generate_with_char_check(
        self,
        hanzi: str,
        history: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> _SentenceSchema | None:
        parsed = None
        for _ in range(_MAX_CHAR_RETRIES + 1):
            resp = self._call(history, config)
            if resp is None:
                continue
            parsed = _SentenceSchema.model_validate_json(resp)
            history.append(
                types.Content(role="model", parts=[types.Part(text=resp)])
            )
            if hanzi in parsed.sentence:
                return parsed
            retry_msg = (
                f"WRONG. Your sentence \"{parsed.sentence}\" does not contain "
                f"the character {hanzi}. Try again."
            )
            history.append(
                types.Content(role="user", parts=[types.Part(text=retry_msg)])
            )
        return None

    def _validate(
        self,
        history: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> _ValidationSchema | None:
        history.append(
            types.Content(role="user", parts=[types.Part(text=VALIDATE_PROMPT)])
        )
        resp = self._call(history, config)
        if resp is None:
            return None
        result = _ValidationSchema.model_validate_json(resp)
        history.append(
            types.Content(role="model", parts=[types.Part(text=resp)])
        )
        return result

    def _call(
        self,
        history: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> str | None:
        """Make a Gemini API call with rate-limit retry."""
        try:
            resp = self._client.models.generate_content(
                model=self._model, contents=history, config=config,
            )
            time.sleep(_INTER_REQUEST_DELAY)
            return resp.text or None
        except Exception as exc:
            if "429" in str(exc):
                logger.warning("Rate limited, sleeping %ds", _RATE_LIMIT_SLEEP)
                time.sleep(_RATE_LIMIT_SLEEP)
                return None
            logger.error("Gemini API error: %s", exc)
            return None

    @staticmethod
    def _to_result(
        parsed: _SentenceSchema,
        *,
        valid: bool,
        error: str = "",
    ) -> SentenceResult:
        return SentenceResult(
            sentence=parsed.sentence,
            pinyin=parsed.pinyin,
            english=parsed.english,
            meaning=parsed.meaning,
            character_pinyin=parsed.character_pinyin,
            valid=valid,
            error=error,
        )

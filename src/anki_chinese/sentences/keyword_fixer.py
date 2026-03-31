"""
Batch keyword fixer using Gemini.

Sends batches of (hanzi, sentence, english) to Gemini and asks for the
contextual English meaning of each character as used in its sentence.
"""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

import logging
import time

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from .generator import MODEL

logger = logging.getLogger(__name__)

_BATCH_SIZE = 20
_RATE_LIMIT_SLEEP = 15
_INTER_REQUEST_DELAY = 0.5

SYSTEM_INSTRUCTION = (
    "You are a Mandarin Chinese expert. For each Chinese character below, "
    "provide the English meaning of that character as used in the given "
    "sentence. Return a single, concise English word or short phrase "
    "(1-3 words)."
)


# -- Structured output schemas ------------------------------------------------


class _KeywordEntry(BaseModel):
    hanzi: str = Field(description="The Chinese character")
    keyword: str = Field(
        description="The contextual English meaning of the character "
        "as used in the sentence (1-3 words)"
    )


class _KeywordBatchSchema(BaseModel):
    entries: list[_KeywordEntry]


# -- Public interface ----------------------------------------------------------


class KeywordFixer:
    """Batch-fix keywords using Gemini to derive contextual meanings."""

    def __init__(self, api_key: str, *, model: str = MODEL) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def fix_batch(
        self,
        items: list[tuple[str, str, str]],
    ) -> dict[str, str]:
        """Fix keywords for a batch of characters.

        Parameters
        ----------
        items:
            List of ``(hanzi, sentence, english_translation)`` tuples.

        Returns
        -------
        dict mapping hanzi → contextual keyword.
        """
        results: dict[str, str] = {}
        for start in range(0, len(items), _BATCH_SIZE):
            chunk = items[start : start + _BATCH_SIZE]
            chunk_result = self._fix_chunk(chunk)
            results.update(chunk_result)
        return results

    # -- Private helpers -------------------------------------------------------

    def _fix_chunk(
        self,
        chunk: list[tuple[str, str, str]],
    ) -> dict[str, str]:
        """Send one batch request to Gemini and parse the result."""
        lines: list[str] = []
        for i, (hanzi, sentence, english) in enumerate(chunk, 1):
            lines.append(f"{i}. {hanzi} — sentence: {sentence}({english})")
        prompt = "\n".join(lines)

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_KeywordBatchSchema,
            temperature=0.0,
        )
        contents = [
            types.Content(role="user", parts=[types.Part(text=prompt)]),
        ]

        resp = self._call(contents, config)
        if resp is None:
            logger.warning("Empty response for batch of %d", len(chunk))
            return {}

        parsed = _KeywordBatchSchema.model_validate_json(resp)
        return {entry.hanzi: entry.keyword for entry in parsed.entries}

    def _call(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> str | None:
        """Make a Gemini API call with rate-limit retry."""
        try:
            resp = self._client.models.generate_content(
                model=self._model, contents=contents, config=config,
            )
            time.sleep(_INTER_REQUEST_DELAY)
            return resp.text or None
        except Exception as exc:
            if "429" in str(exc):
                logger.warning("Rate limited, sleeping %ds", _RATE_LIMIT_SLEEP)
                time.sleep(_RATE_LIMIT_SLEEP)
                return self._call(contents, config)
            logger.error("Gemini API error: %s", exc)
            return None

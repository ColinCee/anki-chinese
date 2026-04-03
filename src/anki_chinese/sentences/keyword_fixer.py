"""
Batch meaning fixer using Gemini.

Sends batches of (hanzi, sentence, english) to Gemini along with CC-CEDICT
definitions and asks for full meaning definitions for each character.
"""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

import logging
import time
from collections.abc import Callable

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from ..config import CEDICT_PATH
from ..data_sources import lookup_char_defs
from .generator import MODEL

logger = logging.getLogger(__name__)

_BATCH_SIZE = 20
_RATE_LIMIT_SLEEP = 15
_INTER_REQUEST_DELAY = 0.5

SYSTEM_INSTRUCTION = (
    "You are a Mandarin Chinese expert. For each Chinese character below, "
    "provide the full English meaning of that character.\n\n"
    "Format: core dictionary meaning first. If the character appears in a compound "
    "with a different meaning, add '; in [compound]: compound meaning'.\n"
    "Examples: 'silver; in 银行: bank', 'to hit; in 打电话: to make a phone call', "
    "'aspect particle (-ing); marks ongoing action', 'phonetic; in 俄罗斯: Russia'."
)


# -- Structured output schemas ------------------------------------------------


class _MeaningEntry(BaseModel):
    hanzi: str = Field(description="The Chinese character")
    meaning: str = Field(
        description="Full English meaning: core dictionary definition + "
        "contextual compound usage if different"
    )


class _MeaningBatchSchema(BaseModel):
    entries: list[_MeaningEntry]


# -- Public interface ----------------------------------------------------------


class KeywordFixer:
    """Batch-fix meanings using Gemini to derive contextual meanings."""

    def __init__(self, api_key: str, *, model: str = MODEL) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def fix_batch(
        self,
        items: list[tuple[str, str, str]],
        *,
        on_chunk_done: Callable[[int], None] | None = None,
    ) -> dict[str, str]:
        """Fix meanings for a batch of characters.

        Parameters
        ----------
        items:
            List of ``(hanzi, sentence, english_translation)`` tuples.
        on_chunk_done:
            Optional callback called after each chunk with the chunk size.

        Returns
        -------
        dict mapping hanzi → contextual meaning.
        """
        results: dict[str, str] = {}
        for start in range(0, len(items), _BATCH_SIZE):
            chunk = items[start : start + _BATCH_SIZE]
            chunk_result = self._fix_chunk(chunk)
            results.update(chunk_result)
            if on_chunk_done:
                on_chunk_done(len(chunk))
        return results

    # -- Private helpers -------------------------------------------------------

    def _fix_chunk(
        self,
        chunk: list[tuple[str, str, str]],
    ) -> dict[str, str]:
        """Send one batch request to Gemini and parse the result."""
        lines: list[str] = []
        for i, (hanzi, sentence, english) in enumerate(chunk, 1):
            cedict_defs = lookup_char_defs(hanzi, CEDICT_PATH)
            defs_str = "; ".join(cedict_defs[:5]) if cedict_defs else "(no entry)"
            lines.append(
                f"{i}. {hanzi}\n"
                f"   Dictionary: {defs_str}\n"
                f"   Sentence: {sentence} ({english})"
            )
        prompt = "\n".join(lines)

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_MeaningBatchSchema,
            temperature=0.0,
        )
        contents = [
            types.Content(role="user", parts=[types.Part(text=prompt)]),
        ]

        resp = self._call(contents, config)
        if resp is None:
            logger.warning("Empty response for batch of %d", len(chunk))
            return {}

        parsed = _MeaningBatchSchema.model_validate_json(resp)
        return {entry.hanzi: entry.meaning for entry in parsed.entries}

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

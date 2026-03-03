"""
Azure Speech Service TTS with SSML phoneme tags.

Generates audio files and returns the Anki-compatible [sound:filename.mp3] tag.
Uses <phoneme> in SSML to force the exact pronunciation matching the
pinyin/jyutping fields, so audio always matches the displayed romanization.
"""

from __future__ import annotations

import os
import time
import unicodedata
from pathlib import Path

from dotenv import load_dotenv

from ..config import CANTONESE_VOICE, GENERATED_MEDIA_DIR, MANDARIN_VOICE

# ── Rate limiter ──────────────────────────────────────────────────────
# Azure F0 tier: 20 transactions per 60 seconds.
_REQUEST_INTERVAL = 3.0  # seconds between API calls (20 per 60s)

load_dotenv()

# ---------- diacritical pinyin → Azure SAPI format ----------
# Azure zh-CN SAPI expects: "yi 1", "zhong 1", "lv 3", "de 5"
# Our stored pinyin uses tone diacritics: "yī", "zhōng", "lǜ", "de"

# Map combining diacritical marks to tone numbers
_TONE_MARKS: dict[int, int] = {
    0x0304: 1,  # macron  ̄  → tone 1
    0x0301: 2,  # acute   ́  → tone 2
    0x030C: 3,  # caron   ̌  → tone 3
    0x0300: 4,  # grave   ̀  → tone 4
}


def _to_sapi_pinyin(diacritical: str) -> str:
    """Convert diacritical pinyin (yī, zhōng, lǜ) to Azure SAPI format (yi 1, zhong 1, lv 3).

    Steps:
      1. Decompose Unicode so tone marks become combining characters.
      2. Scan for the combining tone mark → extract tone number.
      3. Convert u + combining diaeresis (ü) → v  (Azure SAPI convention).
      4. Strip remaining combining marks to get bare ASCII syllable.
      5. Append space + tone number (neutral tone = 5).
    """
    nfd = unicodedata.normalize("NFD", diacritical.strip().lower())

    tone = 5  # default: neutral tone (轻声)
    bare_chars: list[str] = []
    i = 0
    while i < len(nfd):
        ch = nfd[i]
        cp = ord(ch)

        if cp in _TONE_MARKS:
            tone = _TONE_MARKS[cp]
        elif cp == 0x0308:
            # Combining diaeresis — preceding char should be 'u' → replace with 'v'
            if bare_chars and bare_chars[-1] == "u":
                bare_chars[-1] = "v"
        elif unicodedata.category(ch).startswith("M"):
            pass  # skip other combining marks
        else:
            bare_chars.append(ch)

        i += 1

    syllable = "".join(bare_chars)
    return f"{syllable} {tone}"


def _get_speech_config():  # type: ignore[no-untyped-def]
    """Lazy import + config — only needed when actually generating audio."""
    import azure.cognitiveservices.speech as speechsdk

    key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION", "eastus")
    if not key:
        raise RuntimeError(
            "AZURE_SPEECH_KEY not set. Copy .env.example to .env and add your key."
        )
    return speechsdk.SpeechConfig(subscription=key, region=region)


def _ssml_mandarin(
    hanzi: str, pinyin_with_tone: str, *, voice: str | None = None
) -> str:
    """Build SSML that forces a specific Mandarin pronunciation."""
    sapi_ph = _to_sapi_pinyin(pinyin_with_tone)
    v = voice or MANDARIN_VOICE
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
  <voice name="{v}">
    <phoneme alphabet="sapi" ph="{sapi_ph}">{hanzi}</phoneme>
  </voice>
</speak>"""


def _to_sapi_jyutping(jyutping: str) -> str:
    """Ensure jyutping has a space before the tone number for Azure SAPI."""
    jp = jyutping.strip()
    if jp and jp[-1].isdigit() and len(jp) >= 2 and jp[-2] != " ":
        return jp[:-1] + " " + jp[-1]
    return jp


def _ssml_cantonese(hanzi: str, jyutping: str) -> str:
    """Build SSML that forces a specific Cantonese pronunciation."""
    sapi_jp = _to_sapi_jyutping(jyutping)
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-HK">
  <voice name="{CANTONESE_VOICE}">
    <phoneme alphabet="sapi" ph="{sapi_jp}">{hanzi}</phoneme>
  </voice>
</speak>"""


def _ssml_plain(*, text: str, voice: str, lang: str) -> str:
    """Build plain SSML with no forced phoneme pronunciation."""
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">
    <voice name="{voice}">{text}</voice>
</speak>"""


def _generate_audio(ssml: str, output_path: Path) -> bool:
    """Synthesize speech from SSML and save to file.  Returns True on success."""
    import azure.cognitiveservices.speech as speechsdk

    output_path.parent.mkdir(parents=True, exist_ok=True)
    time.sleep(_REQUEST_INTERVAL)

    config = _get_speech_config()
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=config, audio_config=audio_config
    )

    result = synthesizer.speak_ssml_async(ssml).get()  # type: ignore[union-attr]

    if result is None:
        return False

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True

    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        msg = f"TTS failed for {output_path.name}: {details.reason} — {details.error_details}"
        if "429" in (details.error_details or ""):
            print(f"    ⚠ Skipping (rate-limited): {output_path.name}")
            return False
        raise RuntimeError(msg)

    return False


def _is_valid_audio(path: Path) -> bool:
    """Return True if the file exists and is non-empty."""
    return path.exists() and path.stat().st_size > 0


def generate_mandarin(hanzi: str, pinyin: str, *, force: bool = False) -> str:
    """Generate Mandarin audio.  Returns '[sound:filename.mp3]' tag."""
    safe_pinyin = pinyin.replace(" ", "_")
    filename = f"cmn_{hanzi}_{safe_pinyin}.mp3"
    output_path = GENERATED_MEDIA_DIR / filename

    if _is_valid_audio(output_path) and not force:
        return f"[sound:{filename}]"

    ssml = _ssml_mandarin(hanzi, pinyin)
    try:
        _generate_audio(ssml, output_path)
    except RuntimeError as e:
        if "Unknown phoneme" not in str(e):
            raise
        fallback = _ssml_plain(text=hanzi, voice=MANDARIN_VOICE, lang="zh-CN")
        _generate_audio(fallback, output_path)
    return f"[sound:{filename}]"


def generate_cantonese(hanzi: str, jyutping: str, *, force: bool = False) -> str:
    """Generate Cantonese audio.  Returns '[sound:filename.mp3]' tag."""
    safe_jp = jyutping.replace(" ", "_")
    filename = f"yue_{hanzi}_{safe_jp}.mp3"
    output_path = GENERATED_MEDIA_DIR / filename

    if _is_valid_audio(output_path) and not force:
        return f"[sound:{filename}]"

    ssml = _ssml_cantonese(hanzi, jyutping)
    try:
        _generate_audio(ssml, output_path)
    except RuntimeError as e:
        if "Unknown phoneme" not in str(e):
            raise
        fallback = _ssml_plain(text=hanzi, voice=CANTONESE_VOICE, lang="zh-HK")
        _generate_audio(fallback, output_path)
    return f"[sound:{filename}]"


def generate_example_audio(word: str, *, force: bool = False) -> str:
    """Generate Mandarin audio for an example word.  Returns '[sound:filename.mp3]' tag."""
    filename = f"cmn_{word}.mp3"
    output_path = GENERATED_MEDIA_DIR / filename

    if _is_valid_audio(output_path) and not force:
        return f"[sound:{filename}]"

    # Let Azure pick natural pronunciation for multi-char words
    ssml = _ssml_plain(text=word, voice=MANDARIN_VOICE, lang="zh-CN")
    _generate_audio(ssml, output_path)
    return f"[sound:{filename}]"

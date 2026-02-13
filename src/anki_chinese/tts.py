"""
Azure Speech Service TTS with SSML phoneme tags.

Generates audio files and returns the Anki-compatible [sound:filename.mp3] tag.
Uses <phoneme> in SSML to force the exact pronunciation matching the
pinyin/jyutping fields, so audio always matches the displayed romanization.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from .config import GENERATED_MEDIA_DIR, MANDARIN_VOICE, CANTONESE_VOICE

load_dotenv()


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


def _ssml_mandarin(hanzi: str, pinyin_with_tone: str) -> str:
    """Build SSML that forces a specific Mandarin pronunciation."""
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
  <voice name="{MANDARIN_VOICE}">
    <phoneme alphabet="sapi" ph="{pinyin_with_tone}">{hanzi}</phoneme>
  </voice>
</speak>"""


def _ssml_cantonese(hanzi: str, jyutping: str) -> str:
    """Build SSML that forces a specific Cantonese pronunciation."""
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-HK">
  <voice name="{CANTONESE_VOICE}">
    <phoneme alphabet="jyutping" ph="{jyutping}">{hanzi}</phoneme>
  </voice>
</speak>"""


def _generate_audio(ssml: str, output_path: Path) -> bool:
    """Synthesize speech from SSML and save to file.  Returns True on success."""
    import azure.cognitiveservices.speech as speechsdk

    output_path.parent.mkdir(parents=True, exist_ok=True)

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
        raise RuntimeError(
            f"TTS failed for {output_path.name}: {details.reason} — {details.error_details}"
        )
    return False


def generate_mandarin(hanzi: str, pinyin: str, *, force: bool = False) -> str:
    """Generate Mandarin audio.  Returns '[sound:filename.mp3]' tag."""
    # Build a deterministic filename from the character + pinyin
    safe_pinyin = pinyin.replace(" ", "_")
    filename = f"cmn_{hanzi}_{safe_pinyin}.mp3"
    output_path = GENERATED_MEDIA_DIR / filename

    if output_path.exists() and not force:
        return f"[sound:{filename}]"

    ssml = _ssml_mandarin(hanzi, pinyin)
    _generate_audio(ssml, output_path)
    return f"[sound:{filename}]"


def generate_cantonese(hanzi: str, jyutping: str, *, force: bool = False) -> str:
    """Generate Cantonese audio.  Returns '[sound:filename.mp3]' tag."""
    safe_jp = jyutping.replace(" ", "_")
    filename = f"yue_{hanzi}_{safe_jp}.mp3"
    output_path = GENERATED_MEDIA_DIR / filename

    if output_path.exists() and not force:
        return f"[sound:{filename}]"

    ssml = _ssml_cantonese(hanzi, jyutping)
    _generate_audio(ssml, output_path)
    return f"[sound:{filename}]"


def generate_example_audio(word: str, *, force: bool = False) -> str:
    """Generate Mandarin audio for an example word."""
    filename = f"cmn_{word}.mp3"
    output_path = GENERATED_MEDIA_DIR / filename

    if output_path.exists() and not force:
        return f"[sound:{filename}]"

    # For example words, we don't force phoneme — let Azure pick naturally
    # since multi-char words have enough context for correct pronunciation
    ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
  <voice name="{MANDARIN_VOICE}">{word}</voice>
</speak>"""
    _generate_audio(ssml, output_path)
    return f"[sound:{filename}]"

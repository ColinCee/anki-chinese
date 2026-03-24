"""Azure Speech Service TTS with SSML phoneme tags."""

from __future__ import annotations

import os
import time
import unicodedata
from pathlib import Path

from dotenv import load_dotenv

from ..config import CANTONESE_VOICE, GENERATED_AUDIO_DIR, MANDARIN_VOICE
from .files import example_audio_filename, is_valid_audio_file, is_valid_audio_tag
from .provider import ProviderCapabilities
from .retry import DEFAULT_RETRY_POLICY, RetryPolicy

load_dotenv()


class TTSError(RuntimeError):
    """Base error for speech synthesis failures."""


class TTSRateLimitError(TTSError):
    """Speech synthesis failed because Azure rate limited the request."""


def _cleanup_partial_audio(output_path: Path) -> None:
    if output_path.exists() and output_path.stat().st_size == 0:
        output_path.unlink()


def _is_rate_limited_message(message: str) -> bool:
    lowered = message.lower()
    return "429" in lowered or "too many requests" in lowered


_TONE_MARKS: dict[int, int] = {
    0x0304: 1,
    0x0301: 2,
    0x030C: 3,
    0x0300: 4,
}


def _to_sapi_pinyin(diacritical: str) -> str:
    nfd = unicodedata.normalize("NFD", diacritical.strip().lower())

    tone = 5
    bare_chars: list[str] = []
    i = 0
    while i < len(nfd):
        char = nfd[i]
        codepoint = ord(char)

        if codepoint in _TONE_MARKS:
            tone = _TONE_MARKS[codepoint]
        elif codepoint == 0x0308:
            if bare_chars and bare_chars[-1] == "u":
                bare_chars[-1] = "v"
        elif unicodedata.category(char).startswith("M"):
            pass
        else:
            bare_chars.append(char)

        i += 1

    syllable = "".join(bare_chars)
    return f"{syllable} {tone}"


def _get_speech_config():  # type: ignore[no-untyped-def]
    import azure.cognitiveservices.speech as speechsdk

    key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")
    if not key:
        raise RuntimeError(
            "AZURE_SPEECH_KEY not set. Copy .env.example to .env and add your key."
        )
    if not region:
        raise RuntimeError(
            "AZURE_SPEECH_REGION not set. Add your Speech resource region to .env."
        )
    return speechsdk.SpeechConfig(subscription=key, region=region)


def _ssml_mandarin(
    hanzi: str, pinyin_with_tone: str, *, voice: str | None = None
) -> str:
    sapi_ph = _to_sapi_pinyin(pinyin_with_tone)
    use_voice = voice or MANDARIN_VOICE
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
  <voice name="{use_voice}">
    <phoneme alphabet="sapi" ph="{sapi_ph}">{hanzi}</phoneme>
  </voice>
</speak>"""


def _ssml_mandarin_text(
    text: str, pinyin_with_tone: str, *, voice: str | None = None
) -> str:
    syllables = pinyin_with_tone.split()
    use_voice = voice or MANDARIN_VOICE
    if len(syllables) != len(text):
        return _ssml_plain(text=text, voice=use_voice, lang="zh-CN")

    phonemes = "".join(
        f'<phoneme alphabet="sapi" ph="{_to_sapi_pinyin(syllable)}">{char}</phoneme>'
        for char, syllable in zip(text, syllables, strict=False)
    )
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
    <voice name="{use_voice}">
    {phonemes}
  </voice>
</speak>"""


def _to_sapi_jyutping(jyutping: str) -> str:
    cleaned = jyutping.strip()
    if cleaned and cleaned[-1].isdigit() and len(cleaned) >= 2 and cleaned[-2] != " ":
        return cleaned[:-1] + " " + cleaned[-1]
    return cleaned


def _ssml_cantonese(hanzi: str, jyutping: str) -> str:
    sapi_jyutping = _to_sapi_jyutping(jyutping)
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-HK">
  <voice name="{CANTONESE_VOICE}">
    <phoneme alphabet="sapi" ph="{sapi_jyutping}">{hanzi}</phoneme>
  </voice>
</speak>"""


def _ssml_plain(*, text: str, voice: str, lang: str) -> str:
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">
    <voice name="{voice}">{text}</voice>
</speak>"""


def _generate_audio(
    ssml: str,
    output_path: Path,
    *,
    retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
) -> bool:
    import azure.cognitiveservices.speech as speechsdk

    output_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retry_policy.max_attempts + 1):
        _cleanup_partial_audio(output_path)
        delay = (
            retry_policy.request_interval
            if attempt == 1
            else retry_policy.rate_limit_retry_delay
        )
        time.sleep(delay)

        config = _get_speech_config()
        config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=config, audio_config=audio_config
        )

        try:
            result = synthesizer.speak_ssml_async(ssml).get()  # type: ignore[union-attr]
        except Exception as exc:
            _cleanup_partial_audio(output_path)
            if attempt < retry_policy.max_attempts and _is_rate_limited_message(str(exc)):
                continue
            raise

        if result is None:
            _cleanup_partial_audio(output_path)
            raise TTSError(f"TTS failed for {output_path.name}: no result returned")

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            if not is_valid_audio_file(output_path):
                _cleanup_partial_audio(output_path)
                raise TTSError(f"TTS did not create audio for {output_path.name}")
            return True

        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details
            message = (
                f"TTS failed for {output_path.name}: "
                f"{details.reason} — {details.error_details}"
            )
            error_details = details.error_details or ""
            _cleanup_partial_audio(output_path)
            if _is_rate_limited_message(error_details):
                if attempt < retry_policy.max_attempts:
                    continue
                raise TTSRateLimitError(
                    f"{message} (after {attempt} attempts with linear retry)"
                )
            raise TTSError(message)

        _cleanup_partial_audio(output_path)
        raise TTSError(f"TTS failed for {output_path.name}: unexpected result")

    raise TTSRateLimitError(
        f"TTS failed for {output_path.name}: rate limited after {retry_policy.max_attempts} attempts"
    )


class AzureTTSProvider:
    """Provider wrapper that keeps Azure-specific code behind a small API."""

    def __init__(
        self,
        *,
        generated_audio_dir: Path = GENERATED_AUDIO_DIR,
        retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    ) -> None:
        self.generated_audio_dir = generated_audio_dir
        self.retry_policy = retry_policy

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="azure",
            supports_mandarin=True,
            supports_cantonese=True,
            supports_phoneme_control=True,
        )

    def is_valid_audio_tag(self, tag: str) -> bool:
        return is_valid_audio_tag(tag, generated_audio_dir=self.generated_audio_dir)

    def generate_mandarin(self, hanzi: str, pinyin: str, *, force: bool = False) -> str:
        safe_pinyin = pinyin.replace(" ", "_")
        filename = f"cmn_{hanzi}_{safe_pinyin}.mp3"
        output_path = self.generated_audio_dir / filename

        if is_valid_audio_file(output_path) and not force:
            return f"[sound:{filename}]"

        ssml = _ssml_mandarin_text(hanzi, pinyin)
        try:
            _generate_audio(ssml, output_path, retry_policy=self.retry_policy)
        except TTSError as error:
            if "Unknown phoneme" not in str(error):
                raise
            fallback = _ssml_plain(text=hanzi, voice=MANDARIN_VOICE, lang="zh-CN")
            _generate_audio(fallback, output_path, retry_policy=self.retry_policy)
        if not is_valid_audio_file(output_path):
            raise TTSError(f"TTS did not create audio for {filename}")
        return f"[sound:{filename}]"

    def generate_cantonese(
        self, hanzi: str, jyutping: str, *, force: bool = False
    ) -> str:
        safe_jyutping = jyutping.replace(" ", "_")
        filename = f"yue_{hanzi}_{safe_jyutping}.mp3"
        output_path = self.generated_audio_dir / filename

        if is_valid_audio_file(output_path) and not force:
            return f"[sound:{filename}]"

        ssml = _ssml_cantonese(hanzi, jyutping)
        try:
            _generate_audio(ssml, output_path, retry_policy=self.retry_policy)
        except TTSError as error:
            if "Unknown phoneme" not in str(error):
                raise
            fallback = _ssml_plain(text=hanzi, voice=CANTONESE_VOICE, lang="zh-HK")
            _generate_audio(fallback, output_path, retry_policy=self.retry_policy)
        if not is_valid_audio_file(output_path):
            raise TTSError(f"TTS did not create audio for {filename}")
        return f"[sound:{filename}]"

    def generate_example_audio(
        self, word: str, pinyin: str, *, force: bool = False
    ) -> str:
        filename = example_audio_filename(word, pinyin)
        output_path = self.generated_audio_dir / filename

        if is_valid_audio_file(output_path) and not force:
            return f"[sound:{filename}]"

        ssml = _ssml_mandarin_text(word, pinyin)
        try:
            _generate_audio(ssml, output_path, retry_policy=self.retry_policy)
        except TTSError as error:
            if "Unknown phoneme" not in str(error):
                raise
            fallback = _ssml_plain(text=word, voice=MANDARIN_VOICE, lang="zh-CN")
            _generate_audio(fallback, output_path, retry_policy=self.retry_policy)
        if not is_valid_audio_file(output_path):
            raise TTSError(f"TTS did not create audio for {filename}")
        return f"[sound:{filename}]"


_DEFAULT_PROVIDER = AzureTTSProvider()


def generate_mandarin(hanzi: str, pinyin: str, *, force: bool = False) -> str:
    return _DEFAULT_PROVIDER.generate_mandarin(hanzi, pinyin, force=force)


def generate_cantonese(hanzi: str, jyutping: str, *, force: bool = False) -> str:
    return _DEFAULT_PROVIDER.generate_cantonese(hanzi, jyutping, force=force)


def generate_example_audio(word: str, pinyin: str, *, force: bool = False) -> str:
    return _DEFAULT_PROVIDER.generate_example_audio(word, pinyin, force=force)

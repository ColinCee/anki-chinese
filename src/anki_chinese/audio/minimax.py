"""MiniMax speech provider via direct HTTP."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from ..config import GENERATED_AUDIO_DIR
from .errors import (
    TTSConfigurationError,
    TTSError,
    TTSRateLimitError,
    classify_http_error,
    is_rate_limited_message,
)
from .files import (
    is_valid_audio_file,
    is_valid_audio_tag,
    preview_mandarin_filename,
)
from .provider import ProviderCapabilities
from .rate_limit import RateLimiter, SlidingWindowRateLimiter
from .retry import RetryPolicy, synthesize_with_retry

load_dotenv()

# Repo-owned TTS defaults live here. They are not secrets and should only move
# into environment variables when a user intentionally needs to override them.
DEFAULT_MINIMAX_API_HOST = "https://api.minimax.io"
DEFAULT_MINIMAX_MODEL = "speech-2.8-turbo"
DEFAULT_MINIMAX_MANDARIN_VOICE_ID = "Chinese (Mandarin)_Cute_Spirit"
DEFAULT_MINIMAX_CANTONESE_VOICE_ID = "Cantonese_GentleLady"
DEFAULT_MINIMAX_MAX_REQUESTS_PER_WINDOW = 60
DEFAULT_MINIMAX_RATE_LIMIT_WINDOW_SECONDS = 60.0
DEFAULT_MINIMAX_RETRY_POLICY = RetryPolicy(
    rate_limit_retry_delay=15.0,
    max_attempts=5,
)
_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_AUDIO_SAMPLE_RATE = 32000
_DEFAULT_AUDIO_BITRATE = 128000
_SUCCESS_STATUS_CODE = 0


@dataclass(frozen=True)
class MiniMaxSettings:
    api_host: str = DEFAULT_MINIMAX_API_HOST
    model: str = DEFAULT_MINIMAX_MODEL
    mandarin_voice_id: str = DEFAULT_MINIMAX_MANDARIN_VOICE_ID
    cantonese_voice_id: str = DEFAULT_MINIMAX_CANTONESE_VOICE_ID
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls) -> MiniMaxSettings:
        return cls(
            api_host=_read_env("MINIMAX_API_HOST", DEFAULT_MINIMAX_API_HOST).rstrip("/"),
            model=_read_env("MINIMAX_TTS_MODEL", DEFAULT_MINIMAX_MODEL),
            mandarin_voice_id=_read_env(
                "MINIMAX_MANDARIN_VOICE_ID",
                DEFAULT_MINIMAX_MANDARIN_VOICE_ID,
            ),
            cantonese_voice_id=_read_env(
                "MINIMAX_CANTONESE_VOICE_ID",
                DEFAULT_MINIMAX_CANTONESE_VOICE_ID,
            ),
            timeout_seconds=_DEFAULT_TIMEOUT_SECONDS,
        )

    @property
    def endpoint(self) -> str:
        return f"{self.api_host}/v1/t2a_v2"


def _read_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _remove_partial_file(output_path: Path) -> None:
    if output_path.exists() and output_path.stat().st_size == 0:
        output_path.unlink()


def _configuration_guidance() -> str:
    return (
        "Check MINIMAX_API_KEY and MINIMAX_API_HOST. "
        "Global keys use https://api.minimax.io; mainland keys use https://api.minimaxi.com."
    )


def _voice_guidance() -> str:
    return (
        "Check MINIMAX_MANDARIN_VOICE_ID and MINIMAX_CANTONESE_VOICE_ID. "
        "The configured voice ID must exist for your MiniMax account and region."
    )


def _extract_status_details(payload: dict[str, Any]) -> tuple[int | None, str | None]:
    base_resp = payload.get("base_resp")
    if not isinstance(base_resp, dict):
        return None, None

    raw_code = base_resp.get("status_code")
    status_code: int | None = None
    if isinstance(raw_code, int):
        status_code = raw_code
    elif isinstance(raw_code, str):
        try:
            status_code = int(raw_code)
        except ValueError:
            status_code = None

    raw_message = base_resp.get("status_msg")
    status_message = raw_message.strip() if isinstance(raw_message, str) else None
    return status_code, status_message or None


def _build_request_payload(
    *,
    text: str,
    voice_id: str,
    language_boost: str,
    model: str,
) -> dict[str, object]:
    return {
        "model": model,
        "text": text,
        "stream": False,
        "language_boost": language_boost,
        "output_format": "hex",
        "voice_setting": {
            "voice_id": voice_id,
            "speed": 1.0,
            "vol": 1.0,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": _DEFAULT_AUDIO_SAMPLE_RATE,
            "bitrate": _DEFAULT_AUDIO_BITRATE,
            "format": "mp3",
            "channel": 1,
        },
    }


def _post_t2a_request(
    *,
    endpoint: str,
    api_key: str,
    payload: dict[str, object],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except HTTPError as error:
        # Pre-parse message from MiniMax's status envelope if possible
        raw_body = error.read().decode("utf-8", errors="replace")
        message = raw_body.strip() or f"MiniMax request failed with HTTP {error.code}"
        try:
            data = json.loads(raw_body)
            _, status_message = _extract_status_details(data)
            if status_message:
                message = status_message
        except json.JSONDecodeError:
            pass

        raise classify_http_error(
            error,
            provider_name="MiniMax",
            extract_message=message,
            config_hint=_configuration_guidance(),
        ) from error
    except URLError as error:
        raise TTSError(f"MiniMax request failed: {error.reason}") from error

    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise TTSError("MiniMax returned invalid JSON") from error


class MiniMaxTTSProvider:
    """Provider wrapper for MiniMax speech synthesis."""

    def __init__(
        self,
        *,
        generated_audio_dir: Path = GENERATED_AUDIO_DIR,
        settings: MiniMaxSettings | None = None,
        retry_policy: RetryPolicy = DEFAULT_MINIMAX_RETRY_POLICY,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.generated_audio_dir = generated_audio_dir
        self.settings = settings or MiniMaxSettings.from_env()
        self.retry_policy = retry_policy
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter(
            max_requests=DEFAULT_MINIMAX_MAX_REQUESTS_PER_WINDOW,
            window_seconds=DEFAULT_MINIMAX_RATE_LIMIT_WINDOW_SECONDS,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="minimax",
            supports_mandarin=True,
            supports_cantonese=True,
            supports_phoneme_control=False,
        )

    def is_valid_audio_tag(self, tag: str) -> bool:
        return is_valid_audio_tag(tag, generated_audio_dir=self.generated_audio_dir)

    def generate_mandarin(self, hanzi: str, pinyin: str, *, force: bool = False) -> str:
        safe_pinyin = pinyin.replace(" ", "_")
        filename = f"cmn_{hanzi}_{safe_pinyin}.mp3"
        return self._generate_file(
            filename=filename,
            text=hanzi,
            voice_id=self.settings.mandarin_voice_id,
            language_boost="Chinese",
            force=force,
        )

    def generate_plain_mandarin(self, text: str, *, force: bool = False) -> str:
        filename = preview_mandarin_filename(text)
        return self._generate_file(
            filename=filename,
            text=text,
            voice_id=self.settings.mandarin_voice_id,
            language_boost="Chinese",
            force=force,
        )

    def generate_cantonese(
        self, hanzi: str, jyutping: str, *, force: bool = False
    ) -> str:
        safe_jyutping = jyutping.replace(" ", "_")
        filename = f"yue_{hanzi}_{safe_jyutping}.mp3"
        return self._generate_file(
            filename=filename,
            text=hanzi,
            voice_id=self.settings.cantonese_voice_id,
            language_boost="Chinese,Yue",
            force=force,
        )

    def generate_sentence_audio(
        self, hanzi: str, sentence: str, *, force: bool = False
    ) -> str:
        from .files import sentence_audio_filename
        filename = sentence_audio_filename(hanzi, sentence)
        return self._generate_file(
            filename=filename,
            text=sentence,
            voice_id=self.settings.mandarin_voice_id,
            language_boost="Chinese",
            force=force,
        )

    def _generate_file(
        self,
        *,
        filename: str,
        text: str,
        voice_id: str,
        language_boost: str,
        force: bool,
    ) -> str:
        output_path = self.generated_audio_dir / filename
        if is_valid_audio_file(output_path) and not force:
            return f"[sound:{filename}]"

        api_key = os.getenv("MINIMAX_API_KEY", "").strip()
        if not api_key:
            raise TTSConfigurationError(
                "MINIMAX_API_KEY not set. Copy .env.example to .env and add your MiniMax key."
            )

        request_payload = _build_request_payload(
            text=text,
            voice_id=voice_id,
            language_boost=language_boost,
            model=self.settings.model,
        )

        def synthesize() -> bytes:
            response = _post_t2a_request(
                endpoint=self.settings.endpoint,
                api_key=api_key,
                payload=request_payload,
                timeout_seconds=self.settings.timeout_seconds,
            )
            return self._extract_audio_bytes(response)

        synthesize_with_retry(
            synthesize=synthesize,
            output_path=output_path,
            retry_policy=self.retry_policy,
            rate_limiter=self.rate_limiter,
            provider_name="MiniMax",
            cleanup=lambda: _remove_partial_file(output_path),
        )
        return f"[sound:{filename}]"

    def _extract_audio_bytes(self, response: dict[str, Any]) -> bytes:
        status_code, status_message = _extract_status_details(response)
        if status_code not in {None, _SUCCESS_STATUS_CODE}:
            message = status_message or f"MiniMax returned status_code={status_code}"
            lowered = message.lower()
            if "invalid api key" in lowered or "unauthorized" in lowered:
                raise TTSConfigurationError(f"{message} {_configuration_guidance()}")
            if "voice id not exist" in lowered:
                raise TTSConfigurationError(f"{message} {_voice_guidance()}")
            if is_rate_limited_message(message):
                raise TTSRateLimitError(message)
            raise TTSError(message)

        data = response.get("data")
        if not isinstance(data, dict):
            raise TTSError("MiniMax response did not include audio data")

        audio_hex = data.get("audio")
        if not isinstance(audio_hex, str) or not audio_hex:
            raise TTSError("MiniMax response did not include audio content")

        try:
            return bytes.fromhex(audio_hex)
        except ValueError as error:
            raise TTSError("MiniMax returned invalid hex audio") from error

"""Google Cloud Text-to-Speech provider (Chirp 3: HD) via direct HTTP."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2 import service_account

from ..config import GENERATED_AUDIO_DIR
from .errors import (
    TTSConfigurationError,
    TTSError,
    classify_http_error,
)
from .files import (
    is_valid_audio_file,
    is_valid_audio_tag,
    preview_mandarin_filename,
)
from .pinyin import diacritical_to_numbered
from .provider import ProviderCapabilities
from .rate_limit import RateLimiter, SlidingWindowRateLimiter
from .retry import RetryPolicy, synthesize_with_retry

load_dotenv()

DEFAULT_GOOGLE_TTS_ENDPOINT = "https://texttospeech.googleapis.com/v1/text:synthesize"
DEFAULT_MANDARIN_VOICE = "cmn-CN-Chirp3-HD-Leda"
DEFAULT_CANTONESE_VOICE = "yue-HK-Chirp3-HD-Leda"
DEFAULT_GOOGLE_MAX_REQUESTS_PER_WINDOW = 200
DEFAULT_GOOGLE_RATE_LIMIT_WINDOW_SECONDS = 60.0
DEFAULT_GOOGLE_RETRY_POLICY = RetryPolicy(
    rate_limit_retry_delay=10.0,
    max_attempts=3,
)
_DEFAULT_TIMEOUT_SECONDS = 30.0
_TTS_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


@dataclass(frozen=True)
class GoogleTTSSettings:
    endpoint: str = DEFAULT_GOOGLE_TTS_ENDPOINT
    mandarin_voice: str = DEFAULT_MANDARIN_VOICE
    cantonese_voice: str = DEFAULT_CANTONESE_VOICE
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls) -> GoogleTTSSettings:
        return cls(
            endpoint=os.getenv("GOOGLE_TTS_ENDPOINT", "").strip() or DEFAULT_GOOGLE_TTS_ENDPOINT,
            mandarin_voice=os.getenv("GOOGLE_TTS_MANDARIN_VOICE", "").strip()
            or DEFAULT_MANDARIN_VOICE,
            cantonese_voice=os.getenv("GOOGLE_TTS_CANTONESE_VOICE", "").strip()
            or DEFAULT_CANTONESE_VOICE,
        )


def _build_ssml_phoneme(text: str, alphabet: str, phoneme: str) -> str:
    """Build SSML with a <phoneme> tag for pronunciation control."""
    safe_ph = phoneme.replace("&", "&amp;").replace('"', "&quot;")
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<speak><phoneme alphabet="{alphabet}" ph="{safe_ph}">{safe_text}</phoneme></speak>'


def _build_synthesis_request(
    *,
    text: str | None = None,
    ssml: str | None = None,
    voice_name: str,
    language_code: str,
    custom_pronunciations: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the JSON body for texttospeech.googleapis.com/v1/text:synthesize."""
    input_field: dict[str, Any] = {}
    if ssml:
        input_field["ssml"] = ssml
    elif text:
        input_field["text"] = text
    else:
        raise ValueError("Either text or ssml must be provided")

    if custom_pronunciations:
        input_field["customPronunciations"] = {
            "pronunciations": custom_pronunciations,
        }

    return {
        "input": input_field,
        "voice": {
            "languageCode": language_code,
            "name": voice_name,
        },
        "audioConfig": {
            "audioEncoding": "MP3",
        },
    }


def _load_credentials(
    credentials_path: str | None = None,
) -> service_account.Credentials:
    """Load Google Cloud credentials via Application Default Credentials.

    Discovers credentials automatically from (in order):
    1. GOOGLE_APPLICATION_CREDENTIALS env var pointing to a service account JSON
    2. gcloud application-default login (run: gcloud auth application-default login)
    3. Compute Engine / Cloud Shell default service account
    """
    if credentials_path:
        path = Path(credentials_path)
        if not path.is_file():
            raise TTSConfigurationError(f"Service account file not found: {credentials_path}")
        try:
            return service_account.Credentials.from_service_account_file(
                str(path), scopes=_TTS_SCOPES
            )
        except Exception as exc:
            raise TTSConfigurationError(
                f"Failed to load service account credentials: {exc}"
            ) from exc

    # Fall back to Application Default Credentials
    import google.auth
    import google.auth.exceptions

    try:
        credentials, _ = google.auth.default(scopes=_TTS_SCOPES)
        return credentials  # type: ignore[return-value]
    except google.auth.exceptions.DefaultCredentialsError as exc:
        raise TTSConfigurationError(
            "No Google Cloud credentials found. Either:\n"
            "  1. Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json in .env\n"
            "  2. Run: gcloud auth application-default login"
        ) from exc


def _get_access_token(credentials: service_account.Credentials) -> str:
    """Return a valid access token, refreshing if needed."""
    if not credentials.valid:
        credentials.refresh(AuthRequest())
    token = credentials.token
    if not token:
        raise TTSConfigurationError("Failed to obtain access token from credentials.")
    return token


def _get_quota_project(credentials: Any) -> str | None:
    """Extract the quota project from credentials, if present."""
    return getattr(credentials, "quota_project_id", None)


def _post_synthesis_request(
    *,
    endpoint: str,
    access_token: str,
    payload: dict[str, Any],
    timeout_seconds: float,
    quota_project: str | None = None,
) -> dict[str, Any]:
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    if quota_project:
        headers["x-goog-user-project"] = quota_project

    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except HTTPError as error:
        raise classify_http_error(
            error,
            provider_name="Google TTS",
            config_hint="Check GOOGLE_APPLICATION_CREDENTIALS.",
        ) from error
    except URLError as error:
        raise TTSError(f"Google TTS request failed: {error.reason}") from error

    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise TTSError("Google TTS returned invalid JSON") from error


def _extract_audio_bytes(response: dict[str, Any]) -> bytes:
    audio_content = response.get("audioContent")
    if not isinstance(audio_content, str) or not audio_content:
        raise TTSError("Google TTS response did not include audioContent")
    return base64.b64decode(audio_content)


class GoogleTTSProvider:
    """Google Cloud TTS provider using Chirp 3: HD voices with phoneme control."""

    def __init__(
        self,
        *,
        generated_audio_dir: Path = GENERATED_AUDIO_DIR,
        settings: GoogleTTSSettings | None = None,
        retry_policy: RetryPolicy = DEFAULT_GOOGLE_RETRY_POLICY,
        rate_limiter: RateLimiter | None = None,
        credentials: service_account.Credentials | None = None,
    ) -> None:
        self.generated_audio_dir = generated_audio_dir
        self.settings = settings or GoogleTTSSettings.from_env()
        self.retry_policy = retry_policy
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter(
            max_requests=DEFAULT_GOOGLE_MAX_REQUESTS_PER_WINDOW,
            window_seconds=DEFAULT_GOOGLE_RATE_LIMIT_WINDOW_SECONDS,
        )
        self._credentials = credentials

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="google-chirp3-hd",
            supports_mandarin=True,
            supports_cantonese=True,
            supports_phoneme_control=True,
        )

    def is_valid_audio_tag(self, tag: str) -> bool:
        return is_valid_audio_tag(tag, generated_audio_dir=self.generated_audio_dir)

    def generate_mandarin(self, hanzi: str, pinyin: str, *, force: bool = False) -> str:
        safe_pinyin = pinyin.replace(" ", "_")
        filename = f"cmn_{hanzi}_{safe_pinyin}.mp3"
        numbered = diacritical_to_numbered(pinyin)
        payload = _build_synthesis_request(
            text=hanzi,
            voice_name=self.settings.mandarin_voice,
            language_code="cmn-CN",
            custom_pronunciations=[
                {
                    "phrase": hanzi,
                    "phoneticEncoding": "PHONETIC_ENCODING_PINYIN",
                    "pronunciation": numbered,
                }
            ],
        )
        return self._generate_file(filename=filename, payload=payload, force=force)

    def generate_plain_mandarin(self, text: str, *, force: bool = False) -> str:
        filename = preview_mandarin_filename(text)
        payload = _build_synthesis_request(
            text=text,
            voice_name=self.settings.mandarin_voice,
            language_code="cmn-CN",
        )
        return self._generate_file(filename=filename, payload=payload, force=force)

    def generate_cantonese(self, hanzi: str, jyutping: str, *, force: bool = False) -> str:
        safe_jyutping = jyutping.replace(" ", "_")
        filename = f"yue_{hanzi}_{safe_jyutping}.mp3"
        # Cantonese has no custom_pronunciations or phoneme SSML on Chirp 3 HD,
        # so we send plain text and rely on the model's native Cantonese ability.
        payload = _build_synthesis_request(
            text=hanzi,
            voice_name=self.settings.cantonese_voice,
            language_code="yue-HK",
        )
        return self._generate_file(filename=filename, payload=payload, force=force)

    def generate_sentence_audio(self, hanzi: str, sentence: str, *, force: bool = False) -> str:
        from .files import sentence_audio_filename

        filename = sentence_audio_filename(hanzi, sentence)
        payload = _build_synthesis_request(
            text=sentence,
            voice_name=self.settings.mandarin_voice,
            language_code="cmn-CN",
        )
        return self._generate_file(filename=filename, payload=payload, force=force)

    def _generate_file(
        self,
        *,
        filename: str,
        payload: dict[str, Any],
        force: bool,
    ) -> str:
        output_path = self.generated_audio_dir / filename
        if is_valid_audio_file(output_path) and not force:
            return f"[sound:{filename}]"

        credentials = self._get_credentials()
        access_token = _get_access_token(credentials)
        quota_project = _get_quota_project(credentials)

        def synthesize() -> bytes:
            response = _post_synthesis_request(
                endpoint=self.settings.endpoint,
                access_token=access_token,
                payload=payload,
                timeout_seconds=self.settings.timeout_seconds,
                quota_project=quota_project,
            )
            return _extract_audio_bytes(response)

        synthesize_with_retry(
            synthesize=synthesize,
            output_path=output_path,
            retry_policy=self.retry_policy,
            rate_limiter=self.rate_limiter,
            provider_name="Google TTS",
        )
        return f"[sound:{filename}]"

    def _get_credentials(self) -> service_account.Credentials:
        if self._credentials is None:
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip() or None
            self._credentials = _load_credentials(creds_path)
        return self._credentials

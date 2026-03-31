import base64
from pathlib import Path
from unittest.mock import MagicMock

from anki_chinese.audio import google_tts as gtts
from anki_chinese.audio.rate_limit import NoOpRateLimiter
from anki_chinese.audio.retry import RetryPolicy

FAKE_MP3 = b"ID3fake-audio-content"
FAKE_RESPONSE = {"audioContent": base64.b64encode(FAKE_MP3).decode()}


def _fake_credentials() -> MagicMock:
    creds = MagicMock()
    creds.valid = True
    creds.token = "fake-token"
    return creds


def _make_provider(tmp_path: Path, **kwargs) -> gtts.GoogleTTSProvider:
    return gtts.GoogleTTSProvider(
        generated_audio_dir=tmp_path,
        settings=gtts.GoogleTTSSettings(
            mandarin_voice="cmn-CN-Chirp3-HD-Leda",
            cantonese_voice="yue-HK-Chirp3-HD-Leda",
        ),
        retry_policy=RetryPolicy(rate_limit_retry_delay=0.0, max_attempts=1),
        rate_limiter=NoOpRateLimiter(),
        credentials=_fake_credentials(),
        **kwargs,
    )


def test_provider_reports_capabilities(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path)
    caps = provider.capabilities()
    assert caps.name == "google-chirp3-hd"
    assert caps.supports_mandarin
    assert caps.supports_cantonese
    assert caps.supports_phoneme_control


def test_generate_mandarin_uses_custom_pronunciations(
    tmp_path: Path, monkeypatch
) -> None:
    provider = _make_provider(tmp_path)
    captured: dict[str, object] = {}

    def fake_post(*, endpoint, access_token, payload, timeout_seconds, quota_project=None):
        captured["payload"] = payload
        return FAKE_RESPONSE

    monkeypatch.setattr(gtts, "_post_synthesis_request", fake_post)
    monkeypatch.setattr(gtts, "_get_access_token", lambda creds: "fake-token")

    tag = provider.generate_mandarin("一", "yī")

    assert tag == "[sound:cmn_一_yī.mp3]"
    assert (tmp_path / "cmn_一_yī.mp3").read_bytes() == FAKE_MP3

    payload = captured["payload"]
    assert payload["voice"]["name"] == "cmn-CN-Chirp3-HD-Leda"
    assert payload["voice"]["languageCode"] == "cmn-CN"
    assert payload["audioConfig"]["audioEncoding"] == "MP3"

    # custom_pronunciations with numbered pinyin
    prons = payload["input"]["customPronunciations"]["pronunciations"]
    assert len(prons) == 1
    assert prons[0]["phrase"] == "一"
    assert prons[0]["phoneticEncoding"] == "PHONETIC_ENCODING_PINYIN"
    assert prons[0]["pronunciation"] == "yi1"


def test_generate_cantonese_uses_ssml_phoneme(
    tmp_path: Path, monkeypatch
) -> None:
    provider = _make_provider(tmp_path)
    captured: dict[str, object] = {}

    def fake_post(*, endpoint, access_token, payload, timeout_seconds, quota_project=None):
        captured["payload"] = payload
        return FAKE_RESPONSE

    monkeypatch.setattr(gtts, "_post_synthesis_request", fake_post)
    monkeypatch.setattr(gtts, "_get_access_token", lambda creds: "fake-token")

    tag = provider.generate_cantonese("一", "jat1")

    assert tag == "[sound:yue_一_jat1.mp3]"
    assert (tmp_path / "yue_一_jat1.mp3").read_bytes() == FAKE_MP3

    payload = captured["payload"]
    assert payload["voice"]["name"] == "yue-HK-Chirp3-HD-Leda"
    assert payload["voice"]["languageCode"] == "yue-HK"

    # Cantonese uses plain text (no phoneme control available on Chirp 3 HD)
    assert payload["input"]["text"] == "一"
    assert "ssml" not in payload["input"]


def test_generate_plain_mandarin_no_pronunciation(
    tmp_path: Path, monkeypatch
) -> None:
    provider = _make_provider(tmp_path)
    captured: dict[str, object] = {}

    def fake_post(*, endpoint, access_token, payload, timeout_seconds, quota_project=None):
        captured["payload"] = payload
        return FAKE_RESPONSE

    monkeypatch.setattr(gtts, "_post_synthesis_request", fake_post)
    monkeypatch.setattr(gtts, "_get_access_token", lambda creds: "fake-token")

    tag = provider.generate_plain_mandarin("你好世界")

    assert "preview_cmn_" in tag
    assert "customPronunciations" not in captured["payload"]["input"]


def test_existing_file_skips_request(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path)
    existing = tmp_path / "cmn_一_yī.mp3"
    existing.write_bytes(b"ID3")

    tag = provider.generate_mandarin("一", "yī")

    assert tag == "[sound:cmn_一_yī.mp3]"


def test_missing_credentials_raises_configuration_error(tmp_path: Path, monkeypatch) -> None:
    provider = gtts.GoogleTTSProvider(
        generated_audio_dir=tmp_path,
        settings=gtts.GoogleTTSSettings(),
        retry_policy=RetryPolicy(rate_limit_retry_delay=0.0, max_attempts=1),
        rate_limiter=NoOpRateLimiter(),
    )
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

    # Mock google.auth.default to raise so we don't depend on host credentials
    import google.auth
    import google.auth.exceptions

    def _no_creds(*a, **kw):
        raise google.auth.exceptions.DefaultCredentialsError("no creds")

    monkeypatch.setattr(google.auth, "default", _no_creds)

    try:
        provider.generate_mandarin("一", "yī")
    except gtts.TTSConfigurationError as e:
        assert "credentials" in str(e).lower()
    else:
        raise AssertionError("Expected TTSConfigurationError")


def test_build_ssml_phoneme_escapes_special_chars() -> None:
    ssml = gtts._build_ssml_phoneme("A&B", "ipa", 'ph"val')
    assert "&amp;" in ssml
    assert "&quot;" in ssml


def test_extract_audio_bytes_decodes_base64() -> None:
    raw = b"hello-audio"
    response = {"audioContent": base64.b64encode(raw).decode()}
    assert gtts._extract_audio_bytes(response) == raw


def test_extract_audio_bytes_raises_on_missing_content() -> None:
    try:
        gtts._extract_audio_bytes({})
    except gtts.TTSError as e:
        assert "audioContent" in str(e)
    else:
        raise AssertionError("Expected TTSError")

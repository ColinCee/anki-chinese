from pathlib import Path

from anki_chinese.audio import minimax as tts
from anki_chinese.audio.retry import RetryPolicy


def test_build_request_payload_uses_expected_defaults() -> None:
    payload = tts._build_request_payload(
        text="你好",
        voice_id="mandarin-voice",
        language_boost="Chinese",
        model="speech-2.8-turbo",
    )

    assert payload["model"] == "speech-2.8-turbo"
    assert payload["text"] == "你好"
    assert payload["stream"] is False
    assert payload["output_format"] == "hex"
    assert payload["language_boost"] == "Chinese"
    assert payload["voice_setting"] == {
        "voice_id": "mandarin-voice",
        "speed": 1.0,
        "vol": 1.0,
        "pitch": 0,
    }
    assert payload["audio_setting"] == {
        "sample_rate": 32000,
        "bitrate": 128000,
        "format": "mp3",
        "channel": 1,
    }


def test_minimax_provider_reports_capabilities() -> None:
    provider = tts.MiniMaxTTSProvider()

    assert provider.capabilities().supports_mandarin
    assert provider.capabilities().supports_cantonese
    assert not provider.capabilities().supports_phoneme_control


def test_generate_mandarin_uses_existing_valid_file_without_request(tmp_path: Path) -> None:
    provider = tts.MiniMaxTTSProvider(generated_audio_dir=tmp_path)
    existing = tmp_path / "cmn_一_yī.mp3"
    existing.write_bytes(b"ID3")

    tag = provider.generate_mandarin("一", "yī")

    assert tag == "[sound:cmn_一_yī.mp3]"


def test_generate_mandarin_posts_expected_request_and_writes_audio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    provider = tts.MiniMaxTTSProvider(
        generated_audio_dir=tmp_path,
        settings=tts.MiniMaxSettings(
            api_host="https://api.minimax.io",
            model="speech-2.8-turbo",
            mandarin_voice_id="mandarin-voice",
            cantonese_voice_id="cantonese-voice",
            timeout_seconds=5.0,
        ),
        retry_policy=RetryPolicy(request_interval=0.0, rate_limit_retry_delay=0.0, max_attempts=1),
    )
    captured: dict[str, object] = {}

    def fake_post_t2a_request(
        *,
        endpoint: str,
        api_key: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured["endpoint"] = endpoint
        captured["api_key"] = api_key
        captured["payload"] = payload
        captured["timeout_seconds"] = timeout_seconds
        return {
            "data": {"audio": "494433"},
            "base_resp": {"status_code": 0, "status_msg": ""},
        }

    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setattr(tts, "_post_t2a_request", fake_post_t2a_request)

    tag = provider.generate_mandarin("你", "nǐ")

    assert tag == "[sound:cmn_你_nǐ.mp3]"
    assert (tmp_path / "cmn_你_nǐ.mp3").read_bytes() == b"ID3"
    assert captured["endpoint"] == "https://api.minimax.io/v1/t2a_v2"
    assert captured["api_key"] == "test-key"
    assert captured["timeout_seconds"] == 5.0
    assert captured["payload"] == {
        "model": "speech-2.8-turbo",
        "text": "你",
        "stream": False,
        "language_boost": "Chinese",
        "output_format": "hex",
        "voice_setting": {
            "voice_id": "mandarin-voice",
            "speed": 1.0,
            "vol": 1.0,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
    }


def test_generate_cantonese_uses_yue_language_boost(
    tmp_path: Path,
    monkeypatch,
) -> None:
    provider = tts.MiniMaxTTSProvider(
        generated_audio_dir=tmp_path,
        settings=tts.MiniMaxSettings(
            mandarin_voice_id="mandarin-voice",
            cantonese_voice_id="cantonese-voice",
        ),
        retry_policy=RetryPolicy(request_interval=0.0, rate_limit_retry_delay=0.0, max_attempts=1),
    )
    captured: dict[str, object] = {}

    def fake_post_t2a_request(
        *,
        endpoint: str,
        api_key: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured["payload"] = payload
        return {
            "data": {"audio": "494433"},
            "base_resp": {"status_code": 0, "status_msg": ""},
        }

    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setattr(tts, "_post_t2a_request", fake_post_t2a_request)

    tag = provider.generate_cantonese("行", "haang4")

    assert tag == "[sound:yue_行_haang4.mp3]"
    assert captured["payload"]["language_boost"] == "Chinese,Yue"
    assert captured["payload"]["voice_setting"]["voice_id"] == "cantonese-voice"


def test_generate_plain_mandarin_uses_preview_filename(
    tmp_path: Path,
    monkeypatch,
) -> None:
    provider = tts.MiniMaxTTSProvider(
        generated_audio_dir=tmp_path,
        retry_policy=RetryPolicy(request_interval=0.0, rate_limit_retry_delay=0.0, max_attempts=1),
    )

    def fake_post_t2a_request(
        *,
        endpoint: str,
        api_key: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> dict[str, object]:
        return {
            "data": {"audio": "494433"},
            "base_resp": {"status_code": 0, "status_msg": ""},
        }

    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setattr(tts, "_post_t2a_request", fake_post_t2a_request)

    tag = provider.generate_plain_mandarin("你好 test")

    assert tag == "[sound:preview_cmn_你好_test.mp3]"
    assert (tmp_path / "preview_cmn_你好_test.mp3").read_bytes() == b"ID3"


def test_extract_audio_bytes_maps_missing_voice_to_configuration_error() -> None:
    provider = tts.MiniMaxTTSProvider()

    try:
        provider._extract_audio_bytes(
            {
                "base_resp": {
                    "status_code": 1004,
                    "status_msg": "voice id not exist",
                }
            }
        )
    except tts.TTSConfigurationError as error:
        assert "MINIMAX_MANDARIN_VOICE_ID" in str(error)
        assert "MINIMAX_CANTONESE_VOICE_ID" in str(error)
    else:
        raise AssertionError("Expected TTSConfigurationError")

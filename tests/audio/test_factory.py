from unittest.mock import patch

import pytest

from anki_chinese.audio.factory import build_tts_provider


@patch("anki_chinese.audio.google_tts.GoogleTTSProvider")
def test_build_google_provider(mock_cls, tmp_path):
    provider = build_tts_provider(generated_audio_dir=tmp_path, provider_name="google")

    mock_cls.assert_called_once_with(generated_audio_dir=tmp_path)
    assert provider is mock_cls.return_value


@patch("anki_chinese.audio.minimax.MiniMaxTTSProvider")
def test_build_minimax_provider(mock_cls, tmp_path):
    provider = build_tts_provider(generated_audio_dir=tmp_path, provider_name="minimax")

    mock_cls.assert_called_once_with(generated_audio_dir=tmp_path)
    assert provider is mock_cls.return_value


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown TTS provider"):
        build_tts_provider(provider_name="unknown")

from pathlib import Path

from anki_chinese.audio import azure as tts
from anki_chinese.audio import files as audio_files


def test_to_sapi_pinyin_handles_tones_and_umlaut() -> None:
    assert tts._to_sapi_pinyin('yī') == 'yi 1'
    assert tts._to_sapi_pinyin('lǜ') == 'lv 4'
    assert tts._to_sapi_pinyin('de') == 'de 5'


def test_to_sapi_jyutping_inserts_space_before_tone() -> None:
    assert tts._to_sapi_jyutping('gau2') == 'gau 2'
    assert tts._to_sapi_jyutping('gau 2') == 'gau 2'


def test_ssml_mandarin_text_falls_back_to_plain_when_lengths_do_not_match() -> None:
    ssml = tts._ssml_mandarin_text('你好', 'nǐ')

    assert '<phoneme' not in ssml
    assert '>你好<' in ssml


def test_example_audio_filename_and_valid_audio_tag(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(audio_files, 'GENERATED_AUDIO_DIR', tmp_path)
    filename = audio_files.example_audio_filename('你好', 'nǐ hǎo')
    (tmp_path / filename).write_bytes(b'ID3')

    assert filename == 'cmn_你好_nǐ_hǎo.mp3'
    assert audio_files.is_valid_audio_tag(f'[sound:{filename}]')
    assert not audio_files.is_valid_audio_tag('[sound:missing.mp3]')


def test_is_rate_limited_message_detects_known_signals() -> None:
    assert tts._is_rate_limited_message('429 Too Many Requests')
    assert tts._is_rate_limited_message('too many requests from upstream')
    assert not tts._is_rate_limited_message('network timeout')


def test_azure_provider_reports_capabilities() -> None:
    provider = tts.AzureTTSProvider()

    assert provider.capabilities().supports_mandarin
    assert provider.capabilities().supports_cantonese
    assert provider.capabilities().supports_phoneme_control


def test_generate_mandarin_uses_existing_valid_file_without_sdk_call(tmp_path: Path) -> None:
    provider = tts.AzureTTSProvider(generated_audio_dir=tmp_path)
    existing = tmp_path / 'cmn_一_yī.mp3'
    existing.write_bytes(b'ID3')

    tag = provider.generate_mandarin('一', 'yī')

    assert tag == '[sound:cmn_一_yī.mp3]'

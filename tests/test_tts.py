from pathlib import Path

from anki_chinese.audio import azure as tts
from anki_chinese.audio import files as audio_files


def test_to_sapi_pinyin_handles_tones_and_umlaut() -> None:
    assert tts._to_sapi_pinyin("yī") == "yi 1"
    assert tts._to_sapi_pinyin("lǜ") == "lv 4"
    assert tts._to_sapi_pinyin("de") == "de 5"


def test_to_sapi_jyutping_inserts_space_before_tone() -> None:
    assert tts._to_sapi_jyutping("gau2") == "gau 2"
    assert tts._to_sapi_jyutping("gau 2") == "gau 2"


def test_ssml_mandarin_text_falls_back_to_plain_when_lengths_do_not_match() -> None:
    ssml = tts._ssml_mandarin_text("你好", "nǐ")

    assert "<phoneme" not in ssml
    assert ">你好<" in ssml


def test_example_audio_filename_and_valid_audio_tag(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(audio_files, "GENERATED_MEDIA_DIR", tmp_path)
    filename = audio_files.example_audio_filename("你好", "nǐ hǎo")
    (tmp_path / filename).write_bytes(b"ID3")

    assert filename == "cmn_你好_nǐ_hǎo.mp3"
    assert audio_files.is_valid_audio_tag(f"[sound:{filename}]")
    assert not audio_files.is_valid_audio_tag("[sound:missing.mp3]")

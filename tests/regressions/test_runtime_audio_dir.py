import anki_chinese.audio.files as audio_files


def test_is_valid_audio_tag_honors_runtime_audio_directory_argument(tmp_path, monkeypatch) -> None:
    filename = "cmn_你好_nǐ_hǎo.mp3"
    (tmp_path / filename).write_bytes(b"ID3")
    monkeypatch.setattr(audio_files, "GENERATED_AUDIO_DIR", tmp_path / "wrong-location")

    assert audio_files.is_valid_audio_tag(
        f"[sound:{filename}]",
        generated_audio_dir=tmp_path,
    )

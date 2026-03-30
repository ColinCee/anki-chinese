from pathlib import Path

import anki_chinese.deck as deck_module
from anki_chinese.deck import build_deck
from anki_chinese.notes import CharacterNote


def test_build_deck_writes_apkg_file(tmp_path: Path, monkeypatch) -> None:
    audio_dir = tmp_path / "data" / "build" / "audio" / "generated"
    audio_dir.mkdir(parents=True)
    (audio_dir / "cmn_一_yī.mp3").write_bytes(b"ID3")

    deck_output_dir = tmp_path / "data" / "build" / "decks"
    monkeypatch.setattr(deck_module, "GENERATED_AUDIO_DIR", audio_dir)
    monkeypatch.setattr(deck_module, "DECK_OUTPUT_DIR", deck_output_dir)

    note = CharacterNote(
        hanzi="一",
        keyword="one",
        pinyin="yī",
        jyutping="jat1",
        mandarin_audio="[sound:cmn_一_yī.mp3]",
        lesson="Lesson 1",
    )

    output_path = build_deck([note])

    assert output_path == deck_output_dir / "chinese_rsh.apkg"
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_build_deck_empty_notes_produces_valid_apkg(tmp_path: Path, monkeypatch) -> None:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True)
    deck_output_dir = tmp_path / "decks"
    monkeypatch.setattr(deck_module, "GENERATED_AUDIO_DIR", audio_dir)
    monkeypatch.setattr(deck_module, "DECK_OUTPUT_DIR", deck_output_dir)

    output_path = build_deck([])

    assert output_path.exists()
    assert output_path.suffix == ".apkg"
    assert output_path.stat().st_size > 0


def test_build_deck_field_count_matches_config(tmp_path: Path, monkeypatch) -> None:
    from anki_chinese.config import FIELDS

    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True)
    deck_output_dir = tmp_path / "decks"
    monkeypatch.setattr(deck_module, "GENERATED_AUDIO_DIR", audio_dir)
    monkeypatch.setattr(deck_module, "DECK_OUTPUT_DIR", deck_output_dir)

    note = CharacterNote(hanzi="人", keyword="person", pinyin="rén")
    fields_list = note.to_fields_list()

    assert len(fields_list) == len(FIELDS)

    build_deck([note])


def test_build_deck_multiple_notes(tmp_path: Path, monkeypatch) -> None:
    import zipfile

    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True)
    deck_output_dir = tmp_path / "decks"
    monkeypatch.setattr(deck_module, "GENERATED_AUDIO_DIR", audio_dir)
    monkeypatch.setattr(deck_module, "DECK_OUTPUT_DIR", deck_output_dir)

    notes = [
        CharacterNote(hanzi="日", keyword="day", pinyin="rì", lesson="Lesson 1"),
        CharacterNote(hanzi="月", keyword="month", pinyin="yuè", lesson="Lesson 1"),
        CharacterNote(hanzi="星", keyword="star", pinyin="xīng", lesson="Lesson 2"),
    ]

    output_path = build_deck(notes)

    assert output_path.exists()
    with zipfile.ZipFile(output_path) as zf:
        names = zf.namelist()
        assert any(name.endswith(".anki2") or name == "collection.anki2" for name in names)


def test_build_deck_includes_audio_media(tmp_path: Path, monkeypatch) -> None:
    import zipfile

    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True)
    (audio_dir / "cmn_人_rén.mp3").write_bytes(b"ID3fake")
    (audio_dir / "yue_人_jan4.mp3").write_bytes(b"ID3fake")

    deck_output_dir = tmp_path / "decks"
    monkeypatch.setattr(deck_module, "GENERATED_AUDIO_DIR", audio_dir)
    monkeypatch.setattr(deck_module, "DECK_OUTPUT_DIR", deck_output_dir)

    note = CharacterNote(
        hanzi="人",
        keyword="person",
        pinyin="rén",
        mandarin_audio="[sound:cmn_人_rén.mp3]",
        cantonese_audio="[sound:yue_人_jan4.mp3]",
    )

    output_path = build_deck([note])

    with zipfile.ZipFile(output_path) as zf:
        media_json = zf.read("media")
        media_map = __import__("json").loads(media_json)
        packed_filenames = set(media_map.values())
        assert "cmn_人_rén.mp3" in packed_filenames
        assert "yue_人_jan4.mp3" in packed_filenames

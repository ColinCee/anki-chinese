from pathlib import Path

from anki_chinese.deck import build_deck
import anki_chinese.deck as deck_module
from anki_chinese.models import CharacterNote


def test_build_deck_writes_apkg_file(tmp_path: Path, monkeypatch) -> None:
    media_dir = tmp_path / "generated-media"
    media_dir.mkdir()
    (media_dir / "cmn_一_yī.mp3").write_bytes(b"ID3")

    output_dir = tmp_path / "output"
    monkeypatch.setattr(deck_module, "GENERATED_MEDIA_DIR", media_dir)
    monkeypatch.setattr(deck_module, "OUTPUT_DIR", output_dir)

    note = CharacterNote(
        hanzi="一",
        keyword="one",
        pinyin="yī",
        jyutping="jat1",
        mandarin_audio="[sound:cmn_一_yī.mp3]",
        lesson="Lesson 1",
    )

    output_path = build_deck([note])

    assert output_path == output_dir / "chinese_rsh.apkg"
    assert output_path.exists()
    assert output_path.stat().st_size > 0

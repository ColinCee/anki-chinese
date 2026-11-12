import json
import sqlite3
from datetime import date
from pathlib import Path

from anki_chinese import tutor
from anki_chinese.config import MODEL_ID


def _collection(path: Path, notes: list[tuple[str, int, int]]) -> Path:
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE notes (id INTEGER, mid INTEGER, flds TEXT)")
    db.execute("CREATE TABLE cards (nid INTEGER, reps INTEGER, queue INTEGER)")
    for note_id, (hanzi, reps, queue) in enumerate(notes, start=1):
        db.execute("INSERT INTO notes VALUES (?, ?, ?)", (note_id, MODEL_ID, f"{hanzi}\x1fmeaning"))
        db.execute("INSERT INTO cards VALUES (?, ?, ?)", (note_id, reps, queue))
    db.execute("INSERT INTO notes VALUES (99, 1, '外\x1fother note type')")
    db.execute("INSERT INTO cards VALUES (99, 5, 0)")
    db.commit()
    db.close()
    return path


def test_read_collection_splits_studied_unlocked_and_suspended(tmp_path: Path) -> None:
    path = _collection(
        tmp_path / "collection.anki2",
        [("你", 3, 2), ('<img src="4e2d.gif">', 1, 2), ("好", 0, 0), ("学", 0, -1)],
    )

    studied, unlocked = tutor.read_collection(path)

    assert studied == {"你", "中"}
    assert unlocked == {"好"}


def test_new_in_ignores_known_characters_and_punctuation() -> None:
    known = tutor.KnownCharacters(
        studied=frozenset("你好"), unlocked=frozenset("学"), source="t", updated="t"
    )

    assert known.new_in("你好！我学中文，2026 OK 中。") == ["我", "中", "文"]


def test_load_known_uses_todays_cache_without_reading_anki(tmp_path: Path, monkeypatch) -> None:
    cache = tmp_path / "known.json"
    payload = {
        "updated": f"{date.today()}T08:00:00",
        "source": "s",
        "studied": "你",
        "unlocked": "",
    }
    cache.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(tutor, "refresh_known", lambda path: (_ for _ in ()).throw(AssertionError))

    assert tutor.load_known(cache).studied == {"你"}


def test_log_new_feeds_recent_new(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    tutor.log_new({"处": "好处很多。", "模": "新模型"}, log)
    tutor.log_new({"处": "又是处。"}, log)

    assert tutor.recent_new(path=log) == ["处", "模"]

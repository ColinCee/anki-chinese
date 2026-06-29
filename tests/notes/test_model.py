from anki_chinese.notes import CharacterNote


def test_character_note_round_trips_through_dict_and_ignores_unknown_fields(full_note) -> None:
    restored = CharacterNote.from_dict({**full_note.to_dict(), "unknown": "ignored"})

    assert restored == full_note

def test_sentence_fields_round_trip_through_dict() -> None:
    note = CharacterNote(
        hanzi="水",
        meaning="water",
        sentence="我喝水。",
        sentence_pinyin="wǒ hē shuǐ.",
        sentence_english="I drink water.",
        sentence_audio="[sound:cmn_sentence_我喝水。.mp3]",
    )

    restored = CharacterNote.from_dict(note.to_dict())

    assert restored.sentence == "我喝水。"
    assert restored.sentence_pinyin == "wǒ hē shuǐ."
    assert restored.sentence_english == "I drink water."
    assert restored.sentence_audio == "[sound:cmn_sentence_我喝水。.mp3]"


def test_to_fields_list_includes_sentence_fields() -> None:
    note = CharacterNote(
        hanzi="水",
        meaning="water",
        sentence="我喝水。",
        sentence_pinyin="wǒ hē shuǐ.",
        sentence_english="I drink water.",
        sentence_audio="[sound:cmn_sentence_我喝水。.mp3]",
    )
    fields = note.to_fields_list()

    # Sentence fields should all be present in the fields list
    assert "我喝水。" in fields
    assert "wǒ hē shuǐ." in fields
    assert "I drink water." in fields
    assert "[sound:cmn_sentence_我喝水。.mp3]" in fields

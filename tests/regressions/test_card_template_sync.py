"""Card identity, reading prompts, and progressive disclosure."""

import xml.etree.ElementTree as ET

import chevron
import pytest

from anki_chinese.config import CARDS_DIR, FIELDS, MODEL_ID
from anki_chinese.deck import _build_model


def _render(template: str, **fields: str) -> ET.Element:
    html = (CARDS_DIR / template).read_text(encoding="utf-8")
    return ET.fromstring(chevron.render(html, fields))


def _with_class(root: ET.Element, name: str) -> list[ET.Element]:
    return [node for node in root.iter() if name in node.get("class", "").split()]


def test_recognition_and_recall_backs_are_identical() -> None:
    recognition = (CARDS_DIR / "recognition_back.html").read_text(encoding="utf-8")
    recall = (CARDS_DIR / "recall_back.html").read_text(encoding="utf-8")

    assert recognition == recall, (
        "recognition_back.html and recall_back.html have drifted — "
        "both card types should share the same back template"
    )


@pytest.mark.parametrize("template", ["recognition_back.html", "recall_back.html"])
def test_sentence_helpers_are_separate_and_collapsed_by_default(template: str) -> None:
    root = _render(
        template,
        Hanzi="水",
        Sentence="我喝水。",
        SentencePinyin="wǒ hē shuǐ",
        SentenceEnglish="I drink water.",
        Story="A memory aid.",
        StrokeOrder="Stroke diagram",
    )

    details = list(root.iter("details"))
    assert len(details) == 4
    assert all("open" not in node.attrib for node in details)
    assert _with_class(details[0], "context-pinyin")[0].text == "wǒ hē shuǐ"
    assert _with_class(details[1], "context-meaning")[0].text == "I drink water."
    sentence = _with_class(root, "context-chars")[0]
    assert sentence.text == "我喝水。"
    assert all(sentence not in list(node.iter()) for node in details)
    assert list(root.iter()).index(sentence) < list(root.iter()).index(details[0])


@pytest.mark.parametrize("template", ["recognition_back.html", "recall_back.html"])
@pytest.mark.parametrize("sentence", ["我喝水。", ""])
def test_meaning_is_collapsed_after_chinese_reading(template: str, sentence: str) -> None:
    root = _render(template, Hanzi="水", Meaning="water; in 水杯: drinking glass", Sentence=sentence)
    meaning_toggle = _with_class(root, "meaning-toggle")[0]

    assert meaning_toggle.tag == "details"
    assert "open" not in meaning_toggle.attrib
    assert meaning_toggle.findtext("summary") == "Show meaning & usage"
    assert _with_class(meaning_toggle, "meaning")[0].text == "water; in 水杯: drinking glass"
    assert "hero" in root[0].get("class", "").split()
    if sentence:
        assert _with_class(root[1], "context-chars")[0].text == sentence
        assert root[2] is meaning_toggle
    else:
        assert root[1] is meaning_toggle


def test_recognition_front_includes_unaided_sentence_without_answer_fields() -> None:
    root = _render(
        "recognition_front.html",
        Hanzi="水",
        Sentence="我喝水。",
        Pinyin="shuǐ",
        Meaning="water",
        SentenceEnglish="I drink water.",
        SentencePinyin="wǒ hē shuǐ",
    )
    text = "".join(root.itertext())
    assert "水" in text
    assert "我喝水。" in text
    assert not list(root.iter("details"))
    for answer in ("shuǐ", "water", "I drink water.", "wǒ hē shuǐ"):
        assert answer not in text


def test_listening_front_keeps_chinese_hidden_and_offers_audio_and_hints() -> None:
    root = _render(
        "recall_front.html",
        Hanzi="水",
        Sentence="我喝水。",
        MandarinAudio="[sound:character.mp3]",
        SentenceAudio="[sound:sentence.mp3]",
        Pinyin="shuǐ",
        SentenceEnglish="I drink water.",
    )
    text = "".join(root.itertext())
    assert "水" not in text
    assert "[sound:character.mp3]" in text
    assert "[sound:sentence.mp3]" in text
    details = list(root.iter("details"))
    assert len(details) == 2
    assert all("open" not in node.attrib for node in details)
    assert "shuǐ" in "".join(details[0].itertext())
    assert "I drink water." in "".join(details[1].itertext())


@pytest.mark.parametrize(
    "template", ["recognition_front.html", "recognition_back.html", "recall_back.html"]
)
def test_missing_optional_content_does_not_leave_empty_sections(template: str) -> None:
    root = _render(template, Hanzi="水", Pinyin="shuǐ")
    assert not _with_class(root, "context-chars")
    assert not _with_class(root, "context-audio")
    assert not _with_class(root, "memory-section")
    assert not _with_class(root, "meaning-toggle")
    assert not list(root.iter("details"))
    assert not list(root.iter("button"))


def test_listening_without_recordings_has_a_clear_fallback() -> None:
    root = _render("recall_front.html", Hanzi="水", Sentence="我喝水。", Pinyin="shuǐ")
    assert "No character recording yet" in "".join(root.itertext())
    assert not _with_class(root, "listen-audio")
    assert not _with_class(root, "reading-section")
    assert len(list(root.iter("details"))) == 1

    root = _render("recall_front.html", Hanzi="水")
    assert "No pinyin hint available" in "".join(root.itertext())


def test_cantonese_play_button_requires_both_pronunciation_and_audio() -> None:
    for fields in ({}, {"Jyutping": "seoi2"}, {"CantoneseAudio": "[sound:yue.mp3]"}):
        assert not list(_render("recognition_back.html", Hanzi="水", **fields).iter("button"))

    root = _render(
        "recognition_back.html", Hanzi="水", Jyutping="seoi2", CantoneseAudio="[sound:yue.mp3]"
    )
    assert len(_with_class(root, "play-cantonese")) == 1
    # Cantonese remains click-to-play, not an Anki auto-play sound tag.
    assert "[sound:yue.mp3]" not in "".join(root.itertext())


def test_redesign_preserves_model_identity_and_wires_reading_enhancement() -> None:
    model = _build_model()
    assert model.model_id == MODEL_ID
    assert [field["name"] for field in model.fields] == FIELDS
    assert [template["name"] for template in model.templates] == ["Recognition", "Listening"]
    reading_script = (CARDS_DIR / "reading_script.html").read_text(encoding="utf-8")
    assert model.templates[0]["qfmt"].endswith(reading_script)
    assert all(template["afmt"].endswith(reading_script) for template in model.templates)
    assert model.templates[0]["afmt"] == model.templates[1]["afmt"]

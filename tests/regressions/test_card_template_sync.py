"""Both card types must use the same back template."""

from anki_chinese.config import CARDS_DIR


def test_recognition_and_recall_backs_are_identical() -> None:
    recognition = (CARDS_DIR / "recognition_back.html").read_text(encoding="utf-8")
    recall = (CARDS_DIR / "recall_back.html").read_text(encoding="utf-8")

    assert recognition == recall, (
        "recognition_back.html and recall_back.html have drifted — "
        "both card types should share the same back template"
    )


def test_sentence_pinyin_is_collapsed_by_default() -> None:
    back = (CARDS_DIR / "recognition_back.html").read_text(encoding="utf-8")

    assert (
        '{{#SentencePinyin}}<details class="context-pinyin-toggle">\n'
        "            <summary>Show pinyin</summary>\n"
        '            <span class="context-pinyin">{{SentencePinyin}}</span>\n'
        "        </details>{{/SentencePinyin}}"
    ) in back

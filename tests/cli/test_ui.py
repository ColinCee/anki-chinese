from anki_chinese.cli.ui import format_audio_task_labels


def test_format_audio_task_labels_all_tasks():
    result = format_audio_task_labels(["mandarin", "cantonese", "sentence"])

    assert result == "Mandarin, Cantonese, Sentence"


def test_format_audio_task_labels_single_task():
    result = format_audio_task_labels(["cantonese"])

    assert result == "Cantonese"


def test_format_audio_task_labels_ignores_unknown():
    result = format_audio_task_labels(["mandarin", "unknown", "sentence"])

    assert result == "Mandarin, Sentence"


def test_format_audio_task_labels_empty():
    result = format_audio_task_labels([])

    assert result == ""

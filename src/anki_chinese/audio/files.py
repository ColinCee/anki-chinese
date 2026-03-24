"""Audio filenames, tags, and local-file validation."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..config import GENERATED_AUDIO_DIR
from ..notes.model import CharacterNote


def example_audio_filename(word: str, pinyin: str) -> str:
    safe_pinyin = pinyin.replace(" ", "_")
    return f"cmn_{word}_{safe_pinyin}.mp3"


def expected_mandarin_audio_tag(note: CharacterNote) -> str:
    if not note.hanzi or not note.pinyin:
        return ""
    return f"[sound:cmn_{note.hanzi}_{note.pinyin.replace(' ', '_')}.mp3]"


def expected_cantonese_audio_tag(note: CharacterNote) -> str:
    if not note.hanzi or not note.jyutping:
        return ""
    return f"[sound:yue_{note.hanzi}_{note.jyutping.replace(' ', '_')}.mp3]"


def expected_example_audio_tag(note: CharacterNote) -> str:
    if not note.example_word or not note.example_pinyin:
        return ""
    return f"[sound:{example_audio_filename(note.example_word, note.example_pinyin)}]"


def is_valid_audio_file(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def is_valid_audio_tag(tag: str, generated_audio_dir: Path | None = None) -> bool:
    if not tag.startswith("[sound:") or not tag.endswith("]"):
        return False
    filename = tag.replace("[sound:", "", 1).rstrip("]")
    audio_dir = generated_audio_dir or GENERATED_AUDIO_DIR
    return is_valid_audio_file(audio_dir / filename)


def audio_tasks_for_note(
    note: CharacterNote,
    *,
    force: bool,
    is_valid_audio_tag_fn: Callable[[str], bool],
) -> list[str]:
    tasks: list[str] = []

    mandarin_tag = expected_mandarin_audio_tag(note)
    if mandarin_tag and (
        force
        or note.mandarin_audio != mandarin_tag
        or not is_valid_audio_tag_fn(mandarin_tag)
    ):
        tasks.append("mandarin")

    cantonese_tag = expected_cantonese_audio_tag(note)
    if cantonese_tag and (
        force
        or note.cantonese_audio != cantonese_tag
        or not is_valid_audio_tag_fn(cantonese_tag)
    ):
        tasks.append("cantonese")

    example_tag = expected_example_audio_tag(note)
    if example_tag and (
        force
        or note.example_audio != example_tag
        or not is_valid_audio_tag_fn(example_tag)
    ):
        tasks.append("example")

    return tasks

"""Audio filenames, tags, and local-file validation."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..config import GENERATED_AUDIO_DIR
from ..notes import CharacterNote


def preview_mandarin_filename(text: str) -> str:
    safe_text = text.translate(str.maketrans({"/": "_", "\\": "_", ":": "_", " ": "_"}))
    return f"preview_cmn_{safe_text}.mp3"


def expected_mandarin_audio_tag(note: CharacterNote) -> str:
    if not note.hanzi or not note.pinyin:
        return ""
    return f"[sound:cmn_{note.hanzi}_{note.pinyin.replace(' ', '_')}.mp3]"


def expected_cantonese_audio_tag(note: CharacterNote) -> str:
    if not note.hanzi or not note.jyutping:
        return ""
    return f"[sound:yue_{note.hanzi}_{note.jyutping.replace(' ', '_')}.mp3]"


def sentence_audio_filename(hanzi: str, sentence: str) -> str:
    """Deterministic filename for sentence audio using the sentence text."""
    return f"cmn_sentence_{sentence}.mp3"


def expected_sentence_audio_tag(note: CharacterNote) -> str:
    if not note.sentence:
        return ""
    return f"[sound:{sentence_audio_filename(note.hanzi, note.sentence)}]"


def is_valid_audio_file(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def is_valid_audio_tag(tag: str, generated_audio_dir: Path | None = None) -> bool:
    if not tag.startswith("[sound:") or not tag.endswith("]"):
        return False
    filename = tag.replace("[sound:", "", 1).rstrip("]")
    audio_dir = generated_audio_dir or GENERATED_AUDIO_DIR
    return is_valid_audio_file(audio_dir / filename)


def referenced_audio_files(notes: list[CharacterNote]) -> set[str]:
    """Collect all audio filenames currently referenced by notes."""
    filenames: set[str] = set()
    for note in notes:
        for tag in (
            note.mandarin_audio,
            note.cantonese_audio,
            note.sentence_audio,
        ):
            if tag.startswith("[sound:") and tag.endswith("]"):
                filenames.add(tag[7:-1])
    return filenames


def collect_orphaned_audio(
    notes: list[CharacterNote],
    generated_audio_dir: Path,
) -> list[Path]:
    """Return audio files on disk that no note references.

    Only considers ``.mp3`` files to avoid deleting non-audio artifacts.
    """
    referenced = referenced_audio_files(notes)
    orphans: list[Path] = []
    if not generated_audio_dir.is_dir():
        return orphans
    for path in generated_audio_dir.iterdir():
        if path.suffix == ".mp3" and path.name not in referenced:
            orphans.append(path)
    return sorted(orphans)


def remove_orphaned_audio(
    notes: list[CharacterNote],
    generated_audio_dir: Path,
) -> list[Path]:
    """Delete orphaned audio files and return the list of removed paths."""
    orphans = collect_orphaned_audio(notes, generated_audio_dir)
    removed: list[Path] = []
    for path in orphans:
        try:
            path.unlink()
            removed.append(path)
        except OSError:
            pass
    return removed


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

    sentence_tag = expected_sentence_audio_tag(note)
    if sentence_tag and (
        force
        or note.sentence_audio != sentence_tag
        or not is_valid_audio_tag_fn(sentence_tag)
    ):
        tasks.append("sentence")

    return tasks

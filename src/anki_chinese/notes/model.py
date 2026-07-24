"""Data models for deck notes."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Literal


@dataclass(frozen=True)
class Curriculum:
    """Curriculum provenance independent of the Anki field projection."""

    track: Literal["rsh", "custom"] = "rsh"
    rsh_number: int | None = None
    lesson: str = ""
    origin: str = ""
    collection: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "track": self.track,
            "rsh_number": self.rsh_number,
            "lesson": self.lesson,
            "origin": self.origin,
            "collection": self.collection,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Curriculum:
        track = str(data.get("track", "rsh"))
        if track not in {"rsh", "custom"}:
            raise ValueError(f"Unsupported curriculum track: {track}")
        raw_number = data.get("rsh_number")
        rsh_number = int(raw_number) if raw_number not in (None, "") else None
        if track == "custom":
            rsh_number = None
        return cls(
            track=track,  # type: ignore[arg-type]
            rsh_number=rsh_number,
            lesson=str(data.get("lesson", "")),
            origin=str(data.get("origin", "")),
            collection=str(data.get("collection", "")),
        )

    @classmethod
    def from_legacy(cls, *, heisig_num: str, lesson: str) -> Curriculum:
        custom = lesson.startswith("Manual-Missing-")
        raw_number = "".join(character for character in heisig_num if character.isdigit())
        return cls(
            track="custom" if custom else "rsh",
            rsh_number=None if custom or not raw_number else int(raw_number),
            lesson="" if custom else lesson,
            origin="manual" if custom else "rsh",
            collection=lesson if custom else "",
        )


@dataclass
class CharacterNote:
    """One character = one note = two cards."""

    hanzi: str = ""
    meaning: str = ""
    pinyin: str = ""
    jyutping: str = ""
    mandarin_audio: str = ""
    cantonese_audio: str = ""

    sentence: str = ""
    sentence_pinyin: str = ""
    sentence_english: str = ""

    sentence_audio: str = ""
    stroke_order: str = ""
    heisig_num: str = ""
    lesson: str = ""
    story: str = ""
    curriculum: Curriculum = field(default_factory=Curriculum)

    needs_review: bool = field(default=False, repr=False)
    review_reason: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if self.curriculum.track == "custom":
            self.heisig_num = ""
        elif self.curriculum.rsh_number is not None:
            self.heisig_num = str(self.curriculum.rsh_number)
        if self.curriculum.lesson:
            self.lesson = self.curriculum.lesson

    def to_fields_list(self) -> list[str]:
        heisig_num = (
            str(self.curriculum.rsh_number)
            if self.curriculum.track == "rsh" and self.curriculum.rsh_number is not None
            else self.heisig_num if self.curriculum.track == "rsh" else ""
        )
        lesson = self.curriculum.lesson or self.lesson
        return [
            self.hanzi,
            self.meaning,
            self.pinyin,
            self.jyutping,
            self.mandarin_audio,
            self.cantonese_audio,
            self.stroke_order,
            heisig_num,
            lesson,
            self.story,
            self.sentence_audio,
            self.sentence,
            self.sentence_pinyin,
            self.sentence_english,
        ]

    def apkg_tags(self) -> list[str]:
        """Return controlled curriculum tags for the generated APKG."""

        tags = [f"curriculum::{self.curriculum.track}"]
        if self.curriculum.rsh_number is not None:
            tags.append(f"rsh::{self.curriculum.rsh_number}")
        if self.curriculum.lesson:
            tags.append(f"lesson::{self.curriculum.lesson.replace(' ', '_')}")
        if self.curriculum.origin:
            tags.append(f"origin::{self.curriculum.origin.replace(' ', '_')}")
        if self.curriculum.collection:
            tags.append(f"collection::{self.curriculum.collection.replace(' ', '_')}")
        if self.lesson and not self.curriculum.lesson:
            tags.append(self.lesson.replace(" ", "_"))
        return tags

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CharacterNote:
        valid = {field_.name for field_ in fields(cls)}
        # Backwards compat: legacy JSON uses "keyword" instead of "meaning"
        if "keyword" in data and "meaning" not in data:
            data = {**data, "meaning": data["keyword"]}
        values = {key: value for key, value in data.items() if key in valid}
        curriculum = values.get("curriculum")
        if isinstance(curriculum, dict):
            values["curriculum"] = Curriculum.from_dict(curriculum)
        elif curriculum is None:
            values["curriculum"] = Curriculum.from_legacy(
                heisig_num=str(values.get("heisig_num", "")),
                lesson=str(values.get("lesson", "")),
            )
        return cls(**values)

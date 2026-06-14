"""Provenance-aware audio state for generated note audio."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from ..notes import CharacterNote
from .files import (
    collect_orphaned_audio,
    expected_cantonese_audio_tag,
    expected_mandarin_audio_tag,
    expected_sentence_audio_tag,
    is_valid_audio_tag,
)
from .provider import AudioGenerationProfile, TTSProvider

AudioKind = Literal["mandarin", "cantonese", "sentence"]
AudioStatus = Literal["valid", "missing", "stale", "invalid", "not_applicable"]


@dataclass(frozen=True)
class AudioIdentity:
    kind: AudioKind
    hanzi: str
    text: str
    reading: str
    tag: str
    provider: str
    model: str
    voice: str
    language_code: str
    settings: dict[str, str | int | float | bool]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AudioIdentity:
        kind = data.get("kind")
        if kind not in ("mandarin", "cantonese", "sentence"):
            raise ValueError(f"Invalid audio identity kind: {kind!r}")
        settings_data = data.get("settings", {})
        if not isinstance(settings_data, dict):
            settings_data = {}
        return cls(
            kind=cast(AudioKind, kind),
            hanzi=str(data["hanzi"]),
            text=str(data["text"]),
            reading=str(data.get("reading", "")),
            tag=str(data["tag"]),
            provider=str(data["provider"]),
            model=str(data["model"]),
            voice=str(data["voice"]),
            language_code=str(data["language_code"]),
            settings={
                str(key): value
                for key, value in settings_data.items()
                if isinstance(value, (str, int, float, bool))
            },
        )


@dataclass(frozen=True)
class AudioRequirement:
    kind: AudioKind
    hanzi: str
    expected: AudioIdentity | None
    current_tag: str
    status: AudioStatus
    reason: str
    force_generation: bool = False

    @property
    def needs_generation(self) -> bool:
        return self.status in {"missing", "stale", "invalid"}


@dataclass(frozen=True)
class AudioManifest:
    version: int
    generated: dict[str, AudioIdentity]

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "generated": {
                tag: identity.to_dict() for tag, identity in sorted(self.generated.items())
            },
        }

    @classmethod
    def empty(cls) -> AudioManifest:
        return cls(version=1, generated={})

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AudioManifest:
        generated_data = data.get("generated", {})
        if not isinstance(generated_data, dict):
            generated_data = {}
        generated = {
            str(tag): AudioIdentity.from_dict(identity)
            for tag, identity in generated_data.items()
            if isinstance(identity, dict)
        }
        version = data.get("version", 1)
        return cls(version=version if isinstance(version, int) else 1, generated=generated)


@dataclass(frozen=True)
class AudioDeckState:
    requirements: list[AudioRequirement]
    orphaned_files: list[Path]

    @property
    def pending_requirements(self) -> list[AudioRequirement]:
        return [requirement for requirement in self.requirements if requirement.needs_generation]

    @property
    def pending_notes(self) -> int:
        return len({requirement.hanzi for requirement in self.pending_requirements})

    def pending_counts_by_kind(self) -> dict[AudioKind, int]:
        return {
            "mandarin": sum(1 for req in self.pending_requirements if req.kind == "mandarin"),
            "cantonese": sum(1 for req in self.pending_requirements if req.kind == "cantonese"),
            "sentence": sum(1 for req in self.pending_requirements if req.kind == "sentence"),
        }


def load_audio_manifest(path: Path) -> AudioManifest:
    if not path.exists():
        return AudioManifest.empty()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return AudioManifest.empty()
    return AudioManifest.from_dict(data)


def save_audio_manifest(path: Path, manifest: AudioManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def expected_audio_identity(
    note: CharacterNote,
    kind: AudioKind,
    profile: AudioGenerationProfile,
) -> AudioIdentity | None:
    if kind == "mandarin":
        tag = expected_mandarin_audio_tag(note)
        text = note.hanzi
        reading = note.pinyin
    elif kind == "cantonese":
        tag = expected_cantonese_audio_tag(note)
        text = note.hanzi
        reading = note.jyutping
    else:
        tag = expected_sentence_audio_tag(note)
        text = note.sentence
        reading = note.sentence_pinyin

    if not tag:
        return None

    return AudioIdentity(
        kind=kind,
        hanzi=note.hanzi,
        text=text,
        reading=reading,
        tag=tag,
        provider=profile.provider,
        model=profile.model,
        voice=profile.voice,
        language_code=profile.language_code,
        settings=profile.settings,
    )


def audio_generation_profiles(
    provider: TTSProvider,
    sentence_provider: TTSProvider | None = None,
) -> dict[AudioKind, AudioGenerationProfile]:
    sentence_profile_provider = sentence_provider or provider
    return {
        "mandarin": provider.generation_profile("mandarin"),
        "cantonese": provider.generation_profile("cantonese"),
        "sentence": sentence_profile_provider.generation_profile("sentence"),
    }


def _current_tag(note: CharacterNote, kind: AudioKind) -> str:
    if kind == "mandarin":
        return note.mandarin_audio
    if kind == "cantonese":
        return note.cantonese_audio
    return note.sentence_audio


def audio_requirement_for_note(
    note: CharacterNote,
    kind: AudioKind,
    *,
    profile: AudioGenerationProfile,
    manifest: AudioManifest,
    generated_audio_dir: Path,
) -> AudioRequirement:
    expected = expected_audio_identity(note, kind, profile)
    current_tag = _current_tag(note, kind)
    if expected is None:
        return AudioRequirement(
            kind=kind,
            hanzi=note.hanzi,
            expected=None,
            current_tag=current_tag,
            status="not_applicable",
            reason="No text/reading available for this audio kind.",
        )

    if not current_tag:
        return AudioRequirement(
            kind=kind,
            hanzi=note.hanzi,
            expected=expected,
            current_tag=current_tag,
            status="missing",
            reason="Audio tag is missing.",
        )
    if current_tag != expected.tag:
        return AudioRequirement(
            kind=kind,
            hanzi=note.hanzi,
            expected=expected,
            current_tag=current_tag,
            status="stale",
            reason="Audio tag does not match current text or reading.",
        )
    if not is_valid_audio_tag(current_tag, generated_audio_dir=generated_audio_dir):
        return AudioRequirement(
            kind=kind,
            hanzi=note.hanzi,
            expected=expected,
            current_tag=current_tag,
            status="invalid",
            reason="Audio tag points to a missing or empty generated file.",
        )

    manifest_identity = manifest.generated.get(current_tag)
    if manifest_identity is not None and manifest_identity != expected:
        return AudioRequirement(
            kind=kind,
            hanzi=note.hanzi,
            expected=expected,
            current_tag=current_tag,
            status="stale",
            reason="Audio was generated with different provider settings.",
            force_generation=True,
        )

    return AudioRequirement(
        kind=kind,
        hanzi=note.hanzi,
        expected=expected,
        current_tag=current_tag,
        status="valid",
        reason="Audio tag matches current text, reading, file, and provider settings.",
    )


def build_audio_deck_state(
    notes: list[CharacterNote],
    *,
    profiles: dict[AudioKind, AudioGenerationProfile],
    generated_audio_dir: Path,
    manifest: AudioManifest | None = None,
) -> AudioDeckState:
    active_manifest = manifest or AudioManifest.empty()
    requirements: list[AudioRequirement] = []
    for note in notes:
        for kind in ("mandarin", "cantonese", "sentence"):
            requirements.append(
                audio_requirement_for_note(
                    note,
                    kind,
                    profile=profiles[kind],
                    manifest=active_manifest,
                    generated_audio_dir=generated_audio_dir,
                )
            )
    return AudioDeckState(
        requirements=requirements,
        orphaned_files=collect_orphaned_audio(notes, generated_audio_dir),
    )


def backfill_audio_manifest(
    notes: list[CharacterNote],
    *,
    profiles: dict[AudioKind, AudioGenerationProfile],
    generated_audio_dir: Path,
) -> AudioManifest:
    generated: dict[str, AudioIdentity] = {}
    empty = AudioManifest.empty()
    for note in notes:
        for kind in ("mandarin", "cantonese", "sentence"):
            requirement = audio_requirement_for_note(
                note,
                kind,
                profile=profiles[kind],
                manifest=empty,
                generated_audio_dir=generated_audio_dir,
            )
            if requirement.status == "valid" and requirement.expected is not None:
                generated[requirement.expected.tag] = requirement.expected
    return AudioManifest(version=1, generated=generated)

"""CLI package entry point and compatibility wrappers."""

from __future__ import annotations

from pathlib import Path

from .app import AppRuntime, app, build_runtime, create_app
from .audio import run_audio
from .build import run_build
from .init import run_init
from .status import run_review, run_status
from .test_tts import run_test_tts


def init(
    input_file: Path | None = None,
    skip_examples: bool = False,
):
    runtime = build_runtime()
    return run_init(
        runtime,
        input_file or runtime.source_deck_path,
        skip_examples=skip_examples,
    )


def audio(
    char: str = "",
    limit: int = 0,
    start_rsh: int = 0,
    force: bool = False,
    fail_fast: bool = False,
):
    runtime = build_runtime()
    return run_audio(
        runtime,
        char=char,
        limit=limit,
        start_rsh=start_rsh,
        force=force,
        fail_fast=fail_fast,
    )


def build(
    full: bool = False,
    skip_audio: bool = False,
    skip_examples: bool = False,
    audio_limit: int = 0,
    audio_start_rsh: int = 0,
):
    runtime = build_runtime()
    return run_build(
        runtime,
        full=full,
        skip_audio=skip_audio,
        skip_examples=skip_examples,
        audio_limit=audio_limit,
        audio_start_rsh=audio_start_rsh,
    )


def status() -> None:
    run_status(build_runtime())


def review() -> None:
    run_review(build_runtime())


def test_tts(
    char: str = "",
    word: str = "",
    voice: str = "",
    force: bool = False,
) -> None:
    run_test_tts(
        build_runtime(),
        char=char,
        word=word,
        voice=voice,
        force=force,
    )


__all__ = [
    "AppRuntime",
    "app",
    "audio",
    "build",
    "build_runtime",
    "create_app",
    "init",
    "review",
    "status",
    "test_tts",
]

from __future__ import annotations

import os
from pathlib import Path

from anki_chinese.workflows.pipeline_state import (
    fingerprint_path,
    load_pipeline_state,
    record_stage,
)


def test_record_stage_persists_input_and_output_fingerprints(tmp_path: Path) -> None:
    source = tmp_path / "source.apkg"
    enriched = tmp_path / "enriched.json"
    state_path = tmp_path / "pipeline.json"
    source.write_text("source", encoding="utf-8")
    enriched.write_text("[]", encoding="utf-8")

    record_stage(
        state_path,
        "init",
        inputs={"source_deck": source},
        outputs={"enriched": enriched},
    )

    state = load_pipeline_state(state_path)
    init_state = state.stages["init"]
    assert init_state.inputs["source_deck"].kind == "file"
    assert init_state.inputs["source_deck"].size == len("source")
    assert init_state.outputs["enriched"].kind == "file"


def test_directory_fingerprint_changes_when_generated_files_change(tmp_path: Path) -> None:
    generated_audio_dir = tmp_path / "generated"
    generated_audio_dir.mkdir()
    first = fingerprint_path(generated_audio_dir)

    audio_file = generated_audio_dir / "cmn_水_shui.mp3"
    audio_file.write_bytes(b"audio")
    os.utime(audio_file, (100, 100))

    second = fingerprint_path(generated_audio_dir)

    assert first.kind == "directory"
    assert second.entries == 1
    assert second.size == len(b"audio")
    assert second.metadata_hash != first.metadata_hash


def test_missing_path_fingerprint_is_explicit(tmp_path: Path) -> None:
    fingerprint = fingerprint_path(tmp_path / "missing.json")

    assert fingerprint.kind == "missing"
    assert fingerprint.size == 0
    assert fingerprint.metadata_hash == ""

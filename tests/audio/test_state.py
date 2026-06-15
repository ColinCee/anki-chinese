from dataclasses import replace
from pathlib import Path

from anki_chinese.audio.state import (
    AudioManifest,
    audio_generation_profiles,
    backfill_audio_manifest,
    build_audio_deck_state,
)
from anki_chinese.notes import CharacterNote


def _write_audio_files(generated_audio_dir: Path, filenames: list[str]) -> None:
    generated_audio_dir.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        (generated_audio_dir / filename).write_bytes(b"ID3")


def test_backfills_existing_valid_audio_with_current_profile(tmp_path: Path, stub_tts_provider) -> None:
    note = CharacterNote(
        hanzi="水",
        meaning="water",
        pinyin="shuǐ",
        jyutping="seoi2",
        mandarin_audio="[sound:cmn_水_shuǐ.mp3]",
        cantonese_audio="[sound:yue_水_seoi2.mp3]",
        sentence="我喝水。",
        sentence_audio="[sound:cmn_sentence_我喝水。.mp3]",
    )
    _write_audio_files(
        tmp_path,
        ["cmn_水_shuǐ.mp3", "yue_水_seoi2.mp3", "cmn_sentence_我喝水。.mp3"],
    )

    manifest = backfill_audio_manifest(
        [note],
        profiles=audio_generation_profiles(stub_tts_provider),
        generated_audio_dir=tmp_path,
    )

    assert set(manifest.generated) == {
        "[sound:cmn_水_shuǐ.mp3]",
        "[sound:yue_水_seoi2.mp3]",
        "[sound:cmn_sentence_我喝水。.mp3]",
    }
    assert manifest.generated["[sound:cmn_水_shuǐ.mp3]"].provider == "stub"
    assert manifest.generated["[sound:cmn_sentence_我喝水。.mp3]"].voice == "stub-sentence"


def test_missing_manifest_entry_does_not_make_existing_audio_stale(
    tmp_path: Path,
    stub_tts_provider,
) -> None:
    note = CharacterNote(
        hanzi="水",
        meaning="water",
        pinyin="shuǐ",
        mandarin_audio="[sound:cmn_水_shuǐ.mp3]",
    )
    _write_audio_files(tmp_path, ["cmn_水_shuǐ.mp3"])

    state = build_audio_deck_state(
        [note],
        profiles=audio_generation_profiles(stub_tts_provider),
        generated_audio_dir=tmp_path,
        manifest=AudioManifest.empty(),
    )

    mandarin = next(req for req in state.requirements if req.kind == "mandarin")
    assert mandarin.status == "valid"


def test_manifest_profile_change_marks_audio_stale(tmp_path: Path, stub_tts_provider) -> None:
    note = CharacterNote(
        hanzi="水",
        meaning="water",
        pinyin="shuǐ",
        mandarin_audio="[sound:cmn_水_shuǐ.mp3]",
    )
    _write_audio_files(tmp_path, ["cmn_水_shuǐ.mp3"])
    old_profiles = audio_generation_profiles(stub_tts_provider)
    manifest = backfill_audio_manifest(
        [note],
        profiles=old_profiles,
        generated_audio_dir=tmp_path,
    )
    new_profiles = {
        **old_profiles,
        "mandarin": replace(old_profiles["mandarin"], model="new-model"),
    }

    state = build_audio_deck_state(
        [note],
        profiles=new_profiles,
        generated_audio_dir=tmp_path,
        manifest=manifest,
    )

    mandarin = next(req for req in state.requirements if req.kind == "mandarin")
    assert mandarin.status == "stale"
    assert mandarin.reason == "Audio was generated with different provider settings."


def test_shared_sentence_audio_is_valid_for_multiple_notes(
    tmp_path: Path,
    stub_tts_provider,
) -> None:
    notes = [
        CharacterNote(
            hanzi="天",
            meaning="sky",
            sentence="今天天气很好。",
            sentence_pinyin="jīn tiān tiān qì hěn hǎo",
            sentence_audio="[sound:cmn_sentence_今天天气很好。.mp3]",
        ),
        CharacterNote(
            hanzi="气",
            meaning="air",
            sentence="今天天气很好。",
            sentence_pinyin="jīntiān tiānqì hěn hǎo",
            sentence_audio="[sound:cmn_sentence_今天天气很好。.mp3]",
        ),
    ]
    _write_audio_files(tmp_path, ["cmn_sentence_今天天气很好。.mp3"])
    manifest = backfill_audio_manifest(
        notes,
        profiles=audio_generation_profiles(stub_tts_provider),
        generated_audio_dir=tmp_path,
    )

    state = build_audio_deck_state(
        notes,
        profiles=audio_generation_profiles(stub_tts_provider),
        generated_audio_dir=tmp_path,
        manifest=manifest,
    )

    sentence_requirements = [req for req in state.requirements if req.kind == "sentence"]
    assert [req.status for req in sentence_requirements] == ["valid", "valid"]

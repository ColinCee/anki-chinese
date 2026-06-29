from anki_chinese import config


def test_default_layout_paths_match_the_documented_repo_structure() -> None:
    project_root = config.PROJECT_ROOT

    assert project_root / "src" / "anki_chinese" / "cards" == config.CARDS_DIR
    assert project_root / "data" / "source" / "All Decks.apkg" == config.SOURCE_DECK_PATH
    assert (
        project_root / "data" / "reference" / "cedict_1_0_ts_utf-8_mdbg.txt" == config.CEDICT_PATH
    )
    assert project_root / "data" / "reference" / "hsk_complete.min.json" == config.HSK_VOCAB_PATH
    assert project_root / "data" / "reference" / "SUBTLEX_CH.xlsx" == config.SUBTLEX_PATH
    assert project_root / "data" / "state" / "enriched.json" == config.ENRICHED_PATH
    assert project_root / "data" / "build" / "audio" / "generated" == config.GENERATED_AUDIO_DIR
    assert project_root / "data" / "build" / "audio" / "samples" == config.SAMPLE_AUDIO_DIR
    assert project_root / "data" / "build" / "decks" == config.DECK_OUTPUT_DIR

from anki_chinese import config


def test_default_layout_paths_match_the_documented_repo_structure() -> None:
    project_root = config.PROJECT_ROOT

    assert config.CARDS_DIR == project_root / 'src' / 'anki_chinese' / 'cards'
    assert config.SOURCE_DECK_PATH == project_root / 'data' / 'source' / 'All Decks.txt'
    assert config.OVERRIDES_PATH == project_root / 'data' / 'manual' / 'overrides.json'
    assert config.EXAMPLE_WORDS_PATH == project_root / 'data' / 'manual' / 'example_words.json'
    assert config.CEDICT_PATH == project_root / 'data' / 'reference' / 'cedict_1_0_ts_utf-8_mdbg.txt'
    assert config.HSK_VOCAB_PATH == project_root / 'data' / 'reference' / 'hsk_complete.min.json'
    assert config.SUBTLEX_PATH == project_root / 'data' / 'reference' / 'SUBTLEX_CH.xlsx'
    assert config.ENRICHED_PATH == project_root / 'data' / 'state' / 'enriched.json'
    assert config.GENERATED_AUDIO_DIR == project_root / 'data' / 'build' / 'audio' / 'generated'
    assert config.SAMPLE_AUDIO_DIR == project_root / 'data' / 'build' / 'audio' / 'samples'
    assert config.DECK_OUTPUT_DIR == project_root / 'data' / 'build' / 'decks'

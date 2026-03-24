from anki_chinese.cli import create_app
from anki_chinese.notes import CharacterNote


def test_build_full_runs_parse_enrich_audio_and_build(runtime_factory, runner, stub_tts_provider) -> None:
    parsed_notes = [CharacterNote(hanzi='行', keyword='go', heisig_num='RSH 144', lesson='Lesson 12')]
    enriched_notes = [
        CharacterNote(
            hanzi='行',
            keyword='go',
            pinyin='xíng',
            jyutping='haang4',
            example_word='银行',
            example_meaning='bank',
            example_pinyin='yín háng',
            heisig_num='RSH 144',
            lesson='Lesson 12',
        )
    ]
    runtime = runtime_factory(
        parsed_notes=parsed_notes,
        enriched_notes=enriched_notes,
        tts_provider=stub_tts_provider,
    )
    app = create_app(runtime)

    result = runner.invoke(app, ['build', '--full'])

    assert result.exit_code == 0
    saved = runtime.note_store.load()
    assert saved[0].mandarin_audio == '[sound:cmn_行_xíng.mp3]'
    assert saved[0].cantonese_audio == '[sound:yue_行_haang4.mp3]'
    assert saved[0].example_audio == '[sound:cmn_银行_yín_háng.mp3]'
    assert (runtime.note_store.path.parent.parent / 'build' / 'decks' / 'deck.apkg').exists()

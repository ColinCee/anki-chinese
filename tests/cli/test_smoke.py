from anki_chinese.cli import create_app
from anki_chinese.notes import CharacterNote


def test_init_command_parses_enriches_and_saves_notes(runtime_factory, runner) -> None:
    runtime = runtime_factory(
        parsed_notes=[CharacterNote(hanzi='一', keyword='one')],
        enriched_notes=[CharacterNote(hanzi='一', keyword='one', pinyin='yī', jyutping='jat1')],
    )
    app = create_app(runtime)

    result = runner.invoke(app, ['init', '--input', str(runtime.source_deck_path)])

    assert result.exit_code == 0
    saved_notes = runtime.note_store.load()
    assert len(saved_notes) == 1
    assert saved_notes[0].pinyin == 'yī'


def test_build_command_loads_saved_notes_and_builds_package(runtime_factory, runner) -> None:
    runtime = runtime_factory(
        saved_notes=[CharacterNote(hanzi='一', keyword='one', pinyin='yī')],
    )
    app = create_app(runtime)

    result = runner.invoke(app, ['build'])

    assert result.exit_code == 0
    assert (runtime.source_deck_path.parent / 'deck.apkg').exists()

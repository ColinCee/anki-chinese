from anki_chinese.cli.status import run_review, run_status
from anki_chinese.notes import CharacterNote


def test_run_status_reports_validation_issues_and_review_count(runtime_factory) -> None:
    notes = [
        CharacterNote(hanzi='一', keyword='one'),
        CharacterNote(hanzi='行', keyword='go', needs_review=True, review_reason='Check reading'),
    ]
    runtime = runtime_factory(saved_notes=notes)

    run_status(runtime)

    output = runtime.console.file.getvalue()
    assert 'issues:' in output
    assert 'missing pinyin' in output
    assert 'notes flagged for review' in output


def test_run_review_prints_fix_guidance_for_flagged_notes(runtime_factory) -> None:
    runtime = runtime_factory(
        saved_notes=[
            CharacterNote(
                hanzi='行',
                keyword='go',
                pinyin='xíng',
                needs_review=True,
                review_reason='Polyphonic character',
            )
        ]
    )

    run_review(runtime)

    output = runtime.console.file.getvalue()
    assert 'data/overrides.json' in output
    assert '行' in output
    assert 'Polyphonic character' in output

"""End-to-end tests running real CLI commands against the actual .apkg export."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from anki_chinese.cli import create_app
from anki_chinese.cli.app import build_runtime

REAL_APKG = Path(__file__).resolve().parents[2] / "data" / "source" / "All Decks.apkg"

pytestmark = pytest.mark.skipif(not REAL_APKG.exists(), reason="Real .apkg not present")


@pytest.fixture
def e2e_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a real runtime but redirect mutable state to tmp_path."""
    runtime = build_runtime()
    # Point mutable outputs at tmp so the test is side-effect free.
    from anki_chinese import deck as deck_module
    from anki_chinese.notes import JsonNoteStore

    runtime.note_store = JsonNoteStore(tmp_path / "enriched.json")
    runtime.generated_audio_dir = tmp_path / "audio" / "generated"
    runtime.sample_audio_dir = tmp_path / "audio" / "samples"
    runtime.deck_output_path = tmp_path / "decks" / "chinese_rsh.apkg"
    runtime.pipeline_state_path = tmp_path / "state" / "pipeline.json"
    runtime.audio_manifest_path = tmp_path / "state" / "audio_manifest.json"
    monkeypatch.setattr(deck_module, "DECK_OUTPUT_DIR", runtime.deck_output_path.parent)
    return runtime


def test_init_parses_real_apkg(e2e_runtime, runner: CliRunner) -> None:
    app = create_app(e2e_runtime)

    result = runner.invoke(app, ["init", "--input", str(REAL_APKG)])

    assert result.exit_code == 0, result.output
    assert "notes parsed" in result.output
    saved = e2e_runtime.note_store.load()
    assert len(saved) > 2000


def test_status_reports_missing_live_learning_state(e2e_runtime, runner: CliRunner) -> None:
    app = create_app(e2e_runtime)
    # Seed state so status has something to report.
    runner.invoke(app, ["init", "--input", str(REAL_APKG)])

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    assert "Learned-character progress unavailable" in result.output
    assert "live scheduling" in result.output


def test_build_produces_output_deck(e2e_runtime, runner: CliRunner) -> None:
    app = create_app(e2e_runtime)
    runner.invoke(app, ["init", "--input", str(REAL_APKG)])

    result = runner.invoke(app, ["build"])

    assert result.exit_code == 0, result.output
    assert "Built" in result.output

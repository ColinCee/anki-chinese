import json

from anki_chinese.cli import create_app
from anki_chinese.cli.doctor import run_doctor
from anki_chinese.notes import CharacterNote


class FakeAnkiConnect:
    def version(self) -> int:
        return 6


def test_run_doctor_reports_readiness_without_mutating(
    monkeypatch,
    runtime_factory,
    tmp_path,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setenv("CLOUDSDK_CONFIG", str(tmp_path / "gcloud"))
    runtime = runtime_factory(
        saved_notes=[
            CharacterNote(
                hanzi="水",
                meaning="water",
                pinyin="shuǐ",
                jyutping="seoi2",
            )
        ]
    )

    checks = run_doctor(runtime, check_anki=True, anki_client=FakeAnkiConnect())

    output = runtime.console.file.getvalue()
    assert "Doctor" in output
    assert "Source deck export" in output
    assert "Gemini API key" in output
    assert "AnkiConnect" in output
    assert any(check.name == "AnkiConnect" and check.status == "ok" for check in checks)


def test_doctor_command_json_output_skips_anki_by_default(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    checks = json.loads(runtime.console.file.getvalue())
    assert any(check["name"] == "AnkiConnect" and check["status"] == "warn" for check in checks)
    assert any(check["name"] == "Enriched notes" and check["status"] == "ok" for check in checks)

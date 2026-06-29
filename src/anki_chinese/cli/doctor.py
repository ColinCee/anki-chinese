"""`anki-chinese doctor` readiness checks."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import typer
from rich.table import Table

from ..activation import AnkiConnectClient, AnkiConnectError
from ..workflows.sync import plan_sync
from .app import AppRuntime
from .audio import load_current_audio_deck_state

DoctorStatus = Literal["ok", "warn", "error"]


class AnkiConnectHealthClient(Protocol):
    def version(self) -> int: ...


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: DoctorStatus
    detail: str
    hint: str = ""

    def to_dict(self) -> dict[str, str]:
        data = {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }
        if self.hint:
            data["hint"] = self.hint
        return data


def _env_is_set(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _google_adc_path() -> Path:
    config_dir = os.getenv("CLOUDSDK_CONFIG", "").strip()
    if config_dir:
        return Path(config_dir) / "application_default_credentials.json"
    return Path.home() / ".config" / "gcloud" / "application_default_credentials.json"


def _check_google_adc() -> DoctorCheck:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if credentials_path:
        path = Path(credentials_path).expanduser()
        if path.is_file():
            return DoctorCheck("Google TTS auth", "ok", "GOOGLE_APPLICATION_CREDENTIALS points to a file")
        return DoctorCheck(
            "Google TTS auth",
            "warn",
            "GOOGLE_APPLICATION_CREDENTIALS is set but the file was not found",
            str(path),
        )

    adc_path = _google_adc_path()
    if adc_path.is_file():
        return DoctorCheck("Google TTS auth", "ok", "gcloud Application Default Credentials found")
    return DoctorCheck(
        "Google TTS auth",
        "warn",
        "No Google Application Default Credentials detected",
        "Run `gcloud auth application-default login` or set GOOGLE_APPLICATION_CREDENTIALS.",
    )


def _check_env() -> list[DoctorCheck]:
    checks = [
        DoctorCheck(
            "Gemini API key",
            "ok" if _env_is_set("GEMINI_API_KEY") else "warn",
            "GEMINI_API_KEY is set"
            if _env_is_set("GEMINI_API_KEY")
            else "GEMINI_API_KEY is not set",
            "" if _env_is_set("GEMINI_API_KEY") else "Needed for sentences, keywords, and repair commands.",
        ),
        DoctorCheck(
            "MiniMax API key",
            "ok" if _env_is_set("MINIMAX_API_KEY") else "warn",
            "MINIMAX_API_KEY is set"
            if _env_is_set("MINIMAX_API_KEY")
            else "MINIMAX_API_KEY is not set",
            "" if _env_is_set("MINIMAX_API_KEY") else "Needed for MiniMax sentence audio.",
        ),
        _check_google_adc(),
    ]
    if _env_is_set("ANKICONNECT_API_KEY"):
        checks.append(DoctorCheck("AnkiConnect API key", "ok", "ANKICONNECT_API_KEY is set"))
    else:
        checks.append(
            DoctorCheck(
                "AnkiConnect API key",
                "ok",
                "ANKICONNECT_API_KEY is not set",
                "This is fine unless your local AnkiConnect add-on requires one.",
            )
        )
    return checks


def _check_files(runtime: AppRuntime) -> list[DoctorCheck]:
    checks = [
        DoctorCheck(
            "Source deck export",
            "ok" if runtime.source_deck_path.is_file() else "error",
            str(runtime.source_deck_path),
            "" if runtime.source_deck_path.is_file() else "Export Anki to data/source/All Decks.apkg.",
        ),
        DoctorCheck(
            "Built deck output",
            "ok" if runtime.deck_output_path.is_file() else "warn",
            str(runtime.deck_output_path),
            "" if runtime.deck_output_path.is_file() else "Run `uv run anki-chinese sync` or `build`.",
        ),
    ]

    try:
        notes = runtime.note_store.load()
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        checks.append(
            DoctorCheck(
                "Enriched notes",
                "error",
                f"Could not load {runtime.note_store.path}: {error}",
                "Run `uv run anki-chinese init`.",
            )
        )
        return checks

    checks.append(DoctorCheck("Enriched notes", "ok", f"{len(notes)} notes loaded"))
    return checks


def _check_sync(runtime: AppRuntime) -> DoctorCheck:
    try:
        plan = plan_sync(
            source_deck_path=runtime.source_deck_path,
            enriched_path=runtime.note_store.path,
            deck_output_path=runtime.deck_output_path,
            generated_audio_dir=runtime.generated_audio_dir,
            tts_provider=runtime.tts_provider,
            sentence_tts_provider=runtime.sentence_tts_provider,
            audio_manifest_path=runtime.audio_manifest_path,
            pipeline_state_path=runtime.pipeline_state_path,
        )
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        return DoctorCheck("Sync plan", "error", f"Could not build sync plan: {error}")

    if plan.is_up_to_date:
        return DoctorCheck("Sync plan", "ok", "No sync steps required")
    blocked = sum(1 for stage in plan.stages if stage.status == "blocked")
    needed = sum(1 for stage in plan.stages if stage.status == "needed")
    return DoctorCheck(
        "Sync plan",
        "warn",
        f"{needed} needed, {blocked} blocked",
        plan.required_commands[0] if plan.required_commands else "Run `uv run anki-chinese sync --dry-run`.",
    )


def _check_audio(runtime: AppRuntime) -> DoctorCheck:
    try:
        notes = runtime.note_store.load()
        state = load_current_audio_deck_state(runtime, notes)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        return DoctorCheck("Audio health", "error", f"Could not inspect audio state: {error}")

    pending = state.pending_counts_by_kind()
    if not state.pending_requirements and not state.orphaned_files:
        return DoctorCheck("Audio health", "ok", "Expected generated audio is current")
    return DoctorCheck(
        "Audio health",
        "warn",
        (
            f"{state.pending_notes} notes need audio updates "
            f"(Mandarin {pending['mandarin']}, Cantonese {pending['cantonese']}, "
            f"Sentence {pending['sentence']}); {len(state.orphaned_files)} orphaned files"
        ),
        "Run `uv run anki-chinese audio` or `uv run anki-chinese audio-clean`.",
    )


def _check_ankiconnect(client: AnkiConnectHealthClient) -> DoctorCheck:
    try:
        version = client.version()
    except AnkiConnectError as error:
        return DoctorCheck("AnkiConnect", "warn", str(error))
    return DoctorCheck("AnkiConnect", "ok", f"Reachable, API version {version}")


def build_doctor_checks(
    runtime: AppRuntime,
    *,
    check_anki: bool,
    anki_client: AnkiConnectHealthClient | None = None,
) -> list[DoctorCheck]:
    checks = [
        *_check_files(runtime),
        _check_sync(runtime),
        _check_audio(runtime),
        *_check_env(),
    ]
    if check_anki:
        checks.append(
            _check_ankiconnect(
                anki_client
                or AnkiConnectClient(
                    api_key=os.getenv("ANKICONNECT_API_KEY", "").strip(),
                    timeout_seconds=1.5,
                )
            )
        )
    else:
        checks.append(
            DoctorCheck(
                "AnkiConnect",
                "warn",
                "Reachability check skipped",
                "Run `uv run anki-chinese doctor --check-anki` when Anki is open.",
            )
        )
    return checks


def _render_checks(runtime: AppRuntime, checks: list[DoctorCheck]) -> None:
    table = Table(title="Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Detail")
    table.add_column("Hint")

    styles = {"ok": "green", "warn": "yellow", "error": "red"}
    for check in checks:
        table.add_row(
            check.name,
            f"[{styles[check.status]}]{check.status}[/{styles[check.status]}]",
            check.detail,
            check.hint,
        )
    runtime.console.print(table)


def run_doctor(
    runtime: AppRuntime,
    *,
    json_output: bool = False,
    strict: bool = False,
    check_anki: bool = False,
    anki_client: AnkiConnectHealthClient | None = None,
) -> list[DoctorCheck]:
    checks = build_doctor_checks(runtime, check_anki=check_anki, anki_client=anki_client)
    if json_output:
        runtime.console.print_json(data=[check.to_dict() for check in checks])
    else:
        _render_checks(runtime, checks)

    has_error = any(check.status == "error" for check in checks)
    has_warning = any(check.status == "warn" for check in checks)
    if has_error or (strict and has_warning):
        raise typer.Exit(1)
    return checks


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def doctor(
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Print readiness checks as machine-readable JSON.",
        ),
        strict: bool = typer.Option(
            False,
            "--strict",
            help="Exit non-zero when any warning is present.",
        ),
        check_anki: bool = typer.Option(
            False,
            "--check-anki",
            help="Also probe local AnkiConnect reachability. Does not mutate Anki.",
        ),
    ) -> None:
        """Check local readiness for rebuild, generation, audio, and live Anki workflows."""

        run_doctor(runtime, json_output=json_output, strict=strict, check_anki=check_anki)

"""AGENTS.md guardrails, enforced by reading the source rather than trusting review."""

from __future__ import annotations

import ast
from functools import cache
from pathlib import Path

import genanki

import anki_chinese
from anki_chinese.activation import __all__ as ACTIVATION_EXPORTS
from anki_chinese.config import DECK_ID, FIELDS, MODEL_ID
from anki_chinese.deck import _build_model, _StableNote

PACKAGE_DIR = Path(anki_chinese.__file__).parent
MIGRATION_HINT = (
    "Changing Anki identity needs an explicit migration; see "
    "docs/reference.md#anki-model before updating this pin."
)


@cache
def _modules() -> dict[str, Path]:
    modules = {}
    for path in PACKAGE_DIR.rglob("*.py"):
        parts = ["anki_chinese", *path.relative_to(PACKAGE_DIR).with_suffix("").parts]
        if parts[-1] == "__init__":
            parts.pop()
        modules[".".join(parts)] = path
    return modules


@cache
def _imports(module: str) -> frozenset[tuple[str, str | None]]:
    """(resolved module, imported name) pairs, including function-level imports."""
    path = _modules()[module]
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    found: set[tuple[str, str | None]] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update((alias.name, None) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = package.split(".")[: len(package.split(".")) - node.level + 1]
                base = ".".join([*anchor, base] if base else anchor)
            for alias in node.names:
                submodule = f"{base}.{alias.name}"
                if submodule in _modules():
                    found.add((submodule, None))
                else:
                    found.add((base, alias.name))
    return frozenset(found)


def _imported_modules(module: str) -> set[str]:
    return {name for name, _ in _imports(module)}


def _closure(*roots: str) -> set[str]:
    """Package modules reachable from roots by their own import statements."""
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        seen.add(module)
        stack.extend(m for m in _imported_modules(module) if m in _modules())
    return seen


def _matches(imported: str, prefixes: tuple[str, ...]) -> bool:
    return any(imported == p or imported.startswith(f"{p}.") for p in prefixes)


def _inside(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


# ── Anki identity ─────────────────────────────────────────────────────


def test_anki_identity_is_pinned() -> None:
    assert MODEL_ID == 1_704_328_571, MIGRATION_HINT
    assert DECK_ID == 1_704_328_572, MIGRATION_HINT
    assert FIELDS == [
        "Hanzi",
        "Meaning",
        "Pinyin",
        "Jyutping",
        "MandarinAudio",
        "CantoneseAudio",
        "StrokeOrder",
        "HeisigNum",
        "Lesson",
        "Story",
        "SentenceAudio",
        "Sentence",
        "SentencePinyin",
        "SentenceEnglish",
    ], MIGRATION_HINT


def test_note_guid_depends_only_on_hanzi() -> None:
    model = _build_model()
    first = _StableNote(hanzi="水", model=model, fields=["水", *[""] * (len(FIELDS) - 1)])
    edited = _StableNote(hanzi="水", model=model, fields=["水", "water", *[""] * (len(FIELDS) - 2)])
    assert first.guid == edited.guid == genanki.guid_for("chinese-rsh", "水"), MIGRATION_HINT
    assert first.guid == "+(L;_ZFC<", MIGRATION_HINT


# ── Boundaries ────────────────────────────────────────────────────────


def test_ankiconnect_transport_stays_in_activation() -> None:
    offenders = [
        module
        for module in _modules()
        if not _inside(module, "anki_chinese.activation")
        and (
            ("anki_chinese.config", "ANKICONNECT_URL") in _imports(module)
            or "anki_chinese.activation.ankiconnect" in _imported_modules(module)
            or (module != "anki_chinese.config" and ":8765" in _modules()[module].read_text())
        )
    ]
    assert not offenders, f"Reach AnkiConnect through `anki_chinese.activation`: {offenders}"


AUDIO_VENDOR_MODULES = ("anki_chinese.audio.google_tts", "anki_chinese.audio.minimax")
TTS_SDKS = ("google.auth", "google.oauth2", "google.cloud")


def test_tts_vendor_details_stay_behind_audio_factory() -> None:
    offenders = [
        module
        for module in _modules()
        if module not in (*AUDIO_VENDOR_MODULES, "anki_chinese.audio.factory")
        and any(_matches(m, AUDIO_VENDOR_MODULES + TTS_SDKS) for m in _imported_modules(module))
    ]
    assert not offenders, (
        f"Use `audio/provider.py` and `audio/factory.py`, not vendor modules/SDKs: {offenders}"
    )


ACTIVATION_MUTATIONS = {
    name
    for name in ACTIVATION_EXPORTS
    if name.startswith(("activate_", "resuspend_", "suspend_", "undo_", "write_"))
}


def test_workbench_does_not_drive_live_mutations() -> None:
    offenders = sorted(
        f"{module}: {name or imported}"
        for module in _modules()
        if _inside(module, "anki_chinese.tui")
        for imported, name in _imports(module)
        if (_inside(imported, "anki_chinese.activation") and name in ACTIVATION_MUTATIONS)
        or _matches(imported, ("anki_chinese.activation.service", "anki_chinese.cli.activate"))
    )
    assert ACTIVATION_MUTATIONS, "activation mutation exports were renamed; update this test"
    assert not offenders, (
        f"The workbench is presentational; live mutations stay in CLI: {offenders}"
    )


def test_doctor_imports_no_mutations() -> None:
    names = {
        name
        for imported, name in _imports("anki_chinese.cli.doctor")
        if imported.startswith("anki_")
    }
    offenders = sorted(
        str(name)
        for name in names
        if name in ACTIVATION_MUTATIONS
        or (name or "").startswith(("run_", "write_", "save_", "delete_", "apply_"))
    )
    assert not offenders, f"`doctor` is read-only: {offenders}"


# ── Deterministic song planning ───────────────────────────────────────

NONDETERMINISTIC = (
    "pypinyin",
    "opencc",
    "jieba",
    "google",
    "openai",
    "anthropic",
    "googletrans",
    "deep_translator",
    "translate",
    "anki_chinese.sentences",
    "anki_chinese.data_sources",
    "anki_chinese.audio",
    "anki_chinese.tutor",
)


def test_song_planning_stays_deterministic() -> None:
    reachable = _closure("anki_chinese.songs.analysis", "anki_chinese.songs.lyrics")
    offenders = sorted(
        f"{module} -> {imported}"
        for module in reachable
        for imported in _imported_modules(module)
        if _matches(imported, NONDETERMINISTIC)
    )
    assert not offenders, (
        "Song planning must not guess readings or translate; see "
        f"docs/decisions/study-target-policy.md: {offenders}"
    )


def test_import_scanner_sees_known_edges() -> None:
    """Guard the scanner itself so the boundary tests cannot pass vacuously."""
    assert "anki_chinese.songs.lyrics" in _imported_modules("anki_chinese.songs.analysis")
    assert ("anki_chinese.activation", "AnkiConnectClient") in _imports("anki_chinese.cli.doctor")
    assert "anki_chinese.audio.google_tts" in _imported_modules("anki_chinese.audio.factory")
    assert "google.oauth2" in _imported_modules("anki_chinese.audio.google_tts")

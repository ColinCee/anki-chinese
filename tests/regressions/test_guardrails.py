"""AGENTS.md guardrails, enforced by reading the source rather than trusting review."""

from __future__ import annotations

import ast
import sys
from functools import cache
from pathlib import Path

import genanki

import anki_chinese
from anki_chinese.activation import AnkiConnectClient
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


# Vendor-neutral audio modules; any other `audio/` module is a provider implementation.
AUDIO_NEUTRAL = {
    f"anki_chinese.audio{suffix}"
    for suffix in (
        "",
        ".provider",
        ".factory",
        ".state",
        ".files",
        ".errors",
        ".pinyin",
        ".retry",
        ".rate_limit",
    )
}
# What code outside `audio/` may import: protocol, construction, provenance, filenames.
AUDIO_PUBLIC = {f"anki_chinese.audio{s}" for s in ("", ".provider", ".factory", ".state", ".files")}


def _is_third_party(imported: str) -> bool:
    top = imported.partition(".")[0]
    return top != "anki_chinese" and top not in sys.stdlib_module_names


def test_audio_providers_stay_behind_factory() -> None:
    audio = [m for m in _modules() if _inside(m, "anki_chinese.audio")]
    vendors = {m for m in audio if m not in AUDIO_NEUTRAL}
    offenders = sorted(
        f"{module} -> {imported}"
        for module in _modules()
        for imported in _imported_modules(module)
        if _inside(imported, "anki_chinese.audio")
        and module not in vendors
        and (
            (not _inside(module, "anki_chinese.audio") and imported not in AUDIO_PUBLIC)
            or (imported in vendors and module != "anki_chinese.audio.factory")
        )
    )
    offenders += sorted(
        f"{module} -> {imported}"
        for module in audio
        if module in AUDIO_NEUTRAL
        for imported in _imported_modules(module)
        if _is_third_party(imported)
    )
    assert vendors, "no provider implementations found; update AUDIO_NEUTRAL"
    assert not offenders, (
        "Provider details stay in provider modules built by `audio/factory.py`; "
        f"elsewhere use the `audio` package, provider, factory, state or files: {offenders}"
    )


def _client_methods() -> set[str]:
    return {
        name
        for name, value in vars(AnkiConnectClient).items()
        if callable(value) and name != "__init__"
    }


def _client_calls(module: str) -> set[str]:
    """AnkiConnectClient method names referenced as attributes anywhere in a module."""
    tree = ast.parse(_modules()[module].read_text(encoding="utf-8"))
    methods = _client_methods()
    return {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)} & methods


# Read-only AnkiConnectClient methods. New client methods count as mutations until listed.
CLIENT_READS = {
    "version",
    "find_notes_by_chars",
    "find_notes_by_template",
    "find_notes_by_tag",
    "suspended_card_ids",
    "find_studied_characters",
    "find_active_characters",
    "find_all_deck_info",
}
ACTIVATION_MUTATIONS = {
    name
    for name in ACTIVATION_EXPORTS
    if name.startswith(("activate_", "resuspend_", "suspend_", "undo_", "write_"))
}


def test_workbench_only_reads_live_anki_directly() -> None:
    tui = [m for m in _modules() if _inside(m, "anki_chinese.tui")]
    offenders = sorted(
        f"{module}: {name or imported}"
        for module in tui
        for imported, name in _imports(module)
        if (_inside(imported, "anki_chinese.activation") and name in ACTIVATION_MUTATIONS)
        or _matches(imported, ("anki_chinese.activation.service", "anki_chinese.cli.activate"))
    )
    offenders += sorted(f"{m}: client.{c}" for m in tui for c in _client_calls(m) - CLIENT_READS)
    assert ACTIVATION_MUTATIONS, "activation mutation exports were renamed; update this test"
    assert not offenders, f"The workbench must not mutate live Anki directly: {offenders}"


FILE_WRITES = {"write_text", "write_bytes", "mkdir", "unlink", "rmdir", "touch", "dump"}
WRITE_MODULES = ("shutil", "tempfile", "sqlite3", "subprocess")


def test_doctor_is_read_only_and_only_probes_version() -> None:
    doctor = "anki_chinese.cli.doctor"
    tree = ast.parse(_modules()[doctor].read_text(encoding="utf-8"))
    offenders = sorted(f"client.{c}" for c in _client_calls(doctor) - {"version"})
    offenders += sorted(
        str(name)
        for imported, name in _imports(doctor)
        if imported.startswith("anki_")
        and (
            name in ACTIVATION_MUTATIONS
            or (name or "").startswith(("run_", "write_", "save_", "delete_", "apply_"))
        )
    )
    offenders += sorted(m for m in _imported_modules(doctor) if _matches(m, WRITE_MODULES))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in FILE_WRITES:
            offenders.append(f".{node.attr}")
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
            offenders.append("open()")
    assert not offenders, (
        f"`doctor` is read-only and `--check-anki` only calls version: {offenders}"
    )


# ── Deterministic song planning ───────────────────────────────────────

# Everything song planning may import. Additions need a deterministic, offline reason;
# readings, LLMs, translation, segmentation and network clients do not qualify.
SONG_PLANNING_ALLOWED = {
    "__future__",
    "collections",
    "dataclasses",
    "pathlib",
    "re",
    "anki_chinese.songs.analysis",
    "anki_chinese.songs.lyrics",
}


def test_song_planning_imports_only_allowlisted_modules() -> None:
    reachable = _closure("anki_chinese.songs.analysis", "anki_chinese.songs.lyrics")
    offenders = sorted(
        f"{module} -> {imported}"
        for module in reachable
        for imported in _imported_modules(module)
        if imported not in SONG_PLANNING_ALLOWED
    )
    assert not offenders, (
        "Song planning must stay deterministic and offline (no LLM, translation, OpenCC, "
        f"pypinyin or network); see docs/decisions/study-target-policy.md: {offenders}"
    )


def test_import_scanner_sees_known_edges() -> None:
    """Guard the scanner itself so the boundary tests cannot pass vacuously."""
    assert "anki_chinese.songs.lyrics" in _imported_modules("anki_chinese.songs.analysis")
    assert ("anki_chinese.activation", "AnkiConnectClient") in _imports("anki_chinese.cli.doctor")
    assert "anki_chinese.audio.google_tts" in _imported_modules("anki_chinese.audio.factory")
    assert "google.oauth2" in _imported_modules("anki_chinese.audio.google_tts")
    assert "version" in _client_calls("anki_chinese.cli.doctor")
    assert {"find_active_characters"} <= _client_calls("anki_chinese.tui.dashboard_model")
    assert {"_invoke", "unsuspend_cards", "version"} <= _client_methods()

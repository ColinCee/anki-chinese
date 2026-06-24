"""`anki-chinese sentences` command."""

from __future__ import annotations

import os
from collections import Counter

import typer
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..notes import (
    CharacterNote,
    PhoneticConfuser,
    SentencePinyinIssue,
    audit_sentence_pinyin,
    filter_from_rsh,
    find_phonetic_confuser_details,
    prioritize_learned,
)
from ..sentences import SentenceResult
from ..workflows.pipeline_state import record_stage
from .app import AppRuntime
from .interaction import require_interactive_terminal


def apply_sentence(note: CharacterNote, result: SentenceResult) -> None:
    """Write a sentence result onto a note, clearing stale audio."""
    note.sentence = result.sentence
    note.sentence_pinyin = result.pinyin
    note.sentence_english = result.english
    if result.meaning:
        note.meaning = result.meaning
    if result.character_pinyin:
        note.pinyin = result.character_pinyin
    note.sentence_audio = ""


def _candidates_table(candidates: list[SentenceResult]) -> Table:
    """Build a Rich table showing numbered sentence candidates."""
    table = Table(show_header=True, show_lines=True)
    table.add_column("#", style="bold", width=3)
    table.add_column("Sentence", style="cyan")
    table.add_column("Pinyin")
    table.add_column("English")
    table.add_column("Meaning", style="green")
    table.add_column("Reading", style="magenta")
    table.add_column("OK", width=3)
    for i, c in enumerate(candidates, 1):
        ok = "[green]✓[/green]" if c.valid else "[red]✗[/red]"
        table.add_row(str(i), c.sentence, c.pinyin, c.english, c.meaning, c.character_pinyin, ok)
    return table


def _format_confusers(confusers: list[PhoneticConfuser]) -> str:
    return ", ".join(f"{c.character}({c.pinyin}, {c.severity})" for c in confusers)


def _sentence_audit_table(
    issues: list[tuple[CharacterNote, list[PhoneticConfuser]]],
    *,
    limit: int = 0,
) -> Table:
    table = Table(title="Sentence phonetic ambiguity")
    table.add_column("RSH", justify="right")
    table.add_column("Char", style="bold cyan")
    table.add_column("Pinyin", style="magenta")
    table.add_column("Sentence")
    table.add_column("Confusers", style="yellow")

    shown = issues[:limit] if limit > 0 else issues
    for note, confusers in shown:
        table.add_row(
            note.heisig_num,
            note.hanzi,
            note.pinyin,
            note.sentence,
            _format_confusers(confusers),
        )
    return table


def _sentence_pinyin_audit_table(
    issues: list[tuple[CharacterNote, SentencePinyinIssue]],
    *,
    limit: int = 0,
) -> Table:
    table = Table(title="Sentence pinyin mismatches")
    table.add_column("RSH", justify="right")
    table.add_column("Char", style="bold cyan")
    table.add_column("Reason", style="yellow")
    table.add_column("Sentence")
    table.add_column("Stored pinyin")
    table.add_column("Expected pinyin", style="green")

    shown = issues[:limit] if limit > 0 else issues
    for note, issue in shown:
        table.add_row(
            note.heisig_num,
            note.hanzi,
            issue.reason,
            note.sentence,
            issue.stored_pinyin,
            issue.expected_pinyin,
        )
    return table


def _find_sentence_confuser_issues(
    notes: list[CharacterNote],
    *,
    include_same_final: bool = False,
    char: str = "",
    limit: int = 0,
) -> list[tuple[CharacterNote, list[PhoneticConfuser]]]:
    issues: list[tuple[CharacterNote, list[PhoneticConfuser]]] = []

    for note in notes:
        if char and note.hanzi != char:
            continue
        if not note.sentence or not note.pinyin:
            continue
        confusers = find_phonetic_confuser_details(
            note.hanzi,
            note.pinyin,
            note.sentence,
            note.sentence_pinyin,
            include_same_final=include_same_final,
        )
        if confusers:
            issues.append((note, confusers))

    return issues[:limit] if limit > 0 else issues


def _find_sentence_pinyin_issues(
    notes: list[CharacterNote],
    *,
    char: str = "",
    limit: int = 0,
) -> list[tuple[CharacterNote, SentencePinyinIssue]]:
    issues: list[tuple[CharacterNote, SentencePinyinIssue]] = []
    for note in notes:
        if char and note.hanzi != char:
            continue
        if not note.sentence:
            continue
        issue = audit_sentence_pinyin(note.sentence, note.sentence_pinyin)
        if issue is not None:
            issues.append((note, issue))
    return issues[:limit] if limit > 0 else issues


def run_sentence_audit(
    runtime: AppRuntime,
    *,
    include_same_final: bool = False,
    limit: int = 0,
) -> list[tuple[CharacterNote, list[PhoneticConfuser]]]:
    """Report sentences with other characters that can sound like the target."""
    notes = runtime.note_store.load()
    issues = _find_sentence_confuser_issues(
        notes,
        include_same_final=include_same_final,
    )

    if not issues:
        runtime.console.print("[green]✓[/green] No sentence phonetic ambiguity found")
        return issues

    severity_counts = Counter(
        confuser.severity for _, confusers in issues for confuser in confusers
    )
    summary = ", ".join(f"{severity}: {count}" for severity, count in severity_counts.items())
    runtime.console.print(
        f"[yellow]⚠[/yellow] {len(issues)} sentences with phonetic ambiguity"
        f" ({summary})"
    )
    runtime.console.print(_sentence_audit_table(issues, limit=limit))
    if limit > 0 and len(issues) > limit:
        runtime.console.print(f"[dim]... and {len(issues) - limit} more[/dim]")
    return issues


def run_sentence_pinyin_audit(
    runtime: AppRuntime,
    *,
    char: str = "",
    limit: int = 0,
) -> list[tuple[CharacterNote, SentencePinyinIssue]]:
    """Report sentences whose stored pinyin does not match local pypinyin."""
    notes = runtime.note_store.load()
    issues = _find_sentence_pinyin_issues(notes, char=char)

    if not issues:
        runtime.console.print("[green]✓[/green] No sentence pinyin mismatches found")
        return issues

    reason_counts = Counter(issue.reason for _, issue in issues)
    summary = ", ".join(f"{reason}: {count}" for reason, count in reason_counts.items())
    runtime.console.print(
        f"[yellow]⚠[/yellow] {len(issues)} sentence pinyin mismatches ({summary})"
    )
    runtime.console.print(_sentence_pinyin_audit_table(issues, limit=limit))
    if limit > 0 and len(issues) > limit:
        runtime.console.print(f"[dim]... and {len(issues) - limit} more[/dim]")
    return issues


def _result_confusers(note: CharacterNote, result: SentenceResult) -> list[PhoneticConfuser]:
    return find_phonetic_confuser_details(
        note.hanzi,
        result.character_pinyin or note.pinyin,
        result.sentence,
        result.pinyin,
    )


def run_repair_confusers(
    runtime: AppRuntime,
    *,
    apply: bool = False,
    char: str = "",
    limit: int = 0,
    attempts: int = 3,
) -> list[CharacterNote]:
    """Regenerate only sentences currently failing the phonetic ambiguity audit."""
    notes = runtime.note_store.load()
    if char and not any(note.hanzi == char for note in notes):
        runtime.console.print(f"[red]✗[/red] Character '{char}' not found")
        raise typer.Exit(1)

    issues = _find_sentence_confuser_issues(notes, char=char, limit=limit)
    if not issues:
        runtime.console.print("[green]✓[/green] No sentence confusers to repair")
        return notes

    runtime.console.print(
        f"[yellow]⚠[/yellow] {len(issues)} sentence"
        f"{'' if len(issues) == 1 else 's'} selected for confuser repair"
    )
    runtime.console.print(_sentence_audit_table(issues))

    if not apply:
        runtime.console.print(
            "[dim]Dry run only. Re-run with --apply to regenerate these sentences.[/dim]"
        )
        return notes

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        runtime.console.print(
            "[red]✗[/red] GEMINI_API_KEY not set — cannot repair sentences.\n"
            "  Set it in .env or environment, then re-run with --apply."
        )
        raise typer.Exit(1)

    from ..sentences import SentenceGenerator

    generator = SentenceGenerator(api_key=api_key)
    repaired = 0
    failed: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=runtime.console,
    ) as progress:
        task_id = progress.add_task("Repairing", total=len(issues))
        for note, _confusers in issues:
            progress.update(task_id, description=f"[cyan]{note.hanzi}[/cyan]")
            result: SentenceResult | None = None
            confusers: list[PhoneticConfuser] = []
            failure = "no sentence returned"
            for _ in range(max(1, attempts)):
                result = generator.generate(note.hanzi, pinyin=note.pinyin)
                confusers = _result_confusers(note, result) if result.sentence else []
                if not result.sentence:
                    failure = result.error or "no sentence returned"
                elif confusers:
                    failure = f"still ambiguous ({_format_confusers(confusers)})"
                elif not result.valid:
                    failure = f"validation failed ({result.error})"
                else:
                    break
            if result is not None and result.sentence and not confusers and result.valid:
                old_sentence = note.sentence
                apply_sentence(note, result)
                runtime.note_store.save(notes)
                repaired += 1
                runtime.console.print(
                    f"[green]✓[/green] {note.hanzi}: {old_sentence} → {result.sentence}"
                )
            else:
                failed.append(f"{note.hanzi}: {failure}")
            progress.advance(task_id)

    runtime.note_store.save(notes)
    if repaired:
        record_stage(
            runtime.pipeline_state_path,
            "repair_confusers",
            inputs={"enriched": runtime.note_store.path},
            outputs={"enriched": runtime.note_store.path},
        )
    runtime.console.print(f"[green]✓[/green] Repaired {repaired}/{len(issues)} sentences")
    if failed:
        runtime.console.print(f"[yellow]⚠ {len(failed)} repairs failed[/yellow]")
        for item in failed[:20]:
            runtime.console.print(f"  • {item}")
    return notes


def _pick_sentence(runtime: AppRuntime, generator, note: CharacterNote, count: int) -> bool:
    """Generate candidates in a loop until the user picks or skips."""
    runtime.console.print(
        f"\n[blue]Generating {count} candidates for[/blue] [bold]{note.hanzi}[/bold] "
        f"({note.meaning})"
    )
    if note.sentence:
        runtime.console.print(f"  [dim]Current: {note.sentence} — {note.sentence_english}[/dim]")

    while True:
        candidates = generator.generate_candidates(note.hanzi, count=count, pinyin=note.pinyin)
        if not candidates:
            runtime.console.print("[red]✗[/red] No valid candidates generated")
            return False

        runtime.console.print(_candidates_table(candidates))
        choice = typer.prompt(
            "Pick a sentence (number), or 's' to skip, 'r' to regenerate",
            default="1",
        )

        if choice.lower() == "s":
            runtime.console.print("[dim]Skipped[/dim]")
            return False
        if choice.lower() == "r":
            continue

        try:
            idx = int(choice) - 1
            if not 0 <= idx < len(candidates):
                runtime.console.print("[red]Invalid choice[/red]")
                return False
        except ValueError:
            runtime.console.print("[red]Invalid choice[/red]")
            return False

        apply_sentence(note, candidates[idx])
        runtime.console.print(f"[green]✓[/green] Saved: {candidates[idx].sentence}")
        return True


def run_sentences(
    runtime: AppRuntime,
    *,
    char: str = "",
    limit: int = 0,
    start_rsh: int = 0,
    force: bool = False,
    pick: int = 0,
) -> list[CharacterNote]:
    """Generate example sentences for notes that don't have them yet."""
    if pick:
        require_interactive_terminal(
            runtime.console,
            action="Sentence pick mode",
            hint="Run [bold]sentences[/bold] without [bold]--pick[/bold] for non-interactive generation.",
        )

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        runtime.console.print(
            "[yellow]⚠[/yellow] GEMINI_API_KEY not set — skipping sentence generation.\n"
            "  Set it in .env or environment to enable."
        )
        return runtime.note_store.load()

    from ..sentences import SentenceGenerator

    generator = SentenceGenerator(api_key=api_key)

    notes = runtime.note_store.load()
    targets = notes

    if char:
        targets = [n for n in notes if n.hanzi == char]
        if not targets:
            runtime.console.print(f"[red]✗[/red] Character '{char}' not found")
            raise typer.Exit(1)
    else:
        if start_rsh > 0:
            targets = filter_from_rsh(targets, start_rsh)
        if not force and not pick:
            targets = [n for n in targets if not n.sentence]
        # Prioritize learned characters before applying limit
        learned = runtime.load_learned_hanzi(runtime.source_deck_path)
        if learned:
            targets = prioritize_learned(targets, learned)
        if limit > 0:
            targets = targets[:limit]
        if learned:
            learned_count = sum(1 for n in targets if n.hanzi in learned)
            runtime.console.print(f"  [dim]{learned_count} learned characters prioritized[/dim]")

    if not targets:
        runtime.console.print("[green]✓[/green] All notes already have sentences")
        return notes

    # Interactive pick mode
    if pick > 0:
        picked = 0
        for note in targets:
            if _pick_sentence(runtime, generator, note, count=pick):
                picked += 1
        runtime.note_store.save(notes)
        if picked:
            record_stage(
                runtime.pipeline_state_path,
                "sentences",
                inputs={"enriched": runtime.note_store.path},
                outputs={"enriched": runtime.note_store.path},
            )
        return notes

    runtime.console.print(f"[blue]Generating sentences[/blue] for {len(targets)} notes ...")

    generated = 0
    failed = 0
    retried = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=runtime.console,
    ) as progress:
        task_id = progress.add_task("Sentences", total=len(targets))
        for note in targets:
            progress.update(task_id, description=f"[cyan]{note.hanzi}[/cyan]")
            try:
                result = generator.generate(note.hanzi, pinyin=note.pinyin)
                apply_sentence(note, result)
                # Preserve audio tag — batch mode doesn't clear it
                # (audio command handles generation separately)
                if result.valid:
                    generated += 1
                else:
                    failed += 1
                if result.error:
                    retried += 1
            except Exception as exc:
                runtime.console.print(f"  [red]✗[/red] {note.hanzi}: {exc}")
                failed += 1
            progress.advance(task_id)

    runtime.note_store.save(notes)
    if generated:
        record_stage(
            runtime.pipeline_state_path,
            "sentences",
            inputs={"enriched": runtime.note_store.path},
            outputs={"enriched": runtime.note_store.path},
        )
    runtime.console.print(
        f"[green]✓[/green] Generated {generated} sentences"
        + (f", {retried} retried" if retried else "")
        + (f", [red]{failed} failed[/red]" if failed else "")
    )
    return notes


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    sentences_app = typer.Typer(
        name="sentences",
        help="Generate, audit, and repair example sentences.",
        no_args_is_help=False,
    )

    @sentences_app.callback(invoke_without_command=True)
    def sentences(
        ctx: typer.Context,
        char: str = typer.Option("", "--char", "-c", help="Generate for one character only."),
        limit: int = typer.Option(0, "--limit", "-n", help="Max notes to process."),
        start_rsh: int = typer.Option(0, "--from-rsh", help="Start from RSH number."),
        force: bool = typer.Option(
            False, "--force", "-f", help="Regenerate even if sentence exists."
        ),
        pick: int = typer.Option(
            0, "--pick", "-p", help="Generate N candidates and pick interactively."
        ),
    ) -> None:
        """Generate example sentences using Gemini AI."""
        if ctx.invoked_subcommand is not None:
            return
        run_sentences(runtime, char=char, limit=limit, start_rsh=start_rsh, force=force, pick=pick)

    @sentences_app.command("audit")
    def audit_command(
        include_same_final: bool = typer.Option(
            False,
            "--include-same-final",
            help="Also flag broad same-rhyme/final matches. This can be noisy.",
        ),
        limit: int = typer.Option(0, "--limit", "-n", help="Max rows to display."),
    ) -> None:
        """Audit existing example sentences for audio-confusing characters."""
        run_sentence_audit(runtime, include_same_final=include_same_final, limit=limit)

    @sentences_app.command("audit-pinyin")
    def audit_pinyin_command(
        char: str = typer.Option("", "--char", "-c", help="Audit one character only."),
        limit: int = typer.Option(0, "--limit", "-n", help="Max rows to display."),
    ) -> None:
        """Audit existing example sentence pinyin against local pypinyin."""
        run_sentence_pinyin_audit(runtime, char=char, limit=limit)

    @sentences_app.command("repair-confusers")
    def repair_confusers_command(
        apply: bool = typer.Option(
            False,
            "--apply",
            help="Regenerate and save replacements. Without this, only shows a dry run.",
        ),
        char: str = typer.Option("", "--char", "-c", help="Repair one character only."),
        limit: int = typer.Option(0, "--limit", "-n", help="Max notes to repair."),
        attempts: int = typer.Option(3, "--attempts", min=1, help="Generation attempts per note."),
    ) -> None:
        """Regenerate sentences that contain phonetic confusers."""
        run_repair_confusers(runtime, apply=apply, char=char, limit=limit, attempts=attempts)

    app.add_typer(sentences_app, name="sentences")

    @app.command("sentences-audit", hidden=True)
    def sentences_audit(
        include_same_final: bool = typer.Option(
            False,
            "--include-same-final",
            help="Also flag broad same-rhyme/final matches. This can be noisy.",
        ),
        limit: int = typer.Option(0, "--limit", "-n", help="Max rows to display."),
    ) -> None:
        """Audit existing example sentences for audio-confusing characters."""
        run_sentence_audit(runtime, include_same_final=include_same_final, limit=limit)

    @app.command("sentences-pinyin-audit", hidden=True)
    def sentences_pinyin_audit(
        char: str = typer.Option("", "--char", "-c", help="Audit one character only."),
        limit: int = typer.Option(0, "--limit", "-n", help="Max rows to display."),
    ) -> None:
        """Top-level alias for `sentences audit-pinyin`."""
        run_sentence_pinyin_audit(runtime, char=char, limit=limit)

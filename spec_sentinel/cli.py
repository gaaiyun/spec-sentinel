"""Typer CLI for spec-sentinel."""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import List, Optional

import click
import typer

from spec_sentinel import __version__
from spec_sentinel.engine import lint_file
from spec_sentinel.models import LintReport
from spec_sentinel.reporters import (
    render_human,
    render_json,
    render_sarif,
    render_summary,
)
from spec_sentinel.rules import ALL_RULES

app = typer.Typer(
    add_completion=False,
    help="A spec-quality linter for AI coding agents: ambiguity, "
    "testability, acceptance-criteria and traceability checks plus a "
    "0-100 readiness score.",
    no_args_is_help=True,
)

_SPEC_GLOBS = ("*.md", "*.markdown", "*.yaml", "*.yml")


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    sarif = "sarif"


def _collect_paths(paths: List[Path]) -> List[Path]:
    """Expand directories into spec files; keep explicit files as-is."""
    out: List[Path] = []
    for p in paths:
        if p.is_dir():
            for pattern in _SPEC_GLOBS:
                out.extend(sorted(p.rglob(pattern)))
        else:
            out.append(p)
    # de-duplicate while preserving order
    seen = set()
    unique: List[Path] = []
    for p in out:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            unique.append(p)
    return unique


@app.command()
def lint(
    paths: List[Path] = typer.Argument(
        ...,
        exists=True,
        help="Spec files or directories to lint (.md / .yaml).",
    ),
    threshold: float = typer.Option(
        70.0,
        "--threshold",
        "-t",
        min=0,
        max=100,
        help="Minimum readiness score to pass; below this exits non-zero.",
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.text,
        "--format",
        "-f",
        help="Output format.",
    ),
    select: Optional[List[str]] = typer.Option(
        None,
        "--select",
        help="Only run these rule ids (repeatable).",
    ),
    disable: Optional[List[str]] = typer.Option(
        None,
        "--disable",
        help="Skip these rule ids (repeatable).",
    ),
    no_suggestions: bool = typer.Option(
        False,
        "--no-suggestions",
        help="Hide remediation hints in text output.",
    ),
) -> None:
    """Lint one or more spec files and score their readiness.

    Exit code is 1 if any file scores below the threshold or has an
    error-level diagnostic, so this drops straight into pre-commit or CI.
    """
    files = _collect_paths(paths)
    if not files:
        typer.secho("no spec files found", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    reports: List[LintReport] = []
    for f in files:
        try:
            report = lint_file(
                str(f),
                threshold=threshold,
                select=select or None,
                disable=disable or None,
            )
        except KeyError as exc:  # unknown rule id
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2)
        except Exception as exc:  # parse / IO error on one file
            typer.secho(f"{f}: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2)
        reports.append(report)

    if fmt is OutputFormat.json:
        typer.echo(render_json(reports))
    elif fmt is OutputFormat.sarif:
        typer.echo(render_sarif(reports))
    else:
        for report in reports:
            typer.echo(render_human(report, show_suggestions=not no_suggestions))
            typer.echo("")
        if len(reports) > 1:
            typer.echo(render_summary(reports))

    # Fail if any file is below threshold or carries an error.
    failed = any(
        (not r.score.passed) or r.error_count > 0 for r in reports
    )
    raise typer.Exit(code=1 if failed else 0)


@app.command()
def rules() -> None:
    """List the built-in rules and their default severity."""
    typer.echo(f"{len(ALL_RULES)} rules:")
    for r in ALL_RULES:
        typer.echo(f"  {r.severity.value:<7} {r.id:<28} {r.description}")


@app.command()
def version() -> None:
    """Print the version and exit."""
    typer.echo(f"spec-sentinel {__version__}")


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point used by ``python -m spec_sentinel`` and the console script.

    Runs the Typer app with ``standalone_mode=False`` so that, instead of
    calling ``sys.exit`` itself, Click hands back the chosen exit code as
    the return value. We forward that code; ``typer.Exit`` raised inside a
    command surfaces as that return value too.
    """
    try:
        result = app(args=argv, standalone_mode=False)
        # Click returns the command's return value, or the Exit code when a
        # command raised typer.Exit. Treat a bare int as the exit code.
        if isinstance(result, int):
            return result
        return 0
    except typer.Exit as exc:
        return int(exc.exit_code or 0)
    except click.ClickException as exc:  # usage errors -> code 2
        exc.show()
        return exc.exit_code
    except click.exceptions.Abort:
        typer.secho("aborted", fg=typer.colors.RED, err=True)
        return 1
    except SystemExit as exc:  # defensive: argparse-style failures
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else 1)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

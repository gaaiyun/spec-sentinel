"""Orchestration: parse a spec, run rules, compute the readiness score."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from spec_sentinel import parser
from spec_sentinel.models import Diagnostic, LintReport, SpecDocument
from spec_sentinel.rules import get_rules
from spec_sentinel.scoring import compute_readiness


def lint_document(
    doc: SpecDocument,
    threshold: float = 70.0,
    select: Optional[Sequence[str]] = None,
    disable: Optional[Sequence[str]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> LintReport:
    """Run the active rules over a parsed document and score it."""
    rules = get_rules(select=select, disable=disable)
    diagnostics: List[Diagnostic] = []
    for rule in rules:
        diagnostics.extend(rule.check(doc))

    # Stable ordering: by line, then column, then rule id.
    diagnostics.sort(key=lambda d: (d.line, d.column, d.rule_id))

    score = compute_readiness(
        doc, diagnostics, threshold=threshold, weights=weights
    )
    return LintReport(
        path=doc.path,
        diagnostics=diagnostics,
        score=score,
        requirement_count=len(doc.requirements),
    )


def lint_text(
    text: str,
    path: str = "<string>",
    is_yaml: bool = False,
    **kwargs,
) -> LintReport:
    """Parse raw text then lint it. Convenience wrapper for tests."""
    doc = parser.parse_yaml(text, path) if is_yaml else parser.parse_text(text, path)
    return lint_document(doc, **kwargs)


def lint_file(path: str, **kwargs) -> LintReport:
    """Parse a file from disk then lint it."""
    doc = parser.parse_file(path)
    return lint_document(doc, **kwargs)

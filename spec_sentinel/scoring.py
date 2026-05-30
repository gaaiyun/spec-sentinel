"""Readiness scoring across four quality dimensions.

The scoring model is adapted from the weighted, normalised multi-factor
approach used for RICE/Kano priority scoring in the project's earlier
life: compute an independent 0-1 sub-score per factor, then blend with
configurable weights into a single 0-100 figure. Here the four factors
are the qualities that decide whether a spec is ready for an AI coding
agent:

* **coverage**     - does every requirement have acceptance criteria?
* **clarity**      - how free of vague/weak wording is the prose?
* **testability**  - are requirements phrased so a test can pass/fail?
* **traceability** - do requirements carry stable identifiers?

Each dimension is derived from the parsed document and the diagnostics
the rules produced, so the score and the line-level findings always
agree.
"""

from __future__ import annotations

from typing import Dict, List

from spec_sentinel.models import (
    Diagnostic,
    DimensionScore,
    ReadinessScore,
    Severity,
    SpecDocument,
)

# Default blend weights. They sum to 1.0; the engine renormalises if a
# caller overrides a subset.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "coverage": 0.30,
    "clarity": 0.25,
    "testability": 0.25,
    "traceability": 0.20,
}


def _ratio(good: int, total: int) -> float:
    """Fraction in [0, 1]; an empty population scores a neutral 1.0.

    A spec with no requirements is not penalised on per-requirement
    dimensions (there is nothing to get wrong); the coverage dimension
    handles the "no requirements at all" case separately.
    """
    if total <= 0:
        return 1.0
    return max(0.0, min(1.0, good / total))


def _coverage_score(doc: SpecDocument) -> DimensionScore:
    """Share of requirements that have acceptance criteria."""
    total = len(doc.requirements)
    if total == 0:
        return DimensionScore(
            name="coverage",
            score=0.0,
            detail="no requirements detected in the document",
        )
    with_ac = sum(1 for r in doc.requirements if r.has_acceptance_criteria)
    score = _ratio(with_ac, total) * 100
    return DimensionScore(
        name="coverage",
        score=round(score, 1),
        detail=f"{with_ac}/{total} requirements have acceptance criteria",
    )


def _clarity_score(doc: SpecDocument, diagnostics: List[Diagnostic]) -> DimensionScore:
    """Penalise vague terms and weak verbs, scaled by document size.

    We count wording diagnostics against the number of prose lines so a
    long, mostly-clear spec is not dragged down by a couple of slips,
    while a short spec riddled with vague terms scores low.
    """
    wording_ids = {"ambiguous-term", "weak-verb"}
    hits = sum(1 for d in diagnostics if d.rule_id in wording_ids)
    prose_lines = max(1, sum(1 for ln in doc.lines if ln.strip()))
    # density of problems per prose line, capped so it cannot exceed 1
    density = min(1.0, hits / prose_lines)
    score = (1.0 - density) * 100
    return DimensionScore(
        name="clarity",
        score=round(score, 1),
        detail=f"{hits} vague/weak wording issue(s) across {prose_lines} prose line(s)",
    )


def _testability_score(doc: SpecDocument, diagnostics: List[Diagnostic]) -> DimensionScore:
    """Share of requirements that are observably testable / quantified."""
    total = len(doc.requirements)
    if total == 0:
        return DimensionScore(
            name="testability",
            score=0.0,
            detail="no requirements detected in the document",
        )
    untestable_lines = {
        d.line
        for d in diagnostics
        if d.rule_id in {"untestable-requirement", "unquantified-nfr"}
    }
    bad = sum(1 for r in doc.requirements if r.line in untestable_lines)
    good = total - bad
    score = _ratio(good, total) * 100
    return DimensionScore(
        name="testability",
        score=round(score, 1),
        detail=f"{good}/{total} requirements are testable/quantified",
    )


def _traceability_score(doc: SpecDocument) -> DimensionScore:
    """Share of requirements carrying a stable identifier."""
    total = len(doc.requirements)
    if total == 0:
        return DimensionScore(
            name="traceability",
            score=0.0,
            detail="no requirements detected in the document",
        )
    with_id = sum(1 for r in doc.requirements if r.identifier)
    score = _ratio(with_id, total) * 100
    return DimensionScore(
        name="traceability",
        score=round(score, 1),
        detail=f"{with_id}/{total} requirements have a traceable id",
    )


def compute_readiness(
    doc: SpecDocument,
    diagnostics: List[Diagnostic],
    threshold: float = 70.0,
    weights: Dict[str, float] | None = None,
) -> ReadinessScore:
    """Blend the four dimensions into a 0-100 readiness score.

    Mirrors the normalise-then-weight pattern from the legacy priority
    scorer: each dimension is already on a 0-100 scale, weights are
    renormalised to sum to 1.0, and the overall score is their weighted
    mean. ``passed`` compares the overall score against ``threshold``.
    """
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)
    total_w = sum(w.values())
    if total_w <= 0:
        raise ValueError("weights must sum to a positive value")

    coverage = _coverage_score(doc)
    clarity = _clarity_score(doc, diagnostics)
    testability = _testability_score(doc, diagnostics)
    traceability = _traceability_score(doc)

    overall = (
        coverage.score * w["coverage"]
        + clarity.score * w["clarity"]
        + testability.score * w["testability"]
        + traceability.score * w["traceability"]
    ) / total_w

    overall = round(overall, 1)
    return ReadinessScore(
        coverage=coverage,
        clarity=clarity,
        testability=testability,
        traceability=traceability,
        overall=overall,
        threshold=threshold,
        passed=overall >= threshold,
    )

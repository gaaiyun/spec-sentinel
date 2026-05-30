"""Structural rules about a spec's completeness and testability.

Where the wording rules look at individual phrases, these look at whole
requirements: does each normative statement have acceptance criteria, is
it phrased so a test could pass or fail on it, and are non-functional
requirements actually quantified.
"""

from __future__ import annotations

import re
from typing import Iterable

from spec_sentinel.models import Diagnostic, Severity, SpecDocument
from spec_sentinel.rules.base import Rule

# Keywords that mark a non-functional requirement (NFR).
_NFR_RE = re.compile(
    r"\b(performance|latency|throughput|availability|uptime|scalab|"
    r"response\s+time|concurren|load|memory|cpu|security|reliab|"
    r"durability|capacity)\b",
    re.IGNORECASE,
)

# A concrete, measurable value (number+unit, comparison, percentile).
_MEASURABLE_RE = re.compile(
    r"(\b\d+(\.\d+)?\s?(ms|s|sec|seconds?|m|min|minutes?|h|hours?|days?|%|"
    r"percent|rps|qps|req/s|requests?|users?|connections?|kb|mb|gb|tb)\b|"
    r"(<=|>=|<|>|≤|≥)\s?\d|\bp\d{2,3}\b|\bwithin\s+\d|\bat\s+least\s+\d|"
    r"\bno\s+more\s+than\s+\d)",
    re.IGNORECASE,
)

# Verbs/structures that make a requirement observably testable.
_TESTABLE_RE = re.compile(
    r"\b(return|returns|reject|rejects|display|displays|show|shows|"
    r"respond|responds|emit|emits|persist|persists|store|stores|log|logs|"
    r"redirect|redirects|validate|validates|raise|raises|equals?|"
    r"within|after|before|when|then)\b",
    re.IGNORECASE,
)


class MissingAcceptanceCriteriaRule(Rule):
    """A requirement with no acceptance criteria nearby."""

    id = "missing-acceptance-criteria"
    name = "missing acceptance criteria"
    severity = Severity.ERROR
    description = "Normative requirement without acceptance criteria."

    def check(self, doc: SpecDocument) -> Iterable[Diagnostic]:
        for req in doc.requirements:
            if req.has_acceptance_criteria:
                continue
            yield self._diag(
                doc,
                req.line,
                message="requirement has no acceptance criteria",
                suggestion=(
                    "add Given/When/Then, an 'Acceptance:' line, or a "
                    "'verified by' clause so the behaviour is checkable"
                ),
            )


class UntestableRequirementRule(Rule):
    """A requirement with no observable / verifiable outcome."""

    id = "untestable-requirement"
    name = "untestable requirement"
    severity = Severity.WARNING
    description = "Requirement with no observable outcome to test against."

    def check(self, doc: SpecDocument) -> Iterable[Diagnostic]:
        for req in doc.requirements:
            text = req.text
            if _TESTABLE_RE.search(text) or _MEASURABLE_RE.search(text):
                continue
            yield self._diag(
                doc,
                req.line,
                message="requirement has no observable, testable outcome",
                suggestion=(
                    "phrase as an observable result (returns / rejects / "
                    "displays / within N ms) a test can assert on"
                ),
            )


class UnquantifiedNFRRule(Rule):
    """A non-functional requirement that is not quantified."""

    id = "unquantified-nfr"
    name = "unquantified non-functional requirement"
    severity = Severity.ERROR
    description = "Non-functional requirement stated without a number."

    def check(self, doc: SpecDocument) -> Iterable[Diagnostic]:
        for req in doc.requirements:
            text = req.text
            if not _NFR_RE.search(text):
                continue
            if _MEASURABLE_RE.search(text) or req.is_quantified:
                continue
            yield self._diag(
                doc,
                req.line,
                message="non-functional requirement is not quantified",
                suggestion=(
                    "attach a target, e.g. 'p95 < 200 ms', '99.9% uptime', "
                    "'10k concurrent users'"
                ),
            )


class MissingAcceptanceSectionRule(Rule):
    """The whole document defines requirements but no acceptance section."""

    id = "no-acceptance-section"
    name = "no acceptance-criteria section"
    severity = Severity.INFO
    description = "Spec has requirements but no acceptance-criteria section."

    def check(self, doc: SpecDocument) -> Iterable[Diagnostic]:
        if not doc.requirements:
            return
        if doc.has_acceptance_section:
            return
        any_inline = any(r.has_acceptance_criteria for r in doc.requirements)
        if any_inline:
            return
        # Point at the first requirement so the diagnostic has a location.
        first = doc.requirements[0].line
        yield self._diag(
            doc,
            first,
            message=(
                "spec defines requirements but has no acceptance-criteria "
                "section"
            ),
            suggestion="add an 'Acceptance Criteria' section or per-requirement criteria",
        )

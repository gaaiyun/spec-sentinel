"""Traceability rule: requirements should carry stable identifiers.

An agent (and any downstream test or commit) needs a handle to refer
back to a requirement. Statements without an identifier such as REQ-001
cannot be traced into code or tests, so we flag them.
"""

from __future__ import annotations

from typing import Iterable

from spec_sentinel.models import Diagnostic, Severity, SpecDocument
from spec_sentinel.rules.base import Rule


class UntraceableRequirementRule(Rule):
    """A requirement with no explicit identifier."""

    id = "missing-requirement-id"
    name = "missing requirement id"
    severity = Severity.WARNING
    description = "Requirement without a stable identifier (e.g. REQ-001)."

    def check(self, doc: SpecDocument) -> Iterable[Diagnostic]:
        for req in doc.requirements:
            if req.identifier:
                continue
            yield self._diag(
                doc,
                req.line,
                message="requirement has no traceable identifier",
                suggestion=(
                    "prefix with an id like 'REQ-001' / 'FR-12' so it can "
                    "be traced into tests and commits"
                ),
            )

"""spec-sentinel: a spec-quality linter for AI coding agents.

Static checks on Markdown/YAML specs for ambiguity, testability, acceptance
criteria completeness and traceability, plus a 0-100 readiness score.
"""

__version__ = "0.1.0"

from spec_sentinel.models import (
    Diagnostic,
    LintReport,
    ReadinessScore,
    Severity,
    SpecDocument,
)

__all__ = [
    "Diagnostic",
    "LintReport",
    "ReadinessScore",
    "Severity",
    "SpecDocument",
    "__version__",
]

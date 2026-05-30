"""Core data models for spec-sentinel.

These are plain Pydantic models shared across the parser, rule engine,
scoring and reporters. Keeping them in one place means the JSON / SARIF
serialisation has a single source of truth.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Diagnostic severity, ordered from least to most serious."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def sarif_level(self) -> str:
        """Map to a SARIF ``level`` value."""
        return {
            Severity.INFO: "note",
            Severity.WARNING: "warning",
            Severity.ERROR: "error",
        }[self]


class Diagnostic(BaseModel):
    """A single problem found in a spec, anchored to a line.

    ``line`` and ``column`` are 1-based to match how editors and humans
    count. ``column`` is the start of the offending span; ``end_column``
    is exclusive.
    """

    rule_id: str
    severity: Severity
    message: str
    line: int = Field(ge=1)
    column: int = Field(default=1, ge=1)
    end_column: Optional[int] = Field(default=None, ge=1)
    snippet: str = ""
    suggestion: str = ""

    def location(self) -> str:
        """``line:column`` location string used in human output."""
        return f"{self.line}:{self.column}"


class Requirement(BaseModel):
    """A requirement statement extracted from the spec.

    A requirement is any line that reads like a normative statement
    (contains an RFC-2119 style modal such as *must*/*shall*/*should*,
    or sits under a "Requirements" heading as a list item). We track
    whether it has an explicit identifier and whether acceptance
    criteria were found for it, which feeds the readiness score.
    """

    line: int = Field(ge=1)
    text: str
    identifier: Optional[str] = None
    has_acceptance_criteria: bool = False
    is_quantified: bool = False


class Section(BaseModel):
    """A Markdown heading and the line it starts on."""

    title: str
    level: int = Field(ge=1)
    line: int = Field(ge=1)


class SpecDocument(BaseModel):
    """A parsed spec document.

    ``lines`` keeps the raw text (1-based access via :meth:`line_text`)
    so rules can re-scan content and reporters can show snippets.
    """

    path: str
    lines: List[str] = Field(default_factory=list)
    sections: List[Section] = Field(default_factory=list)
    requirements: List[Requirement] = Field(default_factory=list)
    has_acceptance_section: bool = False
    has_traceability: bool = False

    def line_text(self, line: int) -> str:
        """Return the raw text of a 1-based line, or empty string."""
        if 1 <= line <= len(self.lines):
            return self.lines[line - 1]
        return ""


class DimensionScore(BaseModel):
    """One axis of the readiness score (0-100) with a short reason."""

    name: str
    score: float = Field(ge=0, le=100)
    detail: str = ""


class ReadinessScore(BaseModel):
    """Aggregate readiness score across the four quality dimensions.

    ``overall`` is the weighted blend of the dimensions. ``passed`` is
    set by the engine against the configured threshold.
    """

    coverage: DimensionScore
    clarity: DimensionScore
    testability: DimensionScore
    traceability: DimensionScore
    overall: float = Field(ge=0, le=100)
    threshold: float = Field(default=70.0, ge=0, le=100)
    passed: bool = True

    def dimensions(self) -> List[DimensionScore]:
        return [self.coverage, self.clarity, self.testability, self.traceability]


class LintReport(BaseModel):
    """Everything produced for a single spec file."""

    path: str
    diagnostics: List[Diagnostic] = Field(default_factory=list)
    score: ReadinessScore
    requirement_count: int = 0

    def count(self, severity: Severity) -> int:
        return sum(1 for d in self.diagnostics if d.severity == severity)

    @property
    def error_count(self) -> int:
        return self.count(Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return self.count(Severity.WARNING)

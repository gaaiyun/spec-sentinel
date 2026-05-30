"""Base class shared by all rules."""

from __future__ import annotations

import re
from typing import Iterable, List

from spec_sentinel.models import Diagnostic, Severity, SpecDocument

# Lines that should never be linted as prose: headings, table separators,
# horizontal rules, link/image reference definitions.
_SKIP_LINE_RE = re.compile(r"^\s*(#{1,6}\s|\|?[-:\s|]+$|---+$|\[[^\]]+\]:)")


class Rule:
    """Base rule. Subclasses set ``id``/``severity`` and override ``check``."""

    id: str = "base"
    name: str = "base rule"
    severity: Severity = Severity.WARNING
    description: str = ""

    def check(self, doc: SpecDocument) -> Iterable[Diagnostic]:  # pragma: no cover
        raise NotImplementedError

    # -- helpers shared by subclasses ------------------------------------
    @staticmethod
    def _is_prose_line(text: str) -> bool:
        """True if a line is normal prose we should scan for wording."""
        if not text.strip():
            return False
        return _SKIP_LINE_RE.match(text) is None

    def _diag(
        self,
        doc: SpecDocument,
        line: int,
        message: str,
        column: int = 1,
        end_column: int | None = None,
        suggestion: str = "",
    ) -> Diagnostic:
        snippet = doc.line_text(line).strip()
        return Diagnostic(
            rule_id=self.id,
            severity=self.severity,
            message=message,
            line=line,
            column=column,
            end_column=end_column,
            snippet=snippet,
            suggestion=suggestion,
        )

    def _iter_prose(self, doc: SpecDocument) -> List[tuple[int, str]]:
        """Yield ``(line_number, text)`` for prose lines, skipping fences."""
        out: List[tuple[int, str]] = []
        in_fence = False
        for idx, raw in enumerate(doc.lines, start=1):
            stripped = raw.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if self._is_prose_line(raw):
                out.append((idx, raw))
        return out

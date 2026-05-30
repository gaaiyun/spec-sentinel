"""Wording rules: vague adjectives, weak verbs, subjective qualifiers.

These catch the language that reads fine to a human but gives a coding
agent nothing to implement against: "fast", "user-friendly", "handle
errors gracefully", "etc.". Each match points at the exact span so the
author can replace it with something concrete.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Tuple

from spec_sentinel.models import Diagnostic, Severity, SpecDocument
from spec_sentinel.rules.base import Rule

# Vague / unmeasurable terms grouped by theme. Each maps to a short hint
# on how to make it concrete. Matched as whole words, case-insensitive.
_VAGUE_TERMS: Dict[str, str] = {
    # speed / performance without a number
    "fast": "state a latency target, e.g. 'responds within 200 ms'",
    "quickly": "state a latency target, e.g. 'within 200 ms'",
    "slow": "quantify the threshold you consider too slow",
    "responsive": "define the response-time budget",
    "performant": "give a throughput or latency figure",
    "scalable": "state the load it must sustain, e.g. '10k concurrent users'",
    "lightweight": "define the resource budget (memory/CPU)",
    "efficient": "define the resource or time budget",
    # quality / UX adjectives
    "user-friendly": "describe the observable behaviour instead",
    "intuitive": "describe the observable behaviour instead",
    "seamless": "describe the observable behaviour instead",
    "robust": "list the failure modes it must survive",
    "reliable": "give an availability or error-rate target",
    "secure": "name the threat or control, e.g. 'TLS 1.2+, no plaintext'",
    "modern": "name the concrete technology or standard",
    "clean": "describe the measurable property you mean",
    "simple": "describe the measurable property you mean",
    "flexible": "list the specific variations it must support",
    "appropriate": "state the specific value or rule",
    "reasonable": "state the specific value or rule",
    "adequate": "state the specific value or rule",
    "sufficient": "state the specific value or rule",
    "acceptable": "define the acceptance threshold",
    "optimal": "state the target you are optimising for",
    "best": "state the measurable criterion",
    # vagueness / hand-waving
    "etc": "enumerate the items instead of trailing off",
    "and so on": "enumerate the items instead of trailing off",
    "and/or": "pick one, or spell out both cases",
    "various": "enumerate the cases",
    "several": "give the exact count",
    "some": "give the exact count or list",
    "many": "give the exact count",
    "few": "give the exact count",
    "most": "quantify the proportion",
    "as needed": "state the trigger condition",
    "if necessary": "state the trigger condition",
    "where applicable": "state when it applies",
    "tbd": "resolve before handing the spec to an agent",
    "to be determined": "resolve before handing the spec to an agent",
}

# Weak verb phrases that hide the real behaviour.
_WEAK_VERBS: Dict[str, str] = {
    "handle": "say exactly what happens (return, retry, log, reject...)",
    "support": "describe the supported behaviour and its limits",
    "manage": "say what operations are performed",
    "process": "describe the transformation precisely",
    "deal with": "say exactly what happens",
    "take care of": "say exactly what happens",
    "gracefully": "define the exact behaviour on failure",
}

_VAGUE_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _VAGUE_TERMS) + r")\b", re.IGNORECASE
)
_WEAK_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _WEAK_VERBS) + r")\b", re.IGNORECASE
)


def _find_spans(pattern: re.Pattern, text: str) -> List[Tuple[str, int, int]]:
    """Return ``(matched_text, start_col, end_col)`` (1-based, end exclusive)."""
    spans: List[Tuple[str, int, int]] = []
    for m in pattern.finditer(text):
        spans.append((m.group(0), m.start() + 1, m.end() + 1))
    return spans


class VagueWordingRule(Rule):
    """Flag vague adjectives and unmeasurable qualifiers."""

    id = "ambiguous-term"
    name = "ambiguous term"
    severity = Severity.WARNING
    description = "Vague or subjective wording that an agent cannot implement."

    def check(self, doc: SpecDocument) -> Iterable[Diagnostic]:
        for line, raw in self._iter_prose(doc):
            for matched, start, end in _find_spans(_VAGUE_RE, raw):
                key = matched.lower()
                hint = _VAGUE_TERMS.get(key, "")
                yield self._diag(
                    doc,
                    line,
                    message=f"vague term '{matched}'",
                    column=start,
                    end_column=end,
                    suggestion=hint,
                )


class WeakVerbRule(Rule):
    """Flag weak verbs like *handle* / *support* / *gracefully*."""

    id = "weak-verb"
    name = "weak verb"
    severity = Severity.WARNING
    description = "Weak verb that hides the actual required behaviour."

    def check(self, doc: SpecDocument) -> Iterable[Diagnostic]:
        for line, raw in self._iter_prose(doc):
            for matched, start, end in _find_spans(_WEAK_RE, raw):
                key = matched.lower()
                hint = _WEAK_VERBS.get(key, "")
                yield self._diag(
                    doc,
                    line,
                    message=f"weak verb '{matched}'",
                    column=start,
                    end_column=end,
                    suggestion=hint,
                )

"""Rule engine for spec-sentinel.

A rule is a small object with a stable ``id`` and a ``check`` method that
yields :class:`~spec_sentinel.models.Diagnostic` objects for a parsed
document. Rules are pure functions of the document plus their own
configuration, which keeps them easy to test in isolation.
"""

from spec_sentinel.rules.base import Rule
from spec_sentinel.rules.registry import ALL_RULES, get_rules

__all__ = ["Rule", "ALL_RULES", "get_rules"]

"""Registry of all built-in rules and selection helpers."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from spec_sentinel.rules.base import Rule
from spec_sentinel.rules.structure import (
    MissingAcceptanceCriteriaRule,
    MissingAcceptanceSectionRule,
    UnquantifiedNFRRule,
    UntestableRequirementRule,
)
from spec_sentinel.rules.traceability import UntraceableRequirementRule
from spec_sentinel.rules.wording import VagueWordingRule, WeakVerbRule

# Order is the order diagnostics are produced within a line group.
ALL_RULES: List[Rule] = [
    VagueWordingRule(),
    WeakVerbRule(),
    MissingAcceptanceCriteriaRule(),
    UntestableRequirementRule(),
    UnquantifiedNFRRule(),
    MissingAcceptanceSectionRule(),
    UntraceableRequirementRule(),
]

_BY_ID: Dict[str, Rule] = {r.id: r for r in ALL_RULES}


def get_rules(
    select: Optional[Sequence[str]] = None,
    disable: Optional[Sequence[str]] = None,
) -> List[Rule]:
    """Return the active rule set.

    ``select`` keeps only the named rule ids; ``disable`` drops them.
    Unknown ids raise ``KeyError`` so a typo in config fails loudly
    rather than silently running nothing.
    """
    rules = ALL_RULES
    if select:
        for rid in select:
            if rid not in _BY_ID:
                raise KeyError(f"unknown rule id: {rid}")
        rules = [r for r in ALL_RULES if r.id in set(select)]
    if disable:
        for rid in disable:
            if rid not in _BY_ID:
                raise KeyError(f"unknown rule id: {rid}")
        rules = [r for r in rules if r.id not in set(disable)]
    return rules


def rule_ids() -> List[str]:
    return list(_BY_ID.keys())

"""Tests for individual rules."""

from __future__ import annotations

from spec_sentinel import parser
from spec_sentinel.rules import get_rules
from spec_sentinel.rules.registry import rule_ids
from spec_sentinel.rules.structure import (
    MissingAcceptanceCriteriaRule,
    UnquantifiedNFRRule,
    UntestableRequirementRule,
)
from spec_sentinel.rules.traceability import UntraceableRequirementRule
from spec_sentinel.rules.wording import VagueWordingRule, WeakVerbRule


def _diags(rule, text):
    doc = parser.parse_text(text, "spec.md")
    return list(rule.check(doc))


def test_vague_term_flagged_with_span():
    diags = _diags(VagueWordingRule(), "The system must be fast and scalable.\n")
    msgs = [d.message for d in diags]
    assert any("fast" in m for m in msgs)
    assert any("scalable" in m for m in msgs)
    # column points inside the line, not at column 1
    fast = next(d for d in diags if "fast" in d.message)
    assert fast.column > 1
    assert fast.end_column > fast.column
    assert fast.suggestion  # has a remediation hint


def test_weak_verb_flagged():
    diags = _diags(WeakVerbRule(), "The module should handle errors gracefully.\n")
    msgs = " ".join(d.message for d in diags)
    assert "handle" in msgs
    assert "gracefully" in msgs


def test_clean_prose_has_no_wording_diagnostics():
    text = "REQ-1 The service must return HTTP 201 within 200 ms.\n"
    assert _diags(VagueWordingRule(), text) == []
    assert _diags(WeakVerbRule(), text) == []


def test_missing_acceptance_criteria_is_error():
    rule = MissingAcceptanceCriteriaRule()
    text = "## Requirements\nThe service must create an order.\n"
    diags = _diags(rule, text)
    assert len(diags) == 1
    assert diags[0].severity.value == "error"


def test_acceptance_criteria_present_no_diag():
    rule = MissingAcceptanceCriteriaRule()
    text = (
        "## Requirements\n"
        "REQ-1 The service must create an order. "
        "Acceptance: when posted then a row exists.\n"
    )
    assert _diags(rule, text) == []


def test_untestable_requirement_flagged():
    rule = UntestableRequirementRule()
    # no observable verb, no number
    text = "## Requirements\nThe product must be world class.\n"
    diags = _diags(rule, text)
    assert len(diags) == 1


def test_testable_requirement_not_flagged():
    rule = UntestableRequirementRule()
    text = "## Requirements\nThe service must return HTTP 200.\n"
    assert _diags(rule, text) == []


def test_unquantified_nfr_is_error():
    rule = UnquantifiedNFRRule()
    text = "## Requirements\nThe system must have good performance under load.\n"
    diags = _diags(rule, text)
    assert len(diags) == 1
    assert diags[0].severity.value == "error"


def test_quantified_nfr_not_flagged():
    rule = UnquantifiedNFRRule()
    text = "## Requirements\nThe API performance must be under 200 ms at p95.\n"
    assert _diags(rule, text) == []


def test_untraceable_requirement_flagged():
    rule = UntraceableRequirementRule()
    text = "## Requirements\nThe service must return 200.\n"
    diags = _diags(rule, text)
    assert len(diags) == 1
    assert "traceable" in diags[0].message


def test_traceable_requirement_not_flagged():
    rule = UntraceableRequirementRule()
    text = "## Requirements\nREQ-001 The service must return 200.\n"
    assert _diags(rule, text) == []


def test_get_rules_select_and_disable():
    only = get_rules(select=["weak-verb"])
    assert [r.id for r in only] == ["weak-verb"]

    without = get_rules(disable=["weak-verb"])
    assert "weak-verb" not in [r.id for r in without]


def test_get_rules_unknown_id_raises():
    import pytest

    with pytest.raises(KeyError):
        get_rules(select=["does-not-exist"])
    with pytest.raises(KeyError):
        get_rules(disable=["does-not-exist"])


def test_all_rule_ids_unique():
    ids = rule_ids()
    assert len(ids) == len(set(ids))

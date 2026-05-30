"""Tests for the readiness scoring engine."""

from __future__ import annotations

import pytest

from spec_sentinel.engine import lint_file, lint_text
from spec_sentinel.scoring import DEFAULT_WEIGHTS, compute_readiness
from spec_sentinel import parser


def test_good_spec_scores_higher_than_bad(good_spec_path, bad_spec_path):
    good = lint_file(good_spec_path)
    bad = lint_file(bad_spec_path)
    assert good.score.overall > bad.score.overall
    assert good.score.overall >= 70
    assert bad.score.overall < 70


def test_good_spec_passes_default_threshold(good_spec_path):
    report = lint_file(good_spec_path)
    assert report.score.passed is True
    assert report.error_count == 0


def test_bad_spec_fails_and_has_errors(bad_spec_path):
    report = lint_file(bad_spec_path)
    assert report.score.passed is False
    assert report.error_count > 0


def test_dimensions_in_range(good_spec_path):
    s = lint_file(good_spec_path).score
    for dim in s.dimensions():
        assert 0 <= dim.score <= 100
    assert 0 <= s.overall <= 100


# A spec that is mostly fine but not perfect: the requirement has no
# traceable id and uses a vague term, so the dimensions diverge and the
# overall score sits between the threshold extremes.
_MIXED_SPEC = (
    "## Requirements\n"
    "The service must be fast and must return 200. "
    "Acceptance: returns 200.\n"
)


def test_threshold_controls_pass_fail():
    report_low = lint_text(_MIXED_SPEC, threshold=10)
    report_high = lint_text(_MIXED_SPEC, threshold=99)
    assert report_low.score.passed is True
    assert report_high.score.passed is False


def test_weights_renormalised_when_partial():
    doc = parser.parse_text(_MIXED_SPEC)
    from spec_sentinel.engine import lint_document

    report = lint_document(doc)
    diagnostics = report.diagnostics
    s_default = compute_readiness(doc, diagnostics)
    # only clarity matters -> overall equals clarity score
    s_clarity = compute_readiness(
        doc,
        diagnostics,
        weights={"coverage": 0, "clarity": 1, "testability": 0, "traceability": 0},
    )
    assert s_clarity.overall == pytest.approx(s_clarity.clarity.score, abs=0.05)
    # the mixed spec's dimensions differ, so reweighting changes the total
    assert s_default.overall != s_clarity.overall


def test_zero_weight_sum_raises():
    doc = parser.parse_text("nothing here\n")
    with pytest.raises(ValueError):
        compute_readiness(doc, [], weights={k: 0 for k in DEFAULT_WEIGHTS})


def test_coverage_zero_when_no_requirements():
    doc = parser.parse_text("# Just a title\n\nSome narrative prose.\n")
    s = compute_readiness(doc, [])
    assert s.coverage.score == 0.0
    assert s.testability.score == 0.0


def test_full_quality_spec_scores_100():
    text = (
        "## Requirements\n"
        "REQ-1 The service must return HTTP 201 within 200 ms. "
        "Acceptance: when posted then status is 201.\n"
    )
    report = lint_text(text)
    # one clean, testable, traceable, accepted requirement
    assert report.score.coverage.score == 100.0
    assert report.score.testability.score == 100.0
    assert report.score.traceability.score == 100.0
    assert report.score.clarity.score == 100.0
    assert report.score.overall == 100.0

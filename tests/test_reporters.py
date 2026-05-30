"""Tests for the text / JSON / SARIF reporters."""

from __future__ import annotations

import json

from spec_sentinel.engine import lint_file
from spec_sentinel.reporters import (
    render_human,
    render_json,
    render_sarif,
    render_summary,
)


def test_human_report_contains_score_and_locations(bad_spec_path):
    report = lint_file(bad_spec_path)
    out = render_human(report)
    assert "readiness" in out
    assert "FAIL" in out
    # a line:column location appears
    assert any(":" in tok for tok in out.split())


def test_human_report_clean_spec_says_no_issues():
    from spec_sentinel.engine import lint_text

    text = (
        "## Requirements\n"
        "REQ-1 The service must return HTTP 201 within 200 ms. "
        "Acceptance: when posted then status is 201.\n"
    )
    out = render_human(lint_text(text))
    assert "no issues found" in out
    assert "PASS" in out


def test_json_report_is_valid_and_structured(bad_spec_path):
    report = lint_file(bad_spec_path)
    payload = json.loads(render_json([report]))
    assert payload["tool"] == "spec-sentinel"
    assert len(payload["files"]) == 1
    f = payload["files"][0]
    assert "diagnostics" in f
    assert f["score"]["passed"] is False
    assert set(f["score"]["dimensions"]) == {
        "coverage",
        "clarity",
        "testability",
        "traceability",
    }
    # every diagnostic has a line and rule id
    for d in f["diagnostics"]:
        assert d["line"] >= 1
        assert d["ruleId"]


def test_sarif_report_is_valid_2_1_0(bad_spec_path):
    report = lint_file(bad_spec_path)
    sarif = json.loads(render_sarif([report]))
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "spec-sentinel"
    assert run["tool"]["driver"]["rules"]  # rule metadata present
    assert run["results"]  # bad spec yields results
    res = run["results"][0]
    assert res["level"] in {"error", "warning", "note"}
    loc = res["locations"][0]["physicalLocation"]
    assert loc["region"]["startLine"] >= 1


def test_summary_lists_each_file(good_spec_path, bad_spec_path):
    reports = [lint_file(good_spec_path), lint_file(bad_spec_path)]
    out = render_summary(reports)
    assert "2 file(s)" in out
    assert "PASS" in out and "FAIL" in out

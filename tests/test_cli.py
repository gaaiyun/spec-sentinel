"""End-to-end CLI tests via Typer's runner."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from spec_sentinel.cli import app

runner = CliRunner()


def test_help_runs():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "lint" in result.stdout


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "spec-sentinel" in result.stdout


def test_rules_command_lists_rules():
    result = runner.invoke(app, ["rules"])
    assert result.exit_code == 0
    assert "ambiguous-term" in result.stdout
    assert "missing-acceptance-criteria" in result.stdout


def test_lint_good_spec_exits_zero(good_spec_path):
    result = runner.invoke(app, ["lint", good_spec_path])
    assert result.exit_code == 0
    assert "PASS" in result.stdout


def test_lint_bad_spec_exits_one(bad_spec_path):
    result = runner.invoke(app, ["lint", bad_spec_path])
    assert result.exit_code == 1
    assert "FAIL" in result.stdout
    assert "ambiguous-term" in result.stdout or "weak-verb" in result.stdout


def test_lint_json_format(bad_spec_path):
    result = runner.invoke(app, ["lint", "--format", "json", bad_spec_path])
    # exit 1 because it fails, but stdout must still be valid JSON
    payload = json.loads(result.stdout)
    assert payload["tool"] == "spec-sentinel"
    assert payload["files"][0]["score"]["passed"] is False


def test_lint_sarif_format(bad_spec_path):
    result = runner.invoke(app, ["lint", "--format", "sarif", bad_spec_path])
    sarif = json.loads(result.stdout)
    assert sarif["version"] == "2.1.0"


def test_lint_threshold_can_pass_bad_spec(bad_spec_path):
    # drop threshold to 0 -> still fails because of error-level diagnostics
    result = runner.invoke(app, ["lint", "--threshold", "0", bad_spec_path])
    assert result.exit_code == 1


def test_lint_disable_rule(bad_spec_path):
    result = runner.invoke(
        app, ["lint", "--disable", "ambiguous-term", bad_spec_path]
    )
    assert "ambiguous-term" not in result.stdout


def test_lint_select_only_weak_verb(good_spec_path):
    result = runner.invoke(
        app, ["lint", "--select", "weak-verb", good_spec_path]
    )
    # good spec has no weak verbs and selecting one rule cannot raise errors
    assert result.exit_code == 0


def test_lint_unknown_rule_exits_two(good_spec_path):
    result = runner.invoke(app, ["lint", "--select", "nope", good_spec_path])
    assert result.exit_code == 2


def test_lint_directory_scans_samples(samples_dir):
    result = runner.invoke(app, ["lint", str(samples_dir)])
    # directory has good + bad + yaml -> multi-file summary, fails overall
    assert result.exit_code == 1
    assert "file(s):" in result.stdout


def test_lint_yaml_spec(yaml_spec_path):
    result = runner.invoke(app, ["lint", yaml_spec_path])
    assert "readiness" in result.stdout


def test_no_suggestions_hides_hints(bad_spec_path):
    result = runner.invoke(app, ["lint", "--no-suggestions", bad_spec_path])
    assert "hint:" not in result.stdout


def test_main_entrypoint_returns_exit_codes(good_spec_path, bad_spec_path):
    # The console-script entry point runs Typer with standalone_mode=False
    # and must forward exit codes itself (CliRunner uses standalone_mode,
    # so this path needs its own coverage).
    from spec_sentinel.cli import main

    assert main(["lint", good_spec_path]) == 0
    assert main(["lint", bad_spec_path]) == 1
    assert main(["lint", "does-not-exist.md"]) == 2
    assert main(["version"]) == 0

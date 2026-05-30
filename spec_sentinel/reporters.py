"""Render lint reports as human text, JSON, or SARIF.

The human format is meant for a terminal and a quick read; JSON and
SARIF are for CI ingestion (SARIF uploads to GitHub code scanning, JSON
for anything custom). All three derive from the same
:class:`~spec_sentinel.models.LintReport` so they never disagree.
"""

from __future__ import annotations

import json
from typing import Dict, List

from spec_sentinel import __version__
from spec_sentinel.models import Diagnostic, LintReport, Severity

# Severity glyphs kept ASCII-only on purpose (no emoji, CI-log friendly).
_SEVERITY_TAG = {
    Severity.ERROR: "error",
    Severity.WARNING: "warn ",
    Severity.INFO: "info ",
}


def render_human(report: LintReport, show_suggestions: bool = True) -> str:
    """Return a human-readable report for a single file."""
    lines: List[str] = []
    lines.append(f"{report.path}")

    if not report.diagnostics:
        lines.append("  no issues found")
    else:
        for d in report.diagnostics:
            tag = _SEVERITY_TAG[d.severity]
            loc = f"{d.line}:{d.column}".rjust(7)
            lines.append(f"  {loc}  {tag}  [{d.rule_id}] {d.message}")
            if d.snippet:
                lines.append(f"           > {d.snippet}")
            if show_suggestions and d.suggestion:
                lines.append(f"           hint: {d.suggestion}")

    s = report.score
    lines.append("")
    lines.append(
        f"  readiness {s.overall:.0f}/100  "
        f"(coverage {s.coverage.score:.0f}, clarity {s.clarity.score:.0f}, "
        f"testability {s.testability.score:.0f}, "
        f"traceability {s.traceability.score:.0f})"
    )
    for dim in s.dimensions():
        lines.append(f"    - {dim.name:<12} {dim.score:5.1f}  {dim.detail}")
    verdict = "PASS" if s.passed else "FAIL"
    lines.append(
        f"  threshold {s.threshold:.0f}  ->  {verdict}  "
        f"({report.error_count} error(s), {report.warning_count} warning(s))"
    )
    return "\n".join(lines)


def render_summary(reports: List[LintReport]) -> str:
    """One-line-per-file summary plus totals, for multi-file runs."""
    out: List[str] = []
    total_err = 0
    total_warn = 0
    failed = 0
    for r in reports:
        verdict = "PASS" if r.score.passed else "FAIL"
        if not r.score.passed:
            failed += 1
        total_err += r.error_count
        total_warn += r.warning_count
        out.append(
            f"{verdict}  {r.score.overall:5.1f}  "
            f"{r.error_count}E {r.warning_count}W  {r.path}"
        )
    out.append("")
    out.append(
        f"{len(reports)} file(s): {failed} failed, "
        f"{total_err} error(s), {total_warn} warning(s)"
    )
    return "\n".join(out)


def _diag_to_dict(d: Diagnostic) -> Dict:
    return {
        "ruleId": d.rule_id,
        "severity": d.severity.value,
        "message": d.message,
        "line": d.line,
        "column": d.column,
        "endColumn": d.end_column,
        "snippet": d.snippet,
        "suggestion": d.suggestion,
    }


def _report_to_dict(report: LintReport) -> Dict:
    s = report.score
    return {
        "path": report.path,
        "requirementCount": report.requirement_count,
        "diagnostics": [_diag_to_dict(d) for d in report.diagnostics],
        "score": {
            "overall": s.overall,
            "threshold": s.threshold,
            "passed": s.passed,
            "dimensions": {
                dim.name: {"score": dim.score, "detail": dim.detail}
                for dim in s.dimensions()
            },
        },
        "errorCount": report.error_count,
        "warningCount": report.warning_count,
    }


def render_json(reports: List[LintReport]) -> str:
    """Serialise one or more reports to JSON."""
    payload = {
        "tool": "spec-sentinel",
        "version": __version__,
        "files": [_report_to_dict(r) for r in reports],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def render_sarif(reports: List[LintReport]) -> str:
    """Serialise reports to SARIF 2.1.0 for GitHub code scanning."""
    # Collect the rules actually referenced, with metadata.
    from spec_sentinel.rules import ALL_RULES

    rule_meta = {
        r.id: {
            "id": r.id,
            "name": r.name,
            "shortDescription": {"text": r.description or r.name},
            "defaultConfiguration": {"level": r.severity.sarif_level},
        }
        for r in ALL_RULES
    }

    results = []
    for report in reports:
        for d in report.diagnostics:
            region = {"startLine": d.line, "startColumn": d.column}
            if d.end_column:
                region["endColumn"] = d.end_column
            results.append(
                {
                    "ruleId": d.rule_id,
                    "level": d.severity.sarif_level,
                    "message": {
                        "text": d.message
                        + (f" ({d.suggestion})" if d.suggestion else "")
                    },
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": report.path},
                                "region": region,
                            }
                        }
                    ],
                }
            )

    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "spec-sentinel",
                        "version": __version__,
                        "informationUri": "https://github.com/gaaiyun/spec-sentinel",
                        "rules": list(rule_meta.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2, ensure_ascii=False)

# spec-sentinel

Lint your spec before you hand it to a coding agent. spec-sentinel is an
agent-agnostic CLI that statically checks Markdown/YAML specs for ambiguity,
missing acceptance criteria, untestable requirements and weak traceability,
then gives you a 0-100 readiness score you can gate a commit or CI build on.

Think of it as ESLint or Vale, but for specs and PRDs. It runs offline with
no model calls; the checks are deterministic regex/structure rules.

## Why

Tools like Spec Kit, Cursor and Kiro turn a written spec into code. The output
is only as good as the spec: "the API should be fast", "handle errors
gracefully", "support various formats, etc." give an agent nothing concrete to
build or test against, and the gaps surface as rework later. spec-sentinel
catches that language up front, with a line number and a concrete suggestion,
and fails the build when a spec is not ready.

## Install

```
pip install -e .
```

Requires Python 3.9+. Runtime dependencies are Typer, Pydantic and PyYAML. For
the tests, `pip install -e ".[dev]"`.

## 30-second start

The package ships with sample specs, so you can see it work without writing
anything:

```
# a deliberately bad spec -> exits 1
spec-sentinel lint spec_sentinel/samples/bad_spec.md

# a clean spec -> exits 0
spec-sentinel lint spec_sentinel/samples/good_spec.md

# list the rules
spec-sentinel rules
```

If the console script is not on your PATH, `python -m spec_sentinel ...` is
equivalent.

## What it reports

Running it on the bundled bad spec:

```
$ spec-sentinel lint spec_sentinel/samples/bad_spec.md
spec_sentinel/samples/bad_spec.md
      5:1  error  [missing-acceptance-criteria] requirement has no acceptance criteria
           > The checkout service should make the purchase flow fast and user-friendly.
           hint: add Given/When/Then, an 'Acceptance:' line, or a 'verified by' clause so the behaviour is checkable
      5:1  warn   [missing-requirement-id] requirement has no traceable identifier
           > The checkout service should make the purchase flow fast and user-friendly.
           hint: prefix with an id like 'REQ-001' / 'FR-12' so it can be traced into tests and commits
     5:52  warn   [ambiguous-term] vague term 'fast'
           > The checkout service should make the purchase flow fast and user-friendly.
           hint: state a latency target, e.g. 'responds within 200 ms'
     5:61  warn   [ambiguous-term] vague term 'user-friendly'
           > The checkout service should make the purchase flow fast and user-friendly.
           hint: describe the observable behaviour instead
     ... (more diagnostics) ...

  readiness 2/100  (coverage 0, clarity 0, testability 10, traceability 0)
    - coverage       0.0  0/10 requirements have acceptance criteria
    - clarity        0.0  20 vague/weak wording issue(s) across 14 prose line(s)
    - testability   10.0  1/10 requirements are testable/quantified
    - traceability   0.0  0/10 requirements have a traceable id
  threshold 70  ->  FAIL  (11 error(s), 39 warning(s))
```

And on the clean spec:

```
$ spec-sentinel lint spec_sentinel/samples/good_spec.md
spec_sentinel/samples/good_spec.md
  no issues found

  readiness 100/100  (coverage 100, clarity 100, testability 100, traceability 100)
    - coverage     100.0  5/5 requirements have acceptance criteria
    - clarity      100.0  0 vague/weak wording issue(s) across 28 prose line(s)
    - testability  100.0  5/5 requirements are testable/quantified
    - traceability 100.0  5/5 requirements have a traceable id
  threshold 70  ->  PASS  (0 error(s), 0 warning(s))
```

## The readiness score

The score blends four dimensions, each on a 0-100 scale, into one weighted
number (default weights in parentheses):

- **coverage** (0.30) - share of requirements that have acceptance criteria
- **clarity** (0.25) - freedom from vague terms and weak verbs, by density
- **testability** (0.25) - share of requirements with an observable, testable
  outcome (or a quantified target for non-functional requirements)
- **traceability** (0.20) - share of requirements carrying a stable id

`lint` exits non-zero when a file scores below `--threshold` (default 70) or
has any error-level diagnostic, which is what makes it usable as a gate.

## Rules

| id | severity | what it flags |
|----|----------|---------------|
| `ambiguous-term` | warning | vague/subjective words: fast, scalable, user-friendly, robust, etc. |
| `weak-verb` | warning | weak verbs that hide behaviour: handle, support, manage, gracefully |
| `missing-acceptance-criteria` | error | a normative requirement with no acceptance criteria nearby |
| `untestable-requirement` | warning | a requirement with no observable outcome to assert on |
| `unquantified-nfr` | error | a non-functional requirement stated without a number |
| `no-acceptance-section` | info | the spec defines requirements but has no acceptance section |
| `missing-requirement-id` | warning | a requirement without a stable identifier (e.g. REQ-001) |

Select or disable rules per run:

```
spec-sentinel lint spec.md --select ambiguous-term --select weak-verb
spec-sentinel lint spec.md --disable no-acceptance-section
```

## Output formats

```
spec-sentinel lint spec.md --format text     # default, human-readable
spec-sentinel lint spec.md --format json      # machine-readable
spec-sentinel lint spec.md --format sarif     # SARIF 2.1.0 for GitHub code scanning
```

## Use in CI / pre-commit

Because a failing spec exits non-zero, it drops straight into a pre-commit
hook:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: spec-sentinel
      name: spec-sentinel
      entry: spec-sentinel lint
      language: system
      files: '\.(md|markdown|ya?ml)$'
```

Or as a CI step that uploads SARIF to GitHub code scanning:

```
spec-sentinel lint docs/specs/ --format sarif > spec-sentinel.sarif
```

## What it parses

- **Markdown** - headings, list items and normative statements (lines with
  must/shall/should and bullets under a Requirements heading). Multi-line
  bullets are folded into one requirement; fenced code blocks are skipped.
- **YAML** - requirement objects (a mapping with a `description`/`text` field).
  Sibling `id` and `acceptance` keys are linked to the same requirement, so a
  `{id, description, acceptance}` block counts as one requirement, not three.

## Roadmap

The current release focuses on doing the linter and readiness score well. Not
yet implemented:

- **Traceability matrix** - cross-reference requirement ids against test ids
  and code, and report orphans on both sides.
- **Drift detection** - diff a spec against a previous revision (or against the
  code/tests it maps to) and flag requirements that changed without their
  acceptance criteria or tests being updated.
- **Config file** - per-project `spec-sentinel.toml` for thresholds, custom
  vague-term dictionaries and per-rule severities.
- **Optional LLM-assisted ambiguity check** - an opt-in pass that augments the
  rule engine for ambiguity the regexes miss; the default stays fully offline.

## Development

```
pip install -e ".[dev]"
python -m pytest
```

## License

MIT

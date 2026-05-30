"""Turn a spec file into a :class:`SpecDocument`.

The parser is deliberately simple and line-oriented. It does **not** try
to build a full Markdown AST; it just needs enough structure for the
rules and the readiness score:

* headings (to know which sections exist)
* requirement statements (modal verbs / list items under a requirements
  heading)
* whether requirements carry an identifier and acceptance criteria

YAML specs are flattened into pseudo-lines so the same rule engine can
run over them. Each scalar string value becomes a "requirement-ish" line
keyed by its dotted path, which keeps line numbers meaningful for
diagnostics.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

import yaml

from spec_sentinel.models import Requirement, Section, SpecDocument

# Modal verbs that mark a normative requirement (RFC 2119 flavour).
_MODAL_RE = re.compile(
    r"\b(must|must not|shall|shall not|should|should not|will|"
    r"is required to|needs to|has to)\b",
    re.IGNORECASE,
)

# Heading like "## 3.1 Foo" or "## Foo"
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")

# List item: "- ", "* ", "1. " etc.
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")

# An explicit requirement identifier such as REQ-001, FR-12, US-3, NFR-2.
_IDENTIFIER_RE = re.compile(r"\b([A-Z]{2,5}-\d{1,4})\b")

# Headings that indicate acceptance criteria / traceability presence.
_ACCEPTANCE_HEADING_RE = re.compile(
    r"acceptance\s+criteri|given/when/then|gherkin|definition\s+of\s+done",
    re.IGNORECASE,
)
_TRACE_HEADING_RE = re.compile(
    r"traceab|trace\s+matri|requirement\s+id|maps?\s+to", re.IGNORECASE
)

# Inline acceptance-criteria markers used on or near a requirement line.
# Covers Gherkin-style clauses (given/when/then in any pairing) and the
# common "Acceptance:" / "verified by" / "measured by" phrasings.
_ACCEPTANCE_INLINE_RE = re.compile(
    r"(given\b.*\b(when|then)\b|when\b.*\bthen\b|acceptance\s*:|"
    r"verified\s+by|measured\s+by|definition\s+of\s+done)",
    re.IGNORECASE,
)

# A quantified value: number with optional unit/percentage, or a comparison.
_QUANTIFIED_RE = re.compile(
    r"(\b\d+(\.\d+)?\s?(ms|s|sec|seconds?|minutes?|m|h|hours?|days?|%|"
    r"percent|rps|qps|req/s|requests?|users?|kb|mb|gb|tb)\b|"
    r"(<=|>=|<|>|≤|≥)\s?\d|\bp\d{2,3}\b|\bwithin\s+\d)",
    re.IGNORECASE,
)


def _looks_like_requirement(text: str, under_req_section: bool) -> bool:
    """Decide whether a line is a normative requirement statement."""
    if _MODAL_RE.search(text):
        return True
    # List items directly under a "Requirements" heading count even
    # without a modal, since specs often bullet them tersely.
    if under_req_section and _LIST_ITEM_RE.match(text):
        return True
    return False


def parse_text(text: str, path: str = "<string>") -> SpecDocument:
    """Parse raw Markdown text into a :class:`SpecDocument`."""
    raw_lines = text.splitlines()
    doc = SpecDocument(path=path, lines=raw_lines)

    under_req_section = False
    in_code_fence = False

    # First pass: group physical lines into logical blocks. A block is a
    # bullet/paragraph plus any indented continuation lines that follow
    # it, so a requirement spread over several wrapped lines is treated
    # as one statement (and its trailing acceptance text is folded in).
    n = len(raw_lines)
    idx = 0
    while idx < n:
        raw = raw_lines[idx]
        line_no = idx + 1
        stripped = raw.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_fence = not in_code_fence
            idx += 1
            continue
        if in_code_fence:
            idx += 1
            continue

        heading = _HEADING_RE.match(raw)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2)
            doc.sections.append(Section(title=title, level=level, line=line_no))
            under_req_section = bool(
                re.search(r"requirement|functional|user stor|feature", title, re.I)
            )
            if _ACCEPTANCE_HEADING_RE.search(title):
                doc.has_acceptance_section = True
            if _TRACE_HEADING_RE.search(title):
                doc.has_traceability = True
            idx += 1
            continue

        if not stripped:
            idx += 1
            continue

        # Gather continuation lines: indented, non-blank, not a new list
        # item or heading. These belong to the current block.
        block_lines = [stripped]
        look = idx + 1
        while look < n:
            nxt = raw_lines[look]
            if not nxt.strip():
                break
            if _HEADING_RE.match(nxt) or _LIST_ITEM_RE.match(nxt):
                break
            if nxt[:1] not in (" ", "\t"):
                break
            block_lines.append(nxt.strip())
            look += 1
        block_text = " ".join(block_lines)

        if _looks_like_requirement(block_text, under_req_section):
            ident_match = _IDENTIFIER_RE.search(block_text)
            doc.requirements.append(
                Requirement(
                    line=line_no,
                    text=block_text,
                    identifier=ident_match.group(1) if ident_match else None,
                    has_acceptance_criteria=bool(
                        _ACCEPTANCE_INLINE_RE.search(block_text)
                    ),
                    is_quantified=bool(_QUANTIFIED_RE.search(block_text)),
                )
            )

        idx = look

    _attach_nearby_acceptance(doc)
    return doc


def _attach_nearby_acceptance(doc: SpecDocument) -> None:
    """Mark requirements whose following lines supply acceptance criteria.

    A requirement often states the rule on one line and lists the
    acceptance criteria on the next indented bullets. We scan up to a few
    lines after each requirement (until the next requirement or blank
    gap) for acceptance markers or quantified values.
    """
    req_lines = {r.line for r in doc.requirements}
    for req in doc.requirements:
        if req.has_acceptance_criteria:
            continue
        for offset in range(1, 5):
            probe = req.line + offset
            if probe in req_lines:
                break
            text = doc.line_text(probe).strip()
            if not text:
                # one blank line is tolerated, two ends the block
                if doc.line_text(probe + 1).strip() == "":
                    break
                continue
            if _ACCEPTANCE_INLINE_RE.search(text) or _ACCEPTANCE_HEADING_RE.search(
                text
            ):
                req.has_acceptance_criteria = True
            if _QUANTIFIED_RE.search(text):
                req.is_quantified = True


# YAML keys that hold the requirement's main statement.
_REQ_TEXT_KEYS = ("description", "text", "requirement", "story", "behaviour", "behavior")
# Keys that hold an identifier.
_REQ_ID_KEYS = ("id", "key", "ref")
# Keys that hold acceptance criteria.
_REQ_AC_KEYS = ("acceptance", "acceptance_criteria", "criteria", "verify", "verified_by")


def _flatten_yaml(node, prefix: str, out: List[Tuple[str, str]]) -> None:
    """Flatten a YAML structure into ``(dotted_path, scalar_text)`` pairs."""
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            _flatten_yaml(value, child, out)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            child = f"{prefix}[{i}]"
            _flatten_yaml(value, child, out)
    else:
        out.append((prefix, "" if node is None else str(node)))


def _coerce_text(value) -> str:
    """Render a YAML value to a single line of text for matching."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(_coerce_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(_coerce_text(v) for v in value.values())
    return str(value)


def _first_key(mapping: dict, keys) -> object:
    """Return the value of the first matching key (case-insensitive)."""
    lower = {str(k).lower(): k for k in mapping}
    for want in keys:
        if want in lower:
            return mapping[lower[want]]
    return None


def _collect_yaml_requirements(node, line_of, reqs: List[Requirement]) -> None:
    """Walk the YAML structure and build one Requirement per requirement object.

    A *requirement object* is a dict carrying one of the text keys
    (``description``/``text``/...). Its id and acceptance criteria are
    read from sibling keys, so ``{id, description, acceptance}`` becomes a
    single requirement rather than three. ``line_of`` maps a dotted path
    to its line in the rendered view.
    """
    if isinstance(node, dict):
        text_key = _first_key(node, _REQ_TEXT_KEYS)
        if text_key is not None and _coerce_text(text_key).strip():
            stmt = _coerce_text(text_key)
            ident_val = _coerce_text(_first_key(node, _REQ_ID_KEYS))
            ac_val = _coerce_text(_first_key(node, _REQ_AC_KEYS))
            ident_match = _IDENTIFIER_RE.search(ident_val) or _IDENTIFIER_RE.search(
                stmt
            )
            combined = f"{stmt} {ac_val}".strip()
            reqs.append(
                Requirement(
                    line=line_of(node),
                    text=stmt,
                    identifier=ident_match.group(1) if ident_match else None,
                    has_acceptance_criteria=bool(ac_val.strip())
                    or bool(_ACCEPTANCE_INLINE_RE.search(stmt)),
                    is_quantified=bool(_QUANTIFIED_RE.search(combined)),
                )
            )
            return  # do not descend further into a requirement object
        for value in node.values():
            _collect_yaml_requirements(value, line_of, reqs)
    elif isinstance(node, list):
        for value in node:
            _collect_yaml_requirements(value, line_of, reqs)


def parse_yaml(text: str, path: str = "<string>") -> SpecDocument:
    """Parse a YAML spec into a :class:`SpecDocument`.

    YAML has no inherent line semantics once loaded, so we render a
    deterministic ``key: value`` view and use *that* for line numbers and
    for the wording rules (which scan prose). Requirements, however, are
    extracted structurally: each requirement object (a mapping with a
    ``description``/``text`` field) becomes one requirement, with its id
    and acceptance criteria pulled from sibling keys. This keeps the
    readiness score faithful to the document's real structure instead of
    counting every scalar as a separate requirement.
    """
    data = yaml.safe_load(text)
    pairs: List[Tuple[str, str]] = []
    _flatten_yaml(data, "", pairs)

    rendered_lines = [f"{key}: {value}" for key, value in pairs]
    rendered = "\n".join(rendered_lines)

    # Build the base document from the rendered view, but discard its
    # heuristic requirement detection (the flattened keys are not lines of
    # prose). We keep the raw lines so reporters can show snippets.
    doc = SpecDocument(path=path, lines=rendered.splitlines())

    # Map the first line index where each requirement object's text key
    # appears, so diagnostics point at the description line.
    def line_for_path_substring(text_value: str) -> int:
        snippet = _coerce_text(text_value).strip().split("\n")[0][:30]
        for i, line in enumerate(rendered_lines, start=1):
            if snippet and snippet in line:
                return i
        return 1

    # Detect acceptance / traceability presence from keys.
    for key, _ in pairs:
        key_l = key.lower()
        if any(a in key_l for a in ("acceptance", "criteria", "verify", "verified")):
            doc.has_acceptance_section = True
        if _TRACE_HEADING_RE.search(key_l) or key_l.split(".")[-1] in _REQ_ID_KEYS:
            doc.has_traceability = True

    # Structural requirement extraction.
    reqs: List[Requirement] = []

    def line_of(obj: dict) -> int:
        text_val = _coerce_text(_first_key(obj, _REQ_TEXT_KEYS))
        return line_for_path_substring(text_val)

    _collect_yaml_requirements(data, line_of, reqs)
    reqs.sort(key=lambda r: r.line)
    doc.requirements = reqs
    return doc


def parse_file(path: str) -> SpecDocument:
    """Parse a spec file, dispatching on extension."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        return parse_yaml(text, path=str(p))
    return parse_text(text, path=str(p))

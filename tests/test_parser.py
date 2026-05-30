"""Tests for the spec parser."""

from __future__ import annotations

from spec_sentinel import parser


def test_parses_headings_and_requirements():
    text = (
        "# Title\n"
        "## Requirements\n"
        "- REQ-001 The system must return 200 on success.\n"
        "- The UI should be fast.\n"
    )
    doc = parser.parse_text(text, "spec.md")
    titles = [s.title for s in doc.sections]
    assert "Title" in titles
    assert "Requirements" in titles
    # Both bullet lines are normative (modal verbs) -> 2 requirements.
    assert len(doc.requirements) == 2
    assert doc.requirements[0].identifier == "REQ-001"
    assert doc.requirements[1].identifier is None


def test_requirement_line_numbers_are_1_based():
    text = "# T\n\n## Requirements\n\nThe system must log every request.\n"
    doc = parser.parse_text(text, "spec.md")
    assert len(doc.requirements) == 1
    assert doc.requirements[0].line == 5
    assert doc.line_text(5).startswith("The system must log")


def test_code_fences_are_not_parsed_as_requirements():
    text = (
        "## Requirements\n"
        "```\n"
        "the system must do magic\n"  # inside a fence -> ignored
        "```\n"
        "The system must return JSON.\n"
    )
    doc = parser.parse_text(text, "spec.md")
    assert len(doc.requirements) == 1
    assert "JSON" in doc.requirements[0].text


def test_detects_inline_acceptance_criteria():
    text = (
        "## Requirements\n"
        "REQ-1 The service must return 201. "
        "Acceptance: given a valid body, then status is 201.\n"
    )
    doc = parser.parse_text(text, "spec.md")
    assert doc.requirements[0].has_acceptance_criteria is True


def test_attaches_acceptance_on_following_line():
    text = (
        "## Requirements\n"
        "- REQ-1 The service must create an order.\n"
        "  Acceptance: when posted, then a row is persisted.\n"
    )
    doc = parser.parse_text(text, "spec.md")
    assert doc.requirements[0].has_acceptance_criteria is True


def test_detects_quantified_nfr():
    text = "## Requirements\nThe API must respond within 200 ms.\n"
    doc = parser.parse_text(text, "spec.md")
    assert doc.requirements[0].is_quantified is True


def test_acceptance_and_traceability_sections_detected():
    text = (
        "# Spec\n"
        "## Acceptance Criteria\n"
        "stuff\n"
        "## Traceability Matrix\n"
        "more\n"
    )
    doc = parser.parse_text(text, "spec.md")
    assert doc.has_acceptance_section is True
    assert doc.has_traceability is True


def test_yaml_spec_is_structure_aware(yaml_spec_path):
    doc = parser.parse_file(yaml_spec_path)
    # Exactly one requirement per requirement object (3 functional + 1 NFR),
    # NOT one per scalar key.
    assert len(doc.requirements) == 4
    ids = [r.identifier for r in doc.requirements if r.identifier]
    assert "REQ-101" in ids
    assert "REQ-102" in ids
    assert doc.has_acceptance_section is True
    assert doc.has_traceability is True


def test_yaml_links_id_and_acceptance_to_same_requirement():
    text = (
        "requirements:\n"
        "  - id: REQ-1\n"
        "    description: The service must return 200.\n"
        "    acceptance: when called then status is 200.\n"
    )
    doc = parser.parse_yaml(text, "spec.yaml")
    assert len(doc.requirements) == 1
    req = doc.requirements[0]
    assert req.identifier == "REQ-1"
    assert req.has_acceptance_criteria is True


def test_yaml_requirement_without_id_or_acceptance_flagged():
    text = (
        "requirements:\n"
        "  - description: The flow should be fast and handle things.\n"
    )
    doc = parser.parse_yaml(text, "spec.yaml")
    assert len(doc.requirements) == 1
    req = doc.requirements[0]
    assert req.identifier is None
    assert req.has_acceptance_criteria is False


def test_parse_file_dispatches_on_extension(good_spec_path, yaml_spec_path):
    md = parser.parse_file(good_spec_path)
    yml = parser.parse_file(yaml_spec_path)
    assert md.path.endswith(".md")
    assert yml.path.endswith(".yaml")
    assert md.requirements and yml.requirements

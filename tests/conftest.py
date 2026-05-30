"""Shared test fixtures and path helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "spec_sentinel" / "samples"


@pytest.fixture()
def samples_dir() -> Path:
    return SAMPLES_DIR


@pytest.fixture()
def bad_spec_path() -> str:
    return str(SAMPLES_DIR / "bad_spec.md")


@pytest.fixture()
def good_spec_path() -> str:
    return str(SAMPLES_DIR / "good_spec.md")


@pytest.fixture()
def yaml_spec_path() -> str:
    return str(SAMPLES_DIR / "spec.yaml")

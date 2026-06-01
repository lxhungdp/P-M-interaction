"""Pytest fixtures for 01-PM."""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GOLDEN_DIR = ROOT / "tests" / "golden"


@pytest.fixture
def golden_dir() -> pathlib.Path:
    return GOLDEN_DIR

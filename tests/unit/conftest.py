"""Shared pytest fixtures and path constants for unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

SPDX_FIXTURES = Path("tests/fixtures/spdx")
CDX_FIXTURES = Path("tests/fixtures/cyclonedx")


@pytest.fixture
def runner() -> CliRunner:
    """Return a Click CliRunner for invoking the CLI in tests."""
    return CliRunner()

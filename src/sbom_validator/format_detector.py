"""Detect SBOM format from raw JSON content."""

from __future__ import annotations

import json
from pathlib import Path

from sbom_validator.exceptions import ParseError, UnsupportedFormatError


def detect_format(file_path: Path) -> str:
    """Return 'spdx' or 'cyclonedx' based on file content.

    Raises:
        ParseError: If the file cannot be read or is not valid JSON.
        UnsupportedFormatError: If the format cannot be determined.
    """
    # TODO: implement in Phase 2
    raise NotImplementedError

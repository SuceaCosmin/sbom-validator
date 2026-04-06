"""Parser for SPDX 2.3 JSON SBOM files."""

from __future__ import annotations

from pathlib import Path

from sbom_validator.models import NormalizedSBOM


def parse_spdx(file_path: Path) -> NormalizedSBOM:
    """Parse an SPDX 2.3 JSON file into a NormalizedSBOM.

    Raises:
        ParseError: If the file cannot be read or parsed.
    """
    # TODO: implement in Phase 2
    raise NotImplementedError

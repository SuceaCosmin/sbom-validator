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
    if not file_path.exists():
        raise ParseError(f"File not found: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParseError(f"Cannot read file: {file_path}") from exc

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON in file: {file_path}") from exc

    if not isinstance(data, dict):
        raise UnsupportedFormatError(
            f"Expected a JSON object at the root of {file_path}, " f"got {type(data).__name__}"
        )

    if "spdxVersion" in data:
        if data["spdxVersion"] != "SPDX-2.3":
            raise UnsupportedFormatError(
                f"Unsupported SPDX version: {data['spdxVersion']!r}. Only SPDX-2.3 is supported."
            )
        return "spdx"

    if data.get("bomFormat") == "CycloneDX":
        spec = data.get("specVersion")
        if spec != "1.6":
            raise UnsupportedFormatError(
                f"Unsupported CycloneDX version: {spec!r}. Only 1.6 is supported."
            )
        return "cyclonedx"

    raise UnsupportedFormatError(
        f"Cannot determine SBOM format from {file_path}: "
        "no 'spdxVersion' key and no 'bomFormat: CycloneDX' key found."
    )

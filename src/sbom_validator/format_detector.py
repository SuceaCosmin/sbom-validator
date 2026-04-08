"""Detect SBOM format from raw JSON content."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sbom_validator.exceptions import ParseError, UnsupportedFormatError

logger = logging.getLogger(__name__)


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
        logger.warning("Failed to parse JSON from %s: %s", file_path, exc)
        raise ParseError(f"Invalid JSON in file: {file_path}") from exc

    if not isinstance(data, dict):
        msg = f"Expected a JSON object at the root of {file_path}, got {type(data).__name__}"
        logger.warning("Unsupported format in %s: %s", file_path, msg)
        raise UnsupportedFormatError(msg)

    if "spdxVersion" in data:
        if data["spdxVersion"] != "SPDX-2.3":
            msg = f"Unsupported SPDX version: {data['spdxVersion']!r}. Only SPDX-2.3 is supported."
            logger.warning("Unsupported format in %s: %s", file_path, msg)
            raise UnsupportedFormatError(msg)
        logger.info("Format detected: spdx (file: %s)", file_path)
        return "spdx"

    if data.get("bomFormat") == "CycloneDX":
        spec = data.get("specVersion")
        if spec != "1.6":
            msg = f"Unsupported CycloneDX version: {spec!r}. Only 1.6 is supported."
            logger.warning("Unsupported format in %s: %s", file_path, msg)
            raise UnsupportedFormatError(msg)
        logger.info("Format detected: cyclonedx (file: %s)", file_path)
        return "cyclonedx"

    msg = (
        f"Cannot determine SBOM format from {file_path}: "
        "no 'spdxVersion' key and no 'bomFormat: CycloneDX' key found."
    )
    logger.warning("Unsupported format in %s: %s", file_path, msg)
    raise UnsupportedFormatError(msg)

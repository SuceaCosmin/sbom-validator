"""Detect SBOM format from raw JSON content."""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from sbom_validator.constants import (
    CDX_FIELD_BOM_FORMAT,
    CDX_FIELD_SPEC_VERSION,
    CYCLONEDX_BOM_FORMAT_VALUE,
    CYCLONEDX_SUPPORTED_VERSION,
    CYCLONEDX_XML_NAMESPACE,
    FORMAT_CYCLONEDX,
    FORMAT_SPDX,
    SPDX_FIELD_VERSION,
    SPDX_SUPPORTED_VERSION,
)
from sbom_validator.exceptions import ParseError, UnsupportedFormatError

logger = logging.getLogger(__name__)


def _is_cyclonedx_xml(content: str) -> bool:
    """Return True when content is CycloneDX 1.6 XML."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return False

    namespace = ""
    if root.tag.startswith("{") and "}" in root.tag:
        namespace = root.tag[1 : root.tag.index("}")]
    local_name = root.tag.split("}", 1)[-1]

    if local_name != "bom":
        return False
    if namespace != CYCLONEDX_XML_NAMESPACE:
        return False
    return root.attrib.get("version") == "1"


def detect_format(file_path: Path) -> str:
    """Return 'spdx' or 'cyclonedx' based on file content.

    Raises:
        ParseError: If the file cannot be read.
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
    except json.JSONDecodeError:
        if _is_cyclonedx_xml(content):
            logger.info("Format detected: cyclonedx XML (file: %s)", file_path)
            return FORMAT_CYCLONEDX
        msg = f"Cannot determine SBOM format from {file_path}: invalid JSON and not CycloneDX 1.6 XML."
        logger.warning("Unsupported format in %s: %s", file_path, msg)
        raise UnsupportedFormatError(msg)

    if not isinstance(data, dict):
        msg = f"Expected a JSON object at the root of {file_path}, got {type(data).__name__}"
        logger.warning("Unsupported format in %s: %s", file_path, msg)
        raise UnsupportedFormatError(msg)

    if SPDX_FIELD_VERSION in data:
        if data[SPDX_FIELD_VERSION] != SPDX_SUPPORTED_VERSION:
            msg = (
                f"Unsupported SPDX version: {data[SPDX_FIELD_VERSION]!r}. "
                f"Only {SPDX_SUPPORTED_VERSION} is supported."
            )
            logger.warning("Unsupported format in %s: %s", file_path, msg)
            raise UnsupportedFormatError(msg)
        logger.info("Format detected: spdx (file: %s)", file_path)
        return FORMAT_SPDX

    if data.get(CDX_FIELD_BOM_FORMAT) == CYCLONEDX_BOM_FORMAT_VALUE:
        spec = data.get(CDX_FIELD_SPEC_VERSION)
        if spec != CYCLONEDX_SUPPORTED_VERSION:
            msg = (
                f"Unsupported CycloneDX version: {spec!r}. "
                f"Only {CYCLONEDX_SUPPORTED_VERSION} is supported."
            )
            logger.warning("Unsupported format in %s: %s", file_path, msg)
            raise UnsupportedFormatError(msg)
        logger.info("Format detected: cyclonedx (file: %s)", file_path)
        return FORMAT_CYCLONEDX

    msg = (
        f"Cannot determine SBOM format from {file_path}: "
        "no 'spdxVersion' key and no 'bomFormat: CycloneDX' key found."
    )
    logger.warning("Unsupported format in %s: %s", file_path, msg)
    raise UnsupportedFormatError(msg)

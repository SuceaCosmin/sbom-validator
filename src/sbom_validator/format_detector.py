"""Detect SBOM format from raw file content.

Detection priority (first match wins):
  1. JSON object with @context == SPDX3_CONTEXT_URL    -> "spdx3-jsonld"
  2. JSON object with spdxVersion == "SPDX-2.3"       -> "spdx"
  3. JSON object with bomFormat == "CycloneDX"         -> "cyclonedx"
  4. Non-JSON, valid CycloneDX XML root namespace      -> "cyclonedx"
  5. Non-JSON, content starts with "SPDXVersion: "     -> "spdx-tv"
  6. Non-JSON, YAML dict with spdxVersion == "SPDX-2.3"-> "spdx-yaml"
  7. Otherwise -> UnsupportedFormatError
"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

from sbom_validator.constants import (
    CDX_FIELD_BOM_FORMAT,
    CDX_FIELD_SPEC_VERSION,
    CYCLONEDX_BOM_FORMAT_VALUE,
    CYCLONEDX_SUPPORTED_VERSIONS,
    CYCLONEDX_SUPPORTED_XML_NAMESPACES,
    FORMAT_CYCLONEDX,
    FORMAT_SPDX,
    FORMAT_SPDX3_JSONLD,
    FORMAT_SPDX_TV,
    FORMAT_SPDX_YAML,
    SPDX3_CONTEXT_URL,
    SPDX_FIELD_VERSION,
    SPDX_SUPPORTED_VERSION,
)
from sbom_validator.exceptions import ParseError, UnsupportedFormatError

logger = logging.getLogger(__name__)

# Tag-Value files begin with this exact key (case-sensitive per SPDX spec)
_TV_START_TOKEN = "SPDXVersion: "


def _is_cyclonedx_xml(content: str) -> bool:
    """Return True when content is CycloneDX XML for any supported version."""
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
    if namespace not in CYCLONEDX_SUPPORTED_XML_NAMESPACES:
        return False
    return root.attrib.get("version") == "1"


def _detect_non_json(content: str, file_path: Path, supported_versions_str: str) -> str:
    """Classify non-JSON content as cyclonedx (XML), spdx-tv, spdx-yaml, or raise."""
    # Check CycloneDX XML first (unambiguous binary/structured check)
    if _is_cyclonedx_xml(content):
        logger.info("Format detected: cyclonedx XML (file: %s)", file_path)
        return FORMAT_CYCLONEDX

    # Check SPDX Tag-Value: first non-blank line must start with SPDXVersion:
    first_line = content.lstrip("\ufeff")  # strip optional BOM
    if first_line.startswith(_TV_START_TOKEN):
        version_value = first_line[len(_TV_START_TOKEN) :].split("\n")[0].strip()
        if version_value != SPDX_SUPPORTED_VERSION:
            msg = (
                f"Unsupported SPDX version in Tag-Value file: {version_value!r}. "
                f"Only {SPDX_SUPPORTED_VERSION} is supported."
            )
            logger.warning("Unsupported format in %s: %s", file_path, msg)
            raise UnsupportedFormatError(msg)
        logger.info("Format detected: spdx-tv (file: %s)", file_path)
        return FORMAT_SPDX_TV

    # Check SPDX YAML: attempt safe_load and look for spdxVersion key
    try:
        data: Any = yaml.safe_load(content)
    except yaml.YAMLError:
        data = None

    if isinstance(data, dict) and SPDX_FIELD_VERSION in data:
        version_value = data[SPDX_FIELD_VERSION]
        if version_value != SPDX_SUPPORTED_VERSION:
            msg = (
                f"Unsupported SPDX version in YAML file: {version_value!r}. "
                f"Only {SPDX_SUPPORTED_VERSION} is supported."
            )
            logger.warning("Unsupported format in %s: %s", file_path, msg)
            raise UnsupportedFormatError(msg)
        logger.info("Format detected: spdx-yaml (file: %s)", file_path)
        return FORMAT_SPDX_YAML

    msg = (
        f"Cannot determine SBOM format from {file_path}: "
        f"invalid JSON and not CycloneDX XML ({supported_versions_str}), "
        "not SPDX Tag-Value, and not SPDX YAML."
    )
    logger.warning("Unsupported format in %s: %s", file_path, msg)
    raise UnsupportedFormatError(msg)


def detect_format(file_path: Path) -> str:
    """Return the format string detected from file content.

    Returns one of: 'spdx', 'spdx-tv', 'spdx-yaml', 'cyclonedx'.

    Raises:
        ParseError: If the file cannot be read.
        UnsupportedFormatError: If the format cannot be determined or the
            version is unsupported.
    """
    if not file_path.exists():
        raise ParseError(f"File not found: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParseError(f"Cannot read file: {file_path}") from exc

    _supported_versions_str = ", ".join(sorted(CYCLONEDX_SUPPORTED_VERSIONS))

    # Attempt JSON parse first (covers SPDX JSON and CycloneDX JSON)
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return _detect_non_json(content, file_path, _supported_versions_str)

    if not isinstance(data, dict):
        msg = f"Expected a JSON object at the root of {file_path}, got {type(data).__name__}"
        logger.warning("Unsupported format in %s: %s", file_path, msg)
        raise UnsupportedFormatError(msg)

    # SPDX 3.x JSON-LD: @context key present
    if "@context" in data:
        if data["@context"] == SPDX3_CONTEXT_URL:
            logger.info("Format detected: spdx3-jsonld (file: %s)", file_path)
            return FORMAT_SPDX3_JSONLD
        msg = (
            f"Unrecognized SPDX 3.x context URL: {data['@context']!r}. "
            f"Only {SPDX3_CONTEXT_URL!r} is supported."
        )
        logger.warning("Unsupported format in %s: %s", file_path, msg)
        raise UnsupportedFormatError(msg)

    # SPDX JSON: spdxVersion key present
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

    # CycloneDX JSON: bomFormat key present
    if data.get(CDX_FIELD_BOM_FORMAT) == CYCLONEDX_BOM_FORMAT_VALUE:
        spec = data.get(CDX_FIELD_SPEC_VERSION)
        if spec not in CYCLONEDX_SUPPORTED_VERSIONS:
            msg = (
                f"Unsupported CycloneDX version: {spec!r}. "
                f"Supported versions: {_supported_versions_str}."
            )
            logger.warning("Unsupported format in %s: %s", file_path, msg)
            raise UnsupportedFormatError(msg)
        logger.info("Format detected: cyclonedx %s (file: %s)", spec, file_path)
        return FORMAT_CYCLONEDX

    msg = (
        f"Cannot determine SBOM format from {file_path}: "
        "no 'spdxVersion' key and no 'bomFormat: CycloneDX' key found."
    )
    logger.warning("Unsupported format in %s: %s", file_path, msg)
    raise UnsupportedFormatError(msg)

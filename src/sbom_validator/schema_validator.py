"""JSON schema validation for SPDX and CycloneDX SBOM files."""

from __future__ import annotations

import json
import logging
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import jsonschema
import jsonschema.exceptions
import xmlschema

from sbom_validator.constants import (
    FORMAT_CYCLONEDX,
    FORMAT_SPDX,
    RULE_CDX_SCHEMA,
    RULE_SPDX_SCHEMA,
)
from sbom_validator.models import IssueSeverity, ValidationIssue

logger = logging.getLogger(__name__)


def _schemas_dir() -> Path:
    """Return the path to the bundled schemas directory.

    Works in both normal (development) and PyInstaller frozen modes.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass: str = getattr(sys, "_MEIPASS")
        return Path(meipass) / "schemas"
    return Path(__file__).parent / "schemas"


_SCHEMA_FILES: dict[str, str] = {
    FORMAT_SPDX: "spdx-2.3.schema.json",
    FORMAT_CYCLONEDX: "cyclonedx-1.6.schema.json",
}

_FORMAT_RULES: dict[str, str] = {
    FORMAT_SPDX: RULE_SPDX_SCHEMA,
    FORMAT_CYCLONEDX: RULE_CDX_SCHEMA,
}

_loaded_schemas: dict[str, dict[str, Any]] = {}
_loaded_xml_schemas: dict[str, xmlschema.XMLSchemaBase] = {}


def _load_schema(format_name: str) -> dict[str, Any]:
    """Load and cache the bundled JSON schema for the given format."""
    if format_name not in _loaded_schemas:
        schema_path = _schemas_dir() / _SCHEMA_FILES[format_name]
        _loaded_schemas[format_name] = json.loads(schema_path.read_text(encoding="utf-8"))
    return _loaded_schemas[format_name]


def _load_cyclonedx_xml_schema() -> xmlschema.XMLSchemaBase:
    """Load and cache the bundled CycloneDX 1.6 XML schema."""
    key = "cyclonedx-xml"
    if key not in _loaded_xml_schemas:
        schema_path = _schemas_dir() / "cyclonedx-1.6.schema.xsd"
        _loaded_xml_schemas[key] = xmlschema.XMLSchema(str(schema_path))
    return _loaded_xml_schemas[key]


def _validate_json_schema(
    raw_doc: dict[str, Any], format_name: str, rule: str
) -> list[ValidationIssue]:
    """Validate a JSON document and return ValidationIssue items."""
    schema = _load_schema(format_name)
    validator = jsonschema.Draft7Validator(schema)
    issues: list[ValidationIssue] = []
    for error in validator.iter_errors(raw_doc):
        field_path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "$"
        issues.append(
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                field_path=field_path,
                message=error.message,
                rule=rule,
            )
        )
    return issues


def _validate_cyclonedx_xml(raw_doc: str, rule: str) -> list[ValidationIssue]:
    """Validate a CycloneDX XML document against the bundled XSD."""
    issues: list[ValidationIssue] = []
    try:
        root = ET.fromstring(raw_doc)
    except ET.ParseError as exc:
        return [
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                field_path="$",
                message=f"Invalid XML: {exc}",
                rule=rule,
            )
        ]

    validator = _load_cyclonedx_xml_schema()
    for error in validator.iter_errors(root):
        field_path = error.path or "$"
        issues.append(
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                field_path=field_path,
                message=error.reason or str(error),
                rule=rule,
            )
        )
    return issues


def validate_schema(raw_doc: dict[str, Any] | str, format_name: str) -> list[ValidationIssue]:
    """Validate raw document against the appropriate schema.

    Args:
        raw_doc: Parsed JSON document as a dict, or XML string for CycloneDX XML.
        format_name: Either 'spdx' or 'cyclonedx'.

    Returns:
        List of ValidationIssue objects (empty if valid).

    Raises:
        ValueError: If format_name is not 'spdx' or 'cyclonedx'.
    """
    if format_name not in _SCHEMA_FILES:
        raise ValueError(f"Unknown format: {format_name!r}. Expected one of: {list(_SCHEMA_FILES)}")

    logger.debug("Running schema validation for format %s", format_name)
    rule = _FORMAT_RULES[format_name]
    if format_name == FORMAT_SPDX:
        if not isinstance(raw_doc, dict):
            raise ValueError("SPDX schema validation expects a JSON object document.")
        issues = _validate_json_schema(raw_doc, format_name, rule)
    elif isinstance(raw_doc, str):
        issues = _validate_cyclonedx_xml(raw_doc, rule)
    else:
        issues = _validate_json_schema(raw_doc, format_name, rule)

    if issues:
        logger.info("Schema validation found %d error(s)", len(issues))
    else:
        logger.info("Schema validation passed (%d issues)", len(issues))

    return issues

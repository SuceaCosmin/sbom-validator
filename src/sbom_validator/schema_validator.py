"""JSON schema validation for SPDX and CycloneDX SBOM files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import jsonschema.exceptions

from sbom_validator.models import IssueSeverity, ValidationIssue

_SCHEMAS_DIR = Path(__file__).parent / "schemas"

_SCHEMA_FILES: dict[str, str] = {
    "spdx": "spdx-2.3.schema.json",
    "cyclonedx": "cyclonedx-1.6.schema.json",
}

_FORMAT_RULES: dict[str, str] = {
    "spdx": "FR-02",
    "cyclonedx": "FR-03",
}

_loaded_schemas: dict[str, dict[str, Any]] = {}


def _load_schema(format_name: str) -> dict[str, Any]:
    """Load and cache the bundled JSON schema for the given format."""
    if format_name not in _loaded_schemas:
        schema_path = _SCHEMAS_DIR / _SCHEMA_FILES[format_name]
        _loaded_schemas[format_name] = json.loads(
            schema_path.read_text(encoding="utf-8")
        )
    return _loaded_schemas[format_name]


def validate_schema(raw_doc: dict[str, Any], format_name: str) -> list[ValidationIssue]:
    """Validate raw JSON document against the appropriate schema.

    Args:
        raw_doc: Parsed JSON document as a dict.
        format_name: Either 'spdx' or 'cyclonedx'.

    Returns:
        List of ValidationIssue objects (empty if valid).

    Raises:
        ValueError: If format_name is not 'spdx' or 'cyclonedx'.
    """
    if format_name not in _SCHEMA_FILES:
        raise ValueError(
            f"Unknown format: {format_name!r}. Expected one of: {list(_SCHEMA_FILES)}"
        )

    schema = _load_schema(format_name)
    rule = _FORMAT_RULES[format_name]
    schema_path = _SCHEMAS_DIR / _SCHEMA_FILES[format_name]

    try:
        resolver = jsonschema.RefResolver(
            base_uri=schema_path.as_uri(),
            referrer=schema,
        )
        validator_cls = jsonschema.Draft7Validator
        validator = validator_cls(schema, resolver=resolver)
    except Exception:
        # Fall back to basic validator without resolver
        validator = jsonschema.Draft7Validator(schema)

    issues: list[ValidationIssue] = []
    for error in validator.iter_errors(raw_doc):
        if error.absolute_path:
            field_path = ".".join(str(p) for p in error.absolute_path)
        else:
            field_path = "$"
        issues.append(
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                field_path=field_path,
                message=error.message,
                rule=rule,
            )
        )

    return issues

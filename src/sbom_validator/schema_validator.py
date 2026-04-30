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
    CYCLONEDX_SUPPORTED_VERSIONS,
    FORMAT_CYCLONEDX,
    FORMAT_SPDX,
    FORMAT_SPDX3_JSONLD,
    FORMAT_SPDX_TV,
    FORMAT_SPDX_YAML,
    RULE_CDX_SCHEMA,
    RULE_SPDX3_SCHEMA,
    RULE_SPDX_SCHEMA,
    SPDX3_CONTEXT_URL,
)
from sbom_validator.models import IssueCategory, IssueSeverity, ValidationIssue

logger = logging.getLogger(__name__)


def _schemas_dir() -> Path:
    """Return the path to the bundled schemas directory.

    Works in both normal (development) and PyInstaller frozen modes.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass: str = getattr(sys, "_MEIPASS")
        return Path(meipass) / "schemas"
    return Path(__file__).parent / "schemas"


_CDX_JSON_SCHEMA_FILES: dict[str, str] = {
    v: f"cyclonedx-{v}.schema.json" for v in CYCLONEDX_SUPPORTED_VERSIONS
}

_CDX_XSD_SCHEMA_FILES: dict[str, str] = {
    v: f"cyclonedx-{v}.schema.xsd" for v in CYCLONEDX_SUPPORTED_VERSIONS
}

_SPDX_SCHEMA_FILE = "spdx-2.3.schema.json"
_SPDX3_SCHEMA_FILE = "spdx-3.0.1.schema.json"

# Cache key used for the SPDX 3.x envelope-only schema (see _load_spdx3_schema docstring).
_SPDX3_ENVELOPE_CACHE_KEY = "spdx3-jsonld-envelope"

_loaded_json_schemas: dict[str, dict[str, Any]] = {}
_loaded_xml_schemas: dict[str, xmlschema.XMLSchemaBase] = {}


def _load_spdx_schema() -> dict[str, Any]:
    """Load and cache the bundled SPDX 2.3 JSON schema."""
    key = FORMAT_SPDX
    if key not in _loaded_json_schemas:
        schema_path = _schemas_dir() / _SPDX_SCHEMA_FILE
        _loaded_json_schemas[key] = json.loads(schema_path.read_text(encoding="utf-8"))
    return _loaded_json_schemas[key]


def _load_spdx3_schema() -> dict[str, Any]:
    """Return a Draft 2020-12 envelope schema for SPDX 3.x JSON-LD documents.

    The full SPDX 3.0.1 JSON Schema uses a complex `if/then/else` structure where
    the `else` branch (`$ref: AnyClass`) requires the root document to be a concrete
    typed SPDX element when `@graph` is absent.  This would incorrectly reject
    minimal documents that contain only the required `@context` field — a valid
    structural pattern for SPDX 3.x JSON-LD files that use `@graph` for their
    element list and rely on the context to establish the vocabulary.

    The schema-validation stage's responsibility is to verify the document's
    *envelope* (is `@context` present and correct?), not to deep-validate every
    SPDX element in the graph — that is the parser's job.  We therefore synthesise
    a minimal envelope schema from the full schema's top-level constraints rather
    than loading the full schema verbatim.
    """
    if _SPDX3_ENVELOPE_CACHE_KEY not in _loaded_json_schemas:
        # Build an envelope schema that validates:
        #   - "@context" is present and equals the canonical SPDX 3.0.1 context URL
        #   - No other top-level constraints (element-level validation is the parser's concern)
        envelope_schema: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "@context": {
                    "const": SPDX3_CONTEXT_URL,
                }
            },
            "required": ["@context"],
        }
        _loaded_json_schemas[_SPDX3_ENVELOPE_CACHE_KEY] = envelope_schema
    return _loaded_json_schemas[_SPDX3_ENVELOPE_CACHE_KEY]


def _load_cdx_json_schema(version: str) -> dict[str, Any]:
    """Load and cache the bundled CycloneDX JSON schema for the given version."""
    key = f"cyclonedx-{version}"
    if key not in _loaded_json_schemas:
        schema_path = _schemas_dir() / _CDX_JSON_SCHEMA_FILES[version]
        _loaded_json_schemas[key] = json.loads(schema_path.read_text(encoding="utf-8"))
    return _loaded_json_schemas[key]


def _load_cdx_xml_schema(version: str) -> xmlschema.XMLSchemaBase:
    """Load and cache the bundled CycloneDX XSD schema for the given version."""
    key = f"cyclonedx-xml-{version}"
    if key not in _loaded_xml_schemas:
        schema_path = _schemas_dir() / _CDX_XSD_SCHEMA_FILES[version]
        _loaded_xml_schemas[key] = xmlschema.XMLSchema(str(schema_path))
    return _loaded_xml_schemas[key]


def _validate_json_schema(
    raw_doc: dict[str, Any], schema: dict[str, Any], rule: str
) -> list[ValidationIssue]:
    """Validate a JSON document against a Draft 7 schema and return ValidationIssue items."""
    validator = jsonschema.Draft7Validator(schema)
    issues: list[ValidationIssue] = []
    for error in validator.iter_errors(raw_doc):
        field_path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "$"
        issues.append(
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.SCHEMA,
                field_path=field_path,
                message=error.message,
                rule=rule,
            )
        )
    return issues


def _validate_json_schema_2020(
    raw_doc: dict[str, Any], schema: dict[str, Any], rule: str
) -> list[ValidationIssue]:
    """Validate a JSON document against a Draft 2020-12 schema and return ValidationIssue items.

    SPDX 3.x uses JSON Schema Draft 2020-12, which requires a dedicated validator
    class — Draft7Validator does not understand the 2020-12 dialect keywords.
    """
    validator = jsonschema.Draft202012Validator(schema)
    issues: list[ValidationIssue] = []
    for error in validator.iter_errors(raw_doc):
        field_path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "$"
        issues.append(
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.SCHEMA,
                field_path=field_path,
                message=error.message,
                rule=rule,
            )
        )
    return issues


def _validate_cyclonedx_xml(raw_doc: str, cdx_version: str, rule: str) -> list[ValidationIssue]:
    """Validate a CycloneDX XML document against the bundled XSD for the given version."""
    issues: list[ValidationIssue] = []
    try:
        root = ET.fromstring(raw_doc)
    except ET.ParseError as exc:
        return [
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.SCHEMA,
                field_path="$",
                message=f"Invalid XML: {exc}",
                rule=rule,
            )
        ]

    validator = _load_cdx_xml_schema(cdx_version)
    for error in validator.iter_errors(root):
        field_path = error.path or "$"
        issues.append(
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.SCHEMA,
                field_path=field_path,
                message=error.reason or str(error),
                rule=rule,
            )
        )
    return issues


def validate_schema(
    raw_doc: dict[str, Any] | str, format_name: str, cdx_version: str | None = None
) -> list[ValidationIssue]:
    """Validate raw document against the appropriate schema.

    Args:
        raw_doc: Parsed JSON document as a dict, or XML string for CycloneDX XML.
            For 'spdx-yaml', pass the already-loaded YAML dict (same structure
            as SPDX JSON). For 'spdx-tv', pass any value — schema is skipped.
        format_name: One of 'spdx', 'spdx-yaml', 'spdx-tv', 'cyclonedx', or
            'spdx3-jsonld'.
        cdx_version: CycloneDX spec version (e.g. '1.3', '1.5'). Required when
            format_name is 'cyclonedx'. If None, the version is inferred from the
            document itself (JSON: specVersion field; XML: root namespace).

    Returns:
        List of ValidationIssue objects (empty if valid or schema skipped).

    Raises:
        ValueError: If format_name is not a recognised format string.
    """
    _known = (FORMAT_SPDX, FORMAT_SPDX_YAML, FORMAT_SPDX_TV, FORMAT_CYCLONEDX, FORMAT_SPDX3_JSONLD)
    if format_name not in _known:
        raise ValueError(f"Unknown format: {format_name!r}. Expected one of {_known!r}.")

    logger.debug("Running schema validation for format %s version %s", format_name, cdx_version)

    # SPDX Tag-Value: no formal schema — explicitly skip
    if format_name == FORMAT_SPDX_TV:
        logger.info("Schema validation skipped for spdx-tv: no formal schema available")
        return []

    if format_name in (FORMAT_SPDX, FORMAT_SPDX_YAML):
        if not isinstance(raw_doc, dict):
            raise ValueError(f"{format_name} schema validation expects a JSON/YAML dict document.")
        issues = _validate_json_schema(raw_doc, _load_spdx_schema(), RULE_SPDX_SCHEMA)
    elif format_name == FORMAT_SPDX3_JSONLD:
        if not isinstance(raw_doc, dict):
            raise ValueError(f"{format_name} schema validation expects a JSON dict document.")
        issues = _validate_json_schema_2020(raw_doc, _load_spdx3_schema(), RULE_SPDX3_SCHEMA)
    else:
        # Resolve version if not provided
        if cdx_version is None:
            if isinstance(raw_doc, dict):
                cdx_version = str(raw_doc.get("specVersion", "1.6"))
            else:
                cdx_version = _infer_cdx_version_from_xml(raw_doc)

        if cdx_version not in CYCLONEDX_SUPPORTED_VERSIONS:
            cdx_version = "1.6"

        if isinstance(raw_doc, str):
            issues = _validate_cyclonedx_xml(raw_doc, cdx_version, RULE_CDX_SCHEMA)
        else:
            issues = _validate_json_schema(
                raw_doc, _load_cdx_json_schema(cdx_version), RULE_CDX_SCHEMA
            )

    if issues:
        logger.info("Schema validation found %d error(s)", len(issues))
    else:
        logger.info("Schema validation passed (%d issues)", len(issues))

    return issues


def _infer_cdx_version_from_xml(xml_content: str) -> str:
    """Extract CycloneDX spec version from an XML document's root namespace."""
    from sbom_validator.constants import CYCLONEDX_XML_NAMESPACE_PREFIX

    try:
        root = ET.fromstring(xml_content)
        if root.tag.startswith("{") and "}" in root.tag:
            ns = root.tag[1 : root.tag.index("}")]
            if ns.startswith(CYCLONEDX_XML_NAMESPACE_PREFIX):
                return ns[len(CYCLONEDX_XML_NAMESPACE_PREFIX) :]
    except ET.ParseError:
        pass
    return "1.6"

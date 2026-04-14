"""Top-level validation orchestrator."""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from sbom_validator.constants import (
    CDX_FIELD_SPEC_VERSION,
    CYCLONEDX_XML_NAMESPACE_PREFIX,
    FORMAT_SPDX,
    FORMAT_SPDX_TV,
    FORMAT_SPDX_YAML,
    RULE_FORMAT_DETECTION,
)
from sbom_validator.exceptions import ParseError, UnsupportedFormatError
from sbom_validator.format_detector import detect_format
from sbom_validator.models import (
    IssueSeverity,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)
from sbom_validator.ntia_checker import check_ntia
from sbom_validator.parsers.cyclonedx_parser import parse_cyclonedx
from sbom_validator.parsers.spdx_parser import parse_spdx
from sbom_validator.parsers.spdx_tv_parser import parse_spdx_tv
from sbom_validator.parsers.spdx_yaml_parser import parse_spdx_yaml
from sbom_validator.schema_validator import validate_schema

logger = logging.getLogger(__name__)

# Set of all SPDX format identifiers (JSON, YAML, Tag-Value)
_SPDX_FORMATS = frozenset({FORMAT_SPDX, FORMAT_SPDX_TV, FORMAT_SPDX_YAML})


def _extract_cdx_version(raw_doc: dict[str, object] | str) -> str | None:
    """Extract the CycloneDX spec version from a parsed JSON doc or XML string."""
    if isinstance(raw_doc, dict):
        val = raw_doc.get(CDX_FIELD_SPEC_VERSION)
        return str(val) if val is not None else None
    try:
        root = ET.fromstring(raw_doc)
        if root.tag.startswith("{") and "}" in root.tag:
            ns = root.tag[1 : root.tag.index("}")]
            if ns.startswith(CYCLONEDX_XML_NAMESPACE_PREFIX):
                return ns[len(CYCLONEDX_XML_NAMESPACE_PREFIX) :]
    except ET.ParseError:
        pass
    return None


def _error_issue(message: str, rule: str = "SYS-ERROR") -> ValidationIssue:
    """Build a consistent ERROR issue payload for tool/input failures."""
    return ValidationIssue(
        severity=IssueSeverity.ERROR,
        field_path="",
        message=message,
        rule=rule,
    )


def _load_raw_doc(file_path: Path, format_name: str) -> dict[str, object] | str:
    """Read and parse the raw document according to its format.

    Returns:
        dict for JSON-based formats (spdx, spdx-yaml, cyclonedx JSON),
        str for XML-based (cyclonedx XML) and TV formats.

    Raises:
        ParseError, json.JSONDecodeError, yaml.YAMLError, OSError on failure.
    """
    raw_text = file_path.read_text(encoding="utf-8")

    if format_name == FORMAT_SPDX:
        parsed: dict[str, object] = json.loads(raw_text)
        return parsed

    if format_name == FORMAT_SPDX_TV:
        return raw_text  # TV has no schema; return text as-is

    if format_name == FORMAT_SPDX_YAML:
        doc = yaml.safe_load(raw_text)
        if not isinstance(doc, dict):
            raise ParseError(f"SPDX YAML file '{file_path}' must be a YAML mapping at the root.")
        result: dict[str, object] = doc
        return result

    # CycloneDX: try JSON first, fall back to raw text (XML)
    try:
        cdx_parsed: dict[str, object] = json.loads(raw_text)
        return cdx_parsed
    except json.JSONDecodeError:
        return raw_text


def validate(file_path: str | Path) -> ValidationResult:
    """Validate an SBOM file through the full pipeline.

    Pipeline: format detection -> schema validation -> parsing -> NTIA checking.

    Args:
        file_path: Path to the SBOM file (str or Path).

    Returns:
        ValidationResult with status and any issues found.
    """
    file_path = Path(file_path)
    str_path = str(file_path)
    format_name: str | None = None

    logger.info("Validation started for: %s", str_path)

    # Stage 0: Format detection
    logger.debug("Stage %s \u2192 %s", "start", "format_detection")
    try:
        format_name = detect_format(file_path)
        logger.info("Format detected: %s", format_name)
    except (ParseError, UnsupportedFormatError) as e:
        logger.warning("Validation input error for %s: %s", str_path, e)
        return ValidationResult(
            status=ValidationStatus.ERROR,
            file_path=str_path,
            issues=(_error_issue(str(e), rule=RULE_FORMAT_DETECTION),),
            format_detected=None,
        )
    except Exception as e:
        logger.error("Unexpected error during validation of %s: %s", str_path, e)
        return ValidationResult(
            status=ValidationStatus.ERROR,
            file_path=str_path,
            issues=(_error_issue(str(e)),),
            format_detected=None,
        )

    # Stage 1: Read raw document
    logger.debug("Stage %s \u2192 %s", "format_detection", "schema_validation")
    try:
        raw_doc: dict[str, object] | str = _load_raw_doc(file_path, format_name)
    except Exception as e:
        logger.error("Unexpected error reading %s: %s", str_path, e)
        return ValidationResult(
            status=ValidationStatus.ERROR,
            file_path=str_path,
            issues=(_error_issue(str(e)),),
            format_detected=format_name,
        )

    # Stage 2: Schema validation
    cdx_version: str | None = None
    if format_name not in _SPDX_FORMATS:
        cdx_version = _extract_cdx_version(raw_doc)
        logger.debug("CycloneDX spec version extracted: %s", cdx_version)

    schema_issues = validate_schema(raw_doc, format_name, cdx_version)
    logger.info("Schema validation complete, %d issues found", len(schema_issues))
    if schema_issues:
        result = ValidationResult(
            status=ValidationStatus.FAIL,
            file_path=str_path,
            issues=tuple(schema_issues),
            format_detected=format_name,
        )
        logger.debug("Pipeline complete with final status: %s", result.status.value)
        return result

    # Stage 3: Parse into normalized SBOM (only if schema passed)
    logger.debug("Stage %s \u2192 %s", "schema_validation", "parsing")
    try:
        if format_name == FORMAT_SPDX:
            sbom = parse_spdx(file_path)
        elif format_name == FORMAT_SPDX_TV:
            sbom = parse_spdx_tv(file_path)
        elif format_name == FORMAT_SPDX_YAML:
            sbom = parse_spdx_yaml(file_path)
        else:
            sbom = parse_cyclonedx(file_path)
    except ParseError as e:
        logger.warning("Validation parse error for %s: %s", str_path, e)
        return ValidationResult(
            status=ValidationStatus.ERROR,
            file_path=str_path,
            issues=(_error_issue(str(e)),),
            format_detected=format_name,
        )

    # Stage 4: NTIA compliance check
    logger.debug("Stage %s \u2192 %s", "parsing", "ntia_check")
    ntia_issues = check_ntia(sbom)
    logger.info("NTIA check complete, %d issues found", len(ntia_issues))
    if ntia_issues:
        result = ValidationResult(
            status=ValidationStatus.FAIL,
            file_path=str_path,
            issues=tuple(ntia_issues),
            format_detected=format_name,
        )
        logger.debug("Pipeline complete with final status: %s", result.status.value)
        return result

    final_result = ValidationResult(
        status=ValidationStatus.PASS,
        file_path=str_path,
        issues=(),
        format_detected=format_name,
    )
    logger.info(
        "Validation completed: status=%s, issues=%d",
        final_result.status.value,
        len(final_result.issues),
    )
    logger.debug("Pipeline complete with final status: %s", final_result.status.value)
    return final_result

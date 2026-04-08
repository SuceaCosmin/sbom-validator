"""Top-level validation orchestrator."""

from __future__ import annotations

import json
import logging
from pathlib import Path

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
from sbom_validator.schema_validator import validate_schema

logger = logging.getLogger(__name__)


def validate(file_path: str | Path) -> ValidationResult:
    """Validate an SBOM file through the full pipeline.

    Pipeline: format detection -> schema validation -> parsing -> NTIA checking.

    Args:
        file_path: Path to the SBOM JSON file (str or Path).

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
        logger.warning("Unexpected error during validation of %s: %s", str_path, e)
        return ValidationResult(
            status=ValidationStatus.ERROR,
            file_path=str_path,
            issues=(),
            format_detected=None,
        )
    except Exception as e:
        logger.error("Unexpected error during validation of %s: %s", str_path, e)
        return ValidationResult(
            status=ValidationStatus.ERROR,
            file_path=str_path,
            issues=(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    field_path="",
                    message=str(e),
                    rule="",
                ),
            ),
            format_detected=None,
        )

    # Stage 1: Read raw JSON
    logger.debug("Stage %s \u2192 %s", "format_detection", "schema_validation")
    try:
        raw_doc = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Unexpected error during validation of %s: %s", str_path, e)
        return ValidationResult(
            status=ValidationStatus.ERROR,
            file_path=str_path,
            issues=(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    field_path="",
                    message=str(e),
                    rule="",
                ),
            ),
            format_detected=format_name,
        )

    # Stage 2: Schema validation
    schema_issues = validate_schema(raw_doc, format_name)
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
        if format_name == "spdx":
            sbom = parse_spdx(file_path)
        else:
            sbom = parse_cyclonedx(file_path)
    except ParseError as e:
        logger.warning("Unexpected error during validation of %s: %s", str_path, e)
        return ValidationResult(
            status=ValidationStatus.ERROR,
            file_path=str_path,
            issues=(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    field_path="",
                    message=str(e),
                    rule="",
                ),
            ),
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

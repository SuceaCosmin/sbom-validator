"""Top-level validation orchestrator."""

from __future__ import annotations

import json
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

    # Stage 0: Format detection
    try:
        format_name = detect_format(file_path)
    except (ParseError, UnsupportedFormatError):
        return ValidationResult(
            status=ValidationStatus.ERROR,
            file_path=str_path,
            issues=(),
            format_detected=None,
        )
    except Exception as e:
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
    try:
        raw_doc = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
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
    if schema_issues:
        return ValidationResult(
            status=ValidationStatus.FAIL,
            file_path=str_path,
            issues=tuple(schema_issues),
            format_detected=format_name,
        )

    # Stage 3: Parse into normalized SBOM (only if schema passed)
    try:
        if format_name == "spdx":
            sbom = parse_spdx(file_path)
        else:
            sbom = parse_cyclonedx(file_path)
    except ParseError as e:
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
    ntia_issues = check_ntia(sbom)
    if ntia_issues:
        return ValidationResult(
            status=ValidationStatus.FAIL,
            file_path=str_path,
            issues=tuple(ntia_issues),
            format_detected=format_name,
        )

    return ValidationResult(
        status=ValidationStatus.PASS,
        file_path=str_path,
        issues=(),
        format_detected=format_name,
    )

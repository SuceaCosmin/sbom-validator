"""NTIA minimum elements compliance checker."""

from __future__ import annotations

import logging
from datetime import datetime

from sbom_validator.models import IssueSeverity, NormalizedSBOM, ValidationIssue

logger = logging.getLogger(__name__)


def check_ntia(sbom: NormalizedSBOM) -> list[ValidationIssue]:
    """Check NTIA minimum element compliance.

    Returns:
        List of ValidationIssue objects for any missing elements.
    """
    logger.debug("Running NTIA minimum elements check")
    issues: list[ValidationIssue] = []
    issues.extend(_check_supplier(sbom))
    issues.extend(_check_component_name(sbom))
    issues.extend(_check_version(sbom))
    issues.extend(_check_identifiers(sbom))
    issues.extend(_check_relationships(sbom))
    issues.extend(_check_author(sbom))
    issues.extend(_check_timestamp(sbom))
    logger.info("NTIA check completed: %d issue(s)", len(issues))
    return issues


def _check_supplier(sbom: NormalizedSBOM) -> list[ValidationIssue]:
    """FR-04: Every component must have a non-empty supplier name."""
    issues: list[ValidationIssue] = []
    for i, component in enumerate(sbom.components):
        if component.supplier is None or component.supplier.strip() == "":
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    field_path=f"components[{i}].supplier",
                    message=(
                        f"Component '{component.name}' is missing a supplier name (NTIA FR-04)"
                    ),
                    rule="FR-04",
                )
            )
    return issues


def _check_component_name(sbom: NormalizedSBOM) -> list[ValidationIssue]:
    """FR-05: Every component must have a non-empty name."""
    issues: list[ValidationIssue] = []
    for i, component in enumerate(sbom.components):
        if component.name.strip() == "":
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    field_path=f"components[{i}].name",
                    message=(f"Component at index {i} is missing a component name (NTIA FR-05)"),
                    rule="FR-05",
                )
            )
    return issues


def _check_version(sbom: NormalizedSBOM) -> list[ValidationIssue]:
    """FR-06: Every component must have a non-empty version."""
    issues: list[ValidationIssue] = []
    for i, component in enumerate(sbom.components):
        if component.version is None or component.version.strip() == "":
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    field_path=f"components[{i}].version",
                    message=(f"Component '{component.name}' is missing a version (NTIA FR-06)"),
                    rule="FR-06",
                )
            )
    return issues


def _check_identifiers(sbom: NormalizedSBOM) -> list[ValidationIssue]:
    """FR-07: Every component must have at least one unique identifier."""
    issues: list[ValidationIssue] = []
    for i, component in enumerate(sbom.components):
        if not component.identifiers:
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    field_path=f"components[{i}].identifiers",
                    message=(
                        f"Component '{component.name}' has no unique identifiers "
                        f"(e.g., PURL or CPE) (NTIA FR-07)"
                    ),
                    rule="FR-07",
                )
            )
    return issues


def _check_relationships(sbom: NormalizedSBOM) -> list[ValidationIssue]:
    """FR-08: The SBOM must declare at least one dependency relationship."""
    if not sbom.relationships:
        return [
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                field_path="relationships",
                message=("SBOM declares no dependency relationships (NTIA FR-08)"),
                rule="FR-08",
            )
        ]
    return []


def _check_author(sbom: NormalizedSBOM) -> list[ValidationIssue]:
    """FR-09: The SBOM must identify at least one author."""
    if sbom.author is None or sbom.author.strip() == "":
        return [
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                field_path="author",
                message=("SBOM is missing author information (NTIA FR-09)"),
                rule="FR-09",
            )
        ]
    return []


def _check_timestamp(sbom: NormalizedSBOM) -> list[ValidationIssue]:
    """FR-10: The SBOM must contain a valid ISO 8601 timestamp."""
    if sbom.timestamp is None or sbom.timestamp.strip() == "":
        return [
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                field_path="timestamp",
                message=("SBOM is missing a creation timestamp (NTIA FR-10)"),
                rule="FR-10",
            )
        ]

    raw_timestamp = sbom.timestamp.strip()
    # Accept "Z" suffix by normalizing to a UTC offset for fromisoformat().
    normalized = raw_timestamp[:-1] + "+00:00" if raw_timestamp.endswith("Z") else raw_timestamp
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return [
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                field_path="timestamp",
                message=(
                    f"SBOM timestamp '{raw_timestamp}' is not a valid ISO 8601 date-time "
                    "(NTIA FR-10)"
                ),
                rule="FR-10",
            )
        ]
    return []

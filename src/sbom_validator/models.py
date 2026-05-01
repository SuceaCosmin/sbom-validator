"""Data models for normalized SBOM representation and validation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ValidationStatus(StrEnum):
    """Overall validation outcome."""

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


class IssueSeverity(StrEnum):
    """Severity level of a validation issue."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class IssueCategory(StrEnum):
    """Category of a validation issue — which pipeline stage produced it."""

    SCHEMA = "SCHEMA"
    NTIA = "NTIA"
    FORMAT = "FORMAT"


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation finding."""

    severity: IssueSeverity
    category: IssueCategory
    field_path: str
    message: str
    rule: str = ""


@dataclass(frozen=True)
class NormalizedComponent:
    """A normalized representation of a single SBOM component."""

    component_id: str
    name: str
    version: str | None = None
    supplier: str | None = None
    identifiers: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NormalizedRelationship:
    """A directed dependency relationship between two components."""

    from_id: str
    to_id: str
    relationship_type: str = "DEPENDS_ON"


@dataclass(frozen=True)
class NormalizedSBOM:
    """Format-agnostic internal representation of an SBOM."""

    format: str  # one of "spdx", "spdx-tv", "spdx-yaml", "spdx3-jsonld", "cyclonedx"
    author: str | None = None
    timestamp: str | None = None
    components: tuple[NormalizedComponent, ...] = field(default_factory=tuple)
    relationships: tuple[NormalizedRelationship, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ValidationResult:
    """The complete result of validating an SBOM file."""

    status: ValidationStatus
    file_path: str
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    format_detected: str | None = None

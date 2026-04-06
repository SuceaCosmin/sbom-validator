"""JSON schema validation for SPDX and CycloneDX SBOM files."""

from __future__ import annotations

from pathlib import Path

from sbom_validator.models import ValidationIssue


def validate_schema(raw_doc: dict, format_name: str) -> list[ValidationIssue]:
    """Validate raw JSON document against the appropriate schema.

    Args:
        raw_doc: Parsed JSON document as a dict.
        format_name: Either 'spdx' or 'cyclonedx'.

    Returns:
        List of ValidationIssue objects (empty if valid).
    """
    # TODO: implement in Phase 2
    raise NotImplementedError

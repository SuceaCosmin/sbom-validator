"""NTIA minimum elements compliance checker."""

from __future__ import annotations

from sbom_validator.models import NormalizedSBOM, ValidationIssue


def check_ntia(sbom: NormalizedSBOM) -> list[ValidationIssue]:
    """Check NTIA minimum element compliance.

    Returns:
        List of ValidationIssue objects for any missing elements.
    """
    # TODO: implement in Phase 2
    raise NotImplementedError

"""Top-level validation orchestrator."""

from __future__ import annotations

from pathlib import Path

from sbom_validator.models import ValidationResult


def validate(file_path: Path) -> ValidationResult:
    """Validate an SBOM file through the full pipeline.

    Pipeline: format detection -> schema validation -> parsing -> NTIA checking.

    Args:
        file_path: Path to the SBOM JSON file.

    Returns:
        ValidationResult with status and any issues found.
    """
    # TODO: implement in Phase 2
    raise NotImplementedError

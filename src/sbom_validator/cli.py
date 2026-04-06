"""CLI entry point for sbom-validator."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from sbom_validator import __version__
from sbom_validator.models import ValidationResult, ValidationStatus
from sbom_validator.validator import validate


def _result_to_dict(result: ValidationResult) -> dict[str, Any]:
    """Serialise a ValidationResult to a JSON-compatible dict."""
    return {
        "status": result.status.value,
        "file": result.file_path,
        "format_detected": result.format_detected,
        "issues": [
            {
                "severity": issue.severity.value,
                "field_path": issue.field_path,
                "message": issue.message,
                "rule": issue.rule,
            }
            for issue in result.issues
        ],
    }


def _exit_code(result: ValidationResult) -> int:
    """Map ValidationStatus to CLI exit code."""
    if result.status == ValidationStatus.PASS:
        return 0
    if result.status == ValidationStatus.FAIL:
        return 1
    return 2  # ERROR


def _render_text(result: ValidationResult) -> str:
    """Render a human-readable text report."""
    lines: list[str] = []
    status_label = result.status.value  # "PASS", "FAIL", "ERROR"
    lines.append(f"Status:  {status_label}")
    lines.append(f"File:    {result.file_path}")
    if result.format_detected:
        lines.append(f"Format:  {result.format_detected}")
    if result.issues:
        lines.append(f"Issues:  {len(result.issues)}")
        for issue in result.issues:
            lines.append(
                f"  [{issue.severity.value}] {issue.field_path}: {issue.message} ({issue.rule})"
            )
    else:
        if result.status == ValidationStatus.PASS:
            lines.append("Issues:  none")
    return "\n".join(lines)


@click.group()
@click.version_option(version=__version__, prog_name="sbom-validator")
def main() -> None:
    """Validate SBOM files against schema and NTIA minimum elements."""


@main.command(name="validate")
@click.argument("file", type=click.Path(exists=False))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    show_default=True,
    help="Output format.",
)
def validate_cmd(file: str, output_format: str) -> None:
    """Validate an SBOM FILE against schema and NTIA minimum elements.

    Exits with code 0 (PASS), 1 (validation FAIL), or 2 (tool ERROR).
    """
    file_path = Path(file)
    result = validate(file_path)

    if output_format == "json":
        click.echo(json.dumps(_result_to_dict(result), indent=2))
    else:
        click.echo(_render_text(result))

    sys.exit(_exit_code(result))

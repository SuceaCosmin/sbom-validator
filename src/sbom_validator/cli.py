"""CLI entry point for sbom-validator."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import click

from sbom_validator import __version__
from sbom_validator.logging_config import configure_logging
from sbom_validator.models import IssueCategory, ValidationIssue, ValidationResult, ValidationStatus
from sbom_validator.presentation import humanize_field_path, humanize_message
from sbom_validator.report_writer import write_reports
from sbom_validator.validator import validate

logger = logging.getLogger(__name__)


def _result_to_dict(result: ValidationResult) -> dict[str, Any]:
    """Serialise a ValidationResult to a JSON-compatible dict."""
    return {
        "tool_version": __version__,
        "status": result.status.value,
        "file": result.file_path,
        "format_detected": result.format_detected,
        "issues": [
            {
                "severity": issue.severity.value,
                "category": issue.category.value,
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


_CATEGORY_LABELS: dict[str, str] = {
    IssueCategory.SCHEMA: "Schema Issues",
    IssueCategory.NTIA: "NTIA Compliance Issues",
    IssueCategory.FORMAT: "Format / Detection Errors",
}

_CATEGORY_ORDER: list[str] = [IssueCategory.FORMAT, IssueCategory.SCHEMA, IssueCategory.NTIA]


def _render_text(result: ValidationResult) -> str:
    """Render a human-readable text report.

    Rule IDs are intentionally omitted from text output to reduce
    implementation-detail noise for end users. Issues are grouped by category.
    """
    lines: list[str] = []
    status_label = result.status.value  # "PASS", "FAIL", "ERROR"
    lines.append(f"Status:  {status_label}")
    lines.append(f"File:    {result.file_path}")
    if result.format_detected:
        lines.append(f"Format:  {result.format_detected}")
    if result.issues:
        lines.append(f"Issues:  {len(result.issues)}")
        grouped: dict[str, list[ValidationIssue]] = {}
        for issue in result.issues:
            grouped.setdefault(issue.category.value, []).append(issue)
        for cat in _CATEGORY_ORDER:
            cat_issues = grouped.get(cat, [])
            if not cat_issues:
                continue
            label = _CATEGORY_LABELS.get(cat, cat)
            lines.append(f"\n{label} ({len(cat_issues)})")
            for issue in cat_issues:
                lines.append(
                    f"  [{issue.severity.value}] {humanize_field_path(issue.field_path)}: "
                    f"{humanize_message(issue.message)}"
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
@click.option(
    "--log-level",
    default="WARNING",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Set logging verbosity (default: WARNING).",
)
@click.option(
    "--report-dir",
    "report_dir",
    default=None,
    type=click.Path(file_okay=False, writable=True, path_type=Path),
    help="Directory to write HTML and JSON reports into.",
)
def validate_cmd(file: str, output_format: str, log_level: str, report_dir: Path | None) -> None:
    """Validate an SBOM FILE against schema and NTIA minimum elements.

    Exits with code 0 (PASS), 1 (validation FAIL), or 2 (tool ERROR).
    """
    configure_logging(log_level)
    logger.info("sbom-validator %s", __version__)
    file_path = Path(file)
    result = validate(file_path)

    if output_format == "json":
        click.echo(json.dumps(_result_to_dict(result), indent=2))
    else:
        click.echo(_render_text(result))

    if report_dir is not None:
        try:
            write_reports(result, report_dir)
        except OSError as exc:
            click.echo(f"Warning: could not write reports to {report_dir}: {exc}", err=True)

    sys.exit(_exit_code(result))


if __name__ == "__main__":
    main()

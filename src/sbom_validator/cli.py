"""CLI entry point for sbom-validator."""

from __future__ import annotations

import click

from sbom_validator import __version__


@click.group()
@click.version_option(version=__version__, prog_name="sbom-validator")
def main() -> None:
    """Validate SBOM files against schema and NTIA minimum elements."""


@main.command()
@click.argument("file", type=click.Path(exists=False))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (text or json).",
)
def validate(file: str, output_format: str) -> None:
    """Validate an SBOM file.

    FILE is the path to the SBOM JSON file to validate.
    """
    # TODO: implement in Phase 3
    click.echo(f"Validating {file} (not yet implemented)")

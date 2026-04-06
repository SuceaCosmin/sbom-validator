"""Parser for CycloneDX 1.6 JSON SBOM files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sbom_validator.exceptions import ParseError
from sbom_validator.models import (
    NormalizedComponent,
    NormalizedRelationship,
    NormalizedSBOM,
)


def _extract_author(metadata: dict[str, Any]) -> str | None:
    """Extract the author string from a CycloneDX metadata object.

    Priority:
      1. metadata.authors — join all non-empty name fields with ", "
      2. metadata.manufacture.name
      3. None
    """
    authors: list[dict[str, Any]] = metadata.get("authors", [])
    if authors:
        names = [entry.get("name", "") for entry in authors if entry.get("name")]
        if names:
            return ", ".join(names)

    manufacture: dict[str, Any] = metadata.get("manufacture", {})
    manufacture_name: str | None = manufacture.get("name") or None
    return manufacture_name


def _parse_component(component: dict[str, Any], index: int) -> NormalizedComponent:
    """Map a single CycloneDX component dict to a NormalizedComponent."""
    name: str = component.get("name", "")
    version: str | None = component.get("version") or None

    bom_ref: str | None = component.get("bom-ref")
    if bom_ref:
        component_id = bom_ref
    else:
        component_id = f"{name}@{version if version is not None else 'unknown'}"

    supplier_obj: dict[str, Any] = component.get("supplier", {})
    supplier: str | None = supplier_obj.get("name") or None

    identifiers: list[str] = []
    purl: str | None = component.get("purl")
    if purl:
        identifiers.append(purl)
    cpe: str | None = component.get("cpe")
    if cpe:
        identifiers.append(cpe)

    return NormalizedComponent(
        component_id=component_id,
        name=name or None,  # type: ignore[arg-type]
        version=version,
        supplier=supplier,
        identifiers=tuple(identifiers),
    )


def _parse_relationships(
    dependencies: list[dict[str, Any]],
) -> tuple[NormalizedRelationship, ...]:
    """Expand CycloneDX dependencies array into NormalizedRelationship objects."""
    relationships: list[NormalizedRelationship] = []
    for dep in dependencies:
        ref: str = dep["ref"]
        for dep_id in dep.get("dependsOn", []):
            relationships.append(
                NormalizedRelationship(
                    from_id=ref,
                    to_id=dep_id,
                    relationship_type="DEPENDS_ON",
                )
            )
    return tuple(relationships)


def parse_cyclonedx(file_path: Path) -> NormalizedSBOM:
    """Parse a CycloneDX 1.6 JSON file into a NormalizedSBOM.

    Raises:
        ParseError: If the file cannot be read or parsed.
    """
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ParseError(f"Cannot read file '{file_path}': {e}") from e

    if not raw_text.strip():
        raise ParseError(f"File '{file_path}' is empty.")

    try:
        document: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ParseError(f"Invalid JSON in '{file_path}': {e}") from e

    metadata: dict[str, Any] = document.get("metadata", {})

    author: str | None = _extract_author(metadata)
    timestamp: str | None = metadata.get("timestamp") or None

    raw_components: list[dict[str, Any]] = document.get("components", [])
    components = tuple(_parse_component(comp, idx) for idx, comp in enumerate(raw_components))

    raw_dependencies: list[dict[str, Any]] = document.get("dependencies", [])
    relationships = _parse_relationships(raw_dependencies)

    return NormalizedSBOM(
        format="cyclonedx",
        author=author,
        timestamp=timestamp,
        components=components,
        relationships=relationships,
    )

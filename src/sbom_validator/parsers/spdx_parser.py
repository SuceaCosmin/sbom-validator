"""Parser for SPDX 2.3 JSON SBOM files.

Exports:
  parse_spdx(file_path)          -- public entry point for JSON files
  _parse_spdx_document(doc, lbl) -- shared core used by YAML and TV parsers
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sbom_validator.exceptions import ParseError
from sbom_validator.models import NormalizedComponent, NormalizedRelationship, NormalizedSBOM

# Relationship types that indicate a dependency and should be included.
_QUALIFYING_RELATIONSHIP_TYPES: frozenset[str] = frozenset(
    {
        "DEPENDS_ON",
        "DEPENDENCY_OF",
        "DYNAMIC_LINK",
        "STATIC_LINK",
        "RUNTIME_DEPENDENCY_OF",
        "DEV_DEPENDENCY_OF",
        "OPTIONAL_DEPENDENCY_OF",
    }
)

# External reference categories whose locators are collected as identifiers.
_IDENTIFIER_CATEGORIES: frozenset[str] = frozenset({"PACKAGE-MANAGER", "SECURITY"})

# Prefixes stripped from creator, supplier, and originator fields.
_STRIP_PREFIXES: tuple[str, ...] = ("Organization: ", "Tool: ")


def _strip_spdx_prefix(value: str) -> str:
    """Strip a known SPDX actor prefix from *value* and return the bare name."""
    for prefix in _STRIP_PREFIXES:
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def _parse_author(creation_info: dict[str, Any]) -> str | None:
    """Derive the author string from *creation_info*.

    Collects all entries from ``creators`` that start with ``"Tool: "`` or
    ``"Organization: "``, strips the prefix, and joins them with ``", "``.
    Returns ``None`` when no matching entries are found.
    """
    creators: list[str] = creation_info.get("creators", [])
    parts: list[str] = []
    for creator in creators:
        for prefix in _STRIP_PREFIXES:
            if creator.startswith(prefix):
                parts.append(creator[len(prefix) :])
                break
    return ", ".join(parts) if parts else None


def _parse_component(package: dict[str, Any]) -> NormalizedComponent:
    """Map a single SPDX *package* dict to a :class:`NormalizedComponent`."""
    component_id: str = package["SPDXID"]
    name: str = package["name"]

    raw_version: str | None = package.get("versionInfo")
    version: str | None = (
        None
        if (raw_version is None or raw_version == "" or raw_version == "NOASSERTION")
        else raw_version
    )

    raw_supplier: str | None = package.get("supplier")
    if raw_supplier is None or raw_supplier == "" or raw_supplier == "NOASSERTION":
        supplier: str | None = None
    else:
        supplier = _strip_spdx_prefix(raw_supplier)

    external_refs: list[dict[str, Any]] = package.get("externalRefs", [])
    identifiers: tuple[str, ...] = tuple(
        ref["referenceLocator"]
        for ref in external_refs
        if ref.get("referenceCategory") in _IDENTIFIER_CATEGORIES
    )

    return NormalizedComponent(
        component_id=component_id,
        name=name,
        version=version,
        supplier=supplier,
        identifiers=identifiers,
    )


def _parse_relationship(rel: dict[str, Any]) -> NormalizedRelationship:
    """Map a single SPDX *relationship* dict to a :class:`NormalizedRelationship`."""
    return NormalizedRelationship(
        from_id=rel["spdxElementId"],
        to_id=rel["relatedSpdxElement"],
        relationship_type=rel["relationshipType"],
    )


def _parse_spdx_document(document: dict[str, Any], source_label: str) -> NormalizedSBOM:
    """Parse a loaded SPDX 2.3 document dict into a NormalizedSBOM.

    This is the shared core used by both the JSON parser (parse_spdx) and the
    YAML parser (parse_spdx_yaml). The caller is responsible for loading the
    raw document from disk and passing an appropriate source_label for error
    messages.

    Args:
        document: A dict representing the parsed SPDX document (JSON or YAML).
        source_label: Human-readable identifier used in ParseError messages
            (typically the file path as a string).

    Returns:
        NormalizedSBOM with format set by the caller's wrapper function.

    Raises:
        ParseError: If required fields are missing or malformed.
    """
    try:
        creation_info: dict[str, Any] = document.get("creationInfo", {})

        # author
        author: str | None = _parse_author(creation_info)

        # timestamp
        raw_ts: str | None = creation_info.get("created")
        timestamp: str | None = raw_ts if raw_ts else None

        # components — exclude the document pseudo-package
        raw_packages: list[dict[str, Any]] = document.get("packages", [])
        components: tuple[NormalizedComponent, ...] = tuple(
            _parse_component(pkg) for pkg in raw_packages if pkg.get("SPDXID") != "SPDXRef-DOCUMENT"
        )

        # relationships — keep only qualifying types
        raw_relationships: list[dict[str, Any]] = document.get("relationships", [])
        relationships: tuple[NormalizedRelationship, ...] = tuple(
            _parse_relationship(rel)
            for rel in raw_relationships
            if rel.get("relationshipType") in _QUALIFYING_RELATIONSHIP_TYPES
        )

    except KeyError as e:
        raise ParseError(f"SPDX file '{source_label}' is missing required field: {e}") from e

    return NormalizedSBOM(
        format="spdx",
        author=author,
        timestamp=timestamp,
        components=components,
        relationships=relationships,
    )


def parse_spdx(file_path: Path) -> NormalizedSBOM:
    """Parse an SPDX 2.3 JSON file into a NormalizedSBOM.

    Raises:
        ParseError: If the file cannot be read or parsed.
    """
    # --- Read file -----------------------------------------------------------
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ParseError(f"Cannot read SPDX file '{file_path}': {e}") from e

    # --- Decode JSON ---------------------------------------------------------
    if not raw_text.strip():
        raise ParseError(f"SPDX file '{file_path}' is empty.")

    try:
        document: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ParseError(f"SPDX file '{file_path}' contains invalid JSON: {e}") from e

    return _parse_spdx_document(document, str(file_path))

"""Parser for SPDX 2.3 Tag-Value SBOM files.

Tag-Value format is a line-oriented text format where each line has the form:
    <Tag>: <Value>

This parser extracts only the NTIA-relevant fields. Multi-line continuation
values (lines starting with whitespace) are intentionally ignored because no
NTIA element maps to a multi-line TV field.

Parsed fields:
  Document level:
    Creator: Tool: <name>          -> NormalizedSBOM.author (accumulated)
    Creator: Organization: <name>  -> NormalizedSBOM.author (accumulated)
    Created: <iso8601>             -> NormalizedSBOM.timestamp

  Per package (block restarted on each new PackageName: line):
    PackageName: <name>            -> NormalizedComponent.name
    SPDXID: <id>                   -> NormalizedComponent.component_id
    PackageVersion: <ver>          -> NormalizedComponent.version
    PackageSupplier: <value>       -> NormalizedComponent.supplier
    ExternalRef: PACKAGE-MANAGER purl <locator>   -> identifiers
    ExternalRef: SECURITY cpe23Type <locator>      -> identifiers

  Relationships:
    Relationship: <from> <type> <to>  -> NormalizedRelationship (qualifying types only)
"""

from __future__ import annotations

import logging
from pathlib import Path

from sbom_validator.constants import SPDX_SUPPORTED_VERSION
from sbom_validator.exceptions import ParseError
from sbom_validator.models import NormalizedComponent, NormalizedRelationship, NormalizedSBOM

logger = logging.getLogger(__name__)

# Qualifying relationship types (same set as spdx_parser.py).
# DEPENDENCY_OF is the inverse of DEPENDS_ON and must be included to avoid
# false-positive FR-08 failures when producers use the inverse form (#11/#12).
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

# Prefixes stripped from PackageSupplier and Creator fields
_STRIP_PREFIXES: tuple[str, ...] = ("Organization: ", "Tool: ")

# External reference categories collected as identifiers
_IDENTIFIER_CATEGORIES: frozenset[str] = frozenset({"PACKAGE-MANAGER", "SECURITY"})


def _strip_spdx_prefix(value: str) -> str | None:
    """Strip Organization:/Tool: prefix; return None for NOASSERTION or empty."""
    value = value.strip()
    if not value or value == "NOASSERTION":
        return None
    for prefix in _STRIP_PREFIXES:
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def _normalize_value(value: str) -> str | None:
    """Return None for empty strings and NOASSERTION; otherwise return stripped value."""
    v = value.strip()
    if not v or v == "NOASSERTION":
        return None
    return v


def parse_spdx_tv(file_path: Path) -> NormalizedSBOM:
    """Parse an SPDX 2.3 Tag-Value file into a NormalizedSBOM.

    Raises:
        ParseError: If the file cannot be read, is empty, has a wrong SPDX
            version, or contains a package block without a required SPDXID.
    """
    logger.debug("Parsing SPDX Tag-Value file: %s", file_path)

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ParseError(f"Cannot read SPDX Tag-Value file '{file_path}': {e}") from e

    content = raw_text.lstrip("\ufeff")  # strip optional BOM
    if not content.strip():
        raise ParseError(f"SPDX Tag-Value file '{file_path}' is empty.")

    # ── Document-level state ───────────────────────────────────────────────
    author_parts: list[str] = []
    timestamp: str | None = None

    # ── Package-block state ────────────────────────────────────────────────
    # A new package block begins when we encounter a PackageName: line.
    # We accumulate fields for the current block and flush when we see the
    # next PackageName: or end-of-file.
    current_name: str | None = None
    current_id: str | None = None
    current_version: str | None = None
    current_supplier: str | None = None
    current_identifiers: list[str] = []

    components: list[NormalizedComponent] = []
    relationships: list[NormalizedRelationship] = []

    def _flush_package() -> None:
        """Flush the current package block into components list."""
        nonlocal current_name, current_id, current_version, current_supplier
        if current_name is None:
            return  # no package to flush
        if current_id is None:
            raise ParseError(
                f"SPDX Tag-Value file '{file_path}': package '{current_name}' "
                "is missing its SPDXID field."
            )
        components.append(
            NormalizedComponent(
                component_id=current_id,
                name=current_name,
                version=current_version,
                supplier=current_supplier,
                identifiers=tuple(current_identifiers),
            )
        )
        current_name = None
        current_id = None
        current_version = None
        current_supplier = None
        current_identifiers.clear()

    for raw_line in content.splitlines():
        line = raw_line.strip()

        # Skip blank lines and comment lines
        if not line or line.startswith("#"):
            continue

        # Skip continuation lines (multi-line values) — not needed for NTIA
        if raw_line and raw_line[0] in (" ", "\t"):
            continue

        # Split on first ": " separator
        if ": " not in line and not line.endswith(":"):
            continue
        if ": " in line:
            tag, _, value = line.partition(": ")
        else:
            tag = line.rstrip(":")
            value = ""

        tag = tag.strip()
        value = value.strip()

        # ── Document-level fields ──────────────────────────────────────────
        if tag == "SPDXVersion":
            if value != SPDX_SUPPORTED_VERSION:
                raise ParseError(
                    f"SPDX Tag-Value file '{file_path}' has unsupported version "
                    f"{value!r}. Only {SPDX_SUPPORTED_VERSION} is supported."
                )
            continue

        if tag == "Creator":
            for prefix in _STRIP_PREFIXES:
                if value.startswith(prefix):
                    author_parts.append(value[len(prefix) :])
                    break
            continue

        if tag == "Created":
            timestamp = value if value else None
            continue

        # ── Package-level fields ───────────────────────────────────────────
        if tag == "PackageName":
            _flush_package()  # flush any previous package block
            current_name = value
            continue

        if tag == "SPDXID" and current_name is not None:
            # Only capture SPDXID when inside a package block
            current_id = value
            continue

        if tag == "PackageVersion":
            current_version = _normalize_value(value)
            continue

        if tag == "PackageSupplier":
            current_supplier = _strip_spdx_prefix(value)
            continue

        if tag == "ExternalRef":
            # Format: <category> <type> <locator>
            parts = value.split(None, 2)
            if len(parts) == 3:
                category, _ref_type, locator = parts
                if category in _IDENTIFIER_CATEGORIES:
                    current_identifiers.append(locator)
            continue

        # ── Relationships ──────────────────────────────────────────────────
        if tag == "Relationship":
            parts = value.split(None, 2)
            if len(parts) == 3:
                from_id, rel_type, to_id = parts
                if rel_type in _QUALIFYING_RELATIONSHIP_TYPES:
                    relationships.append(
                        NormalizedRelationship(
                            from_id=from_id,
                            to_id=to_id,
                            relationship_type=rel_type,
                        )
                    )
            continue

    # Flush the last package block
    _flush_package()

    author: str | None = ", ".join(author_parts) if author_parts else None

    logger.debug(
        "SPDX TV parsed: %d components, %d relationships",
        len(components),
        len(relationships),
    )

    return NormalizedSBOM(
        format="spdx-tv",
        author=author,
        timestamp=timestamp,
        components=tuple(components),
        relationships=tuple(relationships),
    )

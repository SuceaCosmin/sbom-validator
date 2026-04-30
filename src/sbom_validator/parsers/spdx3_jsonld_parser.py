"""Parser for SPDX 3.x JSON-LD SBOM files.

SPDX 3.x uses a JSON-LD document with a flat ``@graph`` array rather than
nested keys.  The graph is a bag of typed elements — SpdxDocument, software_Package,
Relationship, Organization, tool_Tool, etc. — linked by ``spdxId`` cross-references.

The parser performs two passes over the graph:
  Pass 1: build a spdxId → element dict index for O(1) cross-reference lookups.
  Pass 2: extract SpdxDocument metadata, packages, and DEPENDS_ON relationships.

Public API:
  parse_spdx3_jsonld(file_path) -> NormalizedSBOM
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sbom_validator.constants import FORMAT_SPDX3_JSONLD
from sbom_validator.exceptions import ParseError
from sbom_validator.models import NormalizedComponent, NormalizedRelationship, NormalizedSBOM

logger = logging.getLogger(__name__)

# Only DEPENDS_ON relationships are included; DESCRIBES and others are excluded.
# SPDX 3.x uses a single DEPENDS_ON type for package dependencies (unlike the
# richer set in SPDX 2.3 which required a broader frozenset).
_QUALIFYING_RELATIONSHIP_TYPE = "DEPENDS_ON"

# SPDX 3.x package type discriminator in the @graph.
_PACKAGE_TYPE = "software_Package"

# SPDX 3.x document element type discriminator.
_DOCUMENT_TYPE = "SpdxDocument"

# SPDX 3.x relationship element type discriminator.
_RELATIONSHIP_TYPE = "Relationship"


# ---------------------------------------------------------------------------
# Pass 1 — index builder
# ---------------------------------------------------------------------------


def _build_graph_index(graph: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build a spdxId → element mapping for fast cross-reference lookups.

    Elements without a ``spdxId`` field are skipped — they cannot be resolved
    by reference and would only pollute the index with None keys.
    """
    index: dict[str, dict[str, Any]] = {}
    for element in graph:
        element_id: str | None = element.get("spdxId")
        if element_id is not None:
            index[element_id] = element
    return index


# ---------------------------------------------------------------------------
# Pass 2 helpers
# ---------------------------------------------------------------------------


def _find_spdx_document(
    graph: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the first SpdxDocument element in *graph*.

    Raises:
        ParseError: When no SpdxDocument element is found.
    """
    spdx_documents = [el for el in graph if el.get("type") == _DOCUMENT_TYPE]

    if not spdx_documents:
        raise ParseError("No SpdxDocument element found in @graph")

    if len(spdx_documents) > 1:
        # Spec says exactly one per document; warn and continue with first.
        logger.warning(
            "Found %d SpdxDocument elements in @graph; using the first one.",
            len(spdx_documents),
        )

    return spdx_documents[0]


def _resolve_name(spdx_id: str, index: dict[str, dict[str, Any]]) -> str | None:
    """Look up *spdx_id* in *index* and return its ``name`` field, or None.

    Missing cross-references (spdx_id not in index) or elements with no name
    are silently ignored — the caller decides what to do with None.
    """
    element = index.get(spdx_id)
    if element is None:
        return None
    return element.get("name")


def _parse_author(
    doc_element: dict[str, Any],
    index: dict[str, dict[str, Any]],
) -> str | None:
    """Resolve createdBy spdxId references to their element names.

    Each entry in ``creationInfo.createdBy`` is an spdxId pointing to a
    tool_Tool, Organization, or Person element.  We resolve each one and
    join the non-None results with ``", "``.

    Returns None when createdBy is empty or all references are dangling.
    """
    creation_info: dict[str, Any] = doc_element.get("creationInfo", {})
    created_by_refs: list[str] = creation_info.get("createdBy", [])

    resolved_names = [_resolve_name(ref, index) for ref in created_by_refs]
    non_none_names = [name for name in resolved_names if name is not None]

    return ", ".join(non_none_names) if non_none_names else None


def _parse_timestamp(doc_element: dict[str, Any]) -> str | None:
    """Extract creationInfo.created as a verbatim string, or None if absent."""
    creation_info: dict[str, Any] = doc_element.get("creationInfo", {})
    return creation_info.get("created")


def _resolve_supplier(
    element: dict[str, Any],
    index: dict[str, dict[str, Any]],
) -> str | None:
    """Resolve the first suppliedBy spdxId reference to the supplier's name.

    ``suppliedBy`` is a list; only the first entry is used (NTIA requires a
    supplier to exist, not necessarily multiple).  Returns None if the list is
    empty or the reference cannot be resolved.
    """
    supplied_by_refs: list[str] = element.get("suppliedBy", [])
    if not supplied_by_refs:
        return None

    first_ref = supplied_by_refs[0]
    return _resolve_name(first_ref, index)


def _parse_components(
    graph: list[dict[str, Any]],
    index: dict[str, dict[str, Any]],
) -> tuple[NormalizedComponent, ...]:
    """Extract all software_Package elements as NormalizedComponent instances.

    Packages are identified by ``type == "software_Package"``.  The supplier
    is resolved via cross-reference through the index.
    """
    components: list[NormalizedComponent] = []

    for element in graph:
        element_type: str = element.get("type", "")
        if element_type != _PACKAGE_TYPE:
            continue

        component_id: str = element.get("spdxId", "")
        name: str = element.get("name", "")
        version: str | None = element.get("packageVersion")
        supplier: str | None = _resolve_supplier(element, index)

        components.append(
            NormalizedComponent(
                component_id=component_id,
                name=name,
                version=version,
                supplier=supplier,
            )
        )

    return tuple(components)


def _parse_relationships(graph: list[dict[str, Any]]) -> tuple[NormalizedRelationship, ...]:
    """Extract DEPENDS_ON Relationship elements as NormalizedRelationship instances.

    Only elements with ``type == "Relationship"`` and
    ``relationshipType == "DEPENDS_ON"`` are included; DESCRIBES and all other
    relationship types are excluded per FR-08.

    The ``to`` field is a list; only the first entry is mapped to ``to_id``.
    Relationships where ``from`` or ``to`` cannot be determined are skipped.
    """
    relationships: list[NormalizedRelationship] = []

    for element in graph:
        if element.get("type") != _RELATIONSHIP_TYPE:
            continue
        if element.get("relationshipType") != _QUALIFYING_RELATIONSHIP_TYPE:
            continue

        from_id: str | None = element.get("from")
        to_list: list[str] = element.get("to", [])
        to_id: str | None = to_list[0] if to_list else None

        # Skip malformed relationships with no from or to endpoint.
        if from_id is None or to_id is None:
            continue

        relationships.append(
            NormalizedRelationship(
                from_id=from_id,
                to_id=to_id,
                relationship_type=_QUALIFYING_RELATIONSHIP_TYPE,
            )
        )

    return tuple(relationships)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_spdx3_jsonld(file_path: Path) -> NormalizedSBOM:
    """Parse an SPDX 3.x JSON-LD file into a NormalizedSBOM.

    The SPDX 3.x format uses a JSON-LD ``@graph`` array where every element is
    a typed node linked by ``spdxId`` cross-references.  This function performs
    two passes: first building a spdxId index, then extracting structured data.

    Args:
        file_path: Path to the ``.spdx3.jsonld`` file.

    Returns:
        NormalizedSBOM with ``format == FORMAT_SPDX3_JSONLD``.

    Raises:
        ParseError: If the file cannot be read, contains invalid JSON, has an
            empty or missing ``@graph``, or contains no SpdxDocument element.
    """
    # --- Read file -----------------------------------------------------------
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ParseError(f"Cannot read SPDX 3.x file '{file_path}': {e}") from e

    # --- Decode JSON ---------------------------------------------------------
    if not raw_text.strip():
        raise ParseError(f"SPDX 3.x file '{file_path}' is empty.")

    try:
        document: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ParseError(f"SPDX 3.x file '{file_path}' contains invalid JSON: {e}") from e

    # --- Extract @graph -------------------------------------------------------
    graph: list[dict[str, Any]] = document.get("@graph", [])
    if not graph:
        raise ParseError(f"No elements found in @graph of '{file_path}'")

    # --- Pass 1: build spdxId index ------------------------------------------
    index = _build_graph_index(graph)

    # --- Pass 2: find SpdxDocument and extract metadata ----------------------
    doc_element = _find_spdx_document(graph)

    author = _parse_author(doc_element, index)
    timestamp = _parse_timestamp(doc_element)
    components = _parse_components(graph, index)
    relationships = _parse_relationships(graph)

    return NormalizedSBOM(
        format=FORMAT_SPDX3_JSONLD,
        author=author,
        timestamp=timestamp,
        components=components,
        relationships=relationships,
    )

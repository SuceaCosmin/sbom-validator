"""TDD unit tests for the SPDX 3.x JSON-LD parser (Task 3.F1).

These tests are written BEFORE the parser is implemented and are expected to
FAIL with ImportError until the developer implements parse_spdx3_jsonld() in
sbom_validator/parsers/spdx3_jsonld_parser.py.

References:
  - FR-04  supplier (NTIA)
  - FR-05  component name (NTIA)
  - FR-06  component version (NTIA)
  - FR-08  dependency relationships (NTIA)
  - FR-09  author (NTIA)
  - FR-10  timestamp (NTIA)
  - FR-15  SPDX 3.x schema validation
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sbom_validator.exceptions import ParseError
from sbom_validator.models import NormalizedComponent, NormalizedRelationship, NormalizedSBOM
from sbom_validator.parsers.spdx3_jsonld_parser import parse_spdx3_jsonld

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_CONTEXT_URL = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"

_FIXTURES_PATH = Path("tests/fixtures/spdx")


def _make_minimal_graph(
    *,
    extra_elements: list[dict[str, Any]] | None = None,
    created_by: list[str] | None = None,
) -> dict[str, Any]:
    """Return a minimal valid SPDX 3.x JSON-LD document dict.

    Args:
        extra_elements: Additional @graph elements appended after the SpdxDocument.
        created_by: Override for creationInfo.createdBy (defaults to empty list).
    """
    doc: dict[str, Any] = {
        "@context": _CONTEXT_URL,
        "@graph": [
            {
                "type": "SpdxDocument",
                "spdxId": "https://example.org/doc/test",
                "creationInfo": {
                    "specVersion": "3.0.1",
                    "created": "2024-06-01T00:00:00Z",
                    "createdBy": created_by if created_by is not None else [],
                },
                "name": "test-document",
            }
        ],
    }
    if extra_elements:
        doc["@graph"].extend(extra_elements)
    return doc


# ---------------------------------------------------------------------------
# TestParseSpdx3JsonldHappyPath — valid full document from fixture
# ---------------------------------------------------------------------------


class TestParseSpdx3JsonldHappyPath:
    """Full happy-path tests using the valid-full.spdx3.jsonld fixture.

    valid-full.spdx3.jsonld contains:
      - SpdxDocument with createdBy pointing to a tool_Tool element
      - One tool_Tool element (sbom-generator-3.0)
      - Two software_Package elements:
          requests 2.28.0 (suppliedBy pointing to an Organization)
          urllib3 1.26.14 (suppliedBy: Python Software Foundation)
      - One Organization element (Python Software Foundation)
      - One DEPENDS_ON Relationship (requests → urllib3)
      - One DESCRIBES Relationship (doc → requests, must be excluded)
    """

    def test_returns_normalized_sbom_instance(self) -> None:
        """parse_spdx3_jsonld must return a NormalizedSBOM instance (FR-09, FR-10)."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        assert isinstance(result, NormalizedSBOM)

    def test_format_is_spdx3_jsonld(self) -> None:
        """The format field must be the literal string 'spdx3-jsonld'."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        assert result.format == "spdx3-jsonld"

    def test_author_resolved_from_created_by(self) -> None:
        """createdBy spdxId refs must resolve to the element name (FR-09).

        The fixture's createdBy points to a tool_Tool with name 'sbom-generator-3.0'.
        The resulting author must be 'sbom-generator-3.0'.
        """
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        assert result.author == "sbom-generator-3.0"

    def test_timestamp_extracted(self) -> None:
        """creationInfo.created must be mapped to result.timestamp as-is (FR-10)."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        assert result.timestamp == "2024-01-15T10:00:00Z"

    def test_two_components_parsed(self) -> None:
        """Both software_Package elements must appear in result.components (FR-05)."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        assert len(result.components) == 2

    def test_component_names_mapped(self) -> None:
        """software_Package.name must map to NormalizedComponent.name (FR-05)."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        names = {c.name for c in result.components}
        assert names == {"requests", "urllib3"}

    def test_component_version_mapped(self) -> None:
        """software_Package.packageVersion must map to NormalizedComponent.version (FR-06)."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        requests_pkg = next(c for c in result.components if c.name == "requests")
        assert requests_pkg.version == "2.28.0"

    def test_component_id_is_spdxid(self) -> None:
        """software_Package.spdxId must map to NormalizedComponent.component_id."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        component_ids = {c.component_id for c in result.components}
        assert "https://example.org/pkg/requests" in component_ids
        assert "https://example.org/pkg/urllib3" in component_ids

    def test_supplier_resolved_via_cross_reference(self) -> None:
        """suppliedBy spdxId must resolve to Organization.name (FR-04).

        requests.suppliedBy points to Organization spdxId='https://example.org/org/psf'
        whose name is 'Python Software Foundation'.
        """
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        requests_pkg = next(c for c in result.components if c.name == "requests")
        assert requests_pkg.supplier == "Python Software Foundation"

    def test_package_without_supplied_by_has_none_supplier(self, tmp_path: Path) -> None:
        """A software_Package without suppliedBy must have supplier == None (FR-04)."""
        doc = {
            "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
            "@graph": [
                {
                    "type": "SpdxDocument",
                    "spdxId": "https://example.org/doc/test",
                    "creationInfo": {
                        "specVersion": "3.0.1",
                        "created": "2024-01-01T00:00:00Z",
                        "createdBy": [],
                    },
                },
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/no-supplier",
                    "name": "no-supplier-pkg",
                    "packageVersion": "1.0.0",
                },
            ],
        }
        fixture = tmp_path / "no-supplier.jsonld"
        fixture.write_text(__import__("json").dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(fixture)
        assert result.components[0].supplier is None

    def test_one_depends_on_relationship(self) -> None:
        """Only the DEPENDS_ON relationship must appear; DESCRIBES is excluded (FR-08)."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        assert len(result.relationships) == 1

    def test_relationship_from_and_to_mapped(self) -> None:
        """Relationship.from and Relationship.to[0] must map to from_id and to_id (FR-08)."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        rel = result.relationships[0]
        assert rel.from_id == "https://example.org/pkg/requests"
        assert rel.to_id == "https://example.org/pkg/urllib3"

    def test_relationship_type_is_depends_on(self) -> None:
        """Relationship.relationshipType must be preserved in NormalizedRelationship."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        assert result.relationships[0].relationship_type == "DEPENDS_ON"

    def test_describes_relationship_excluded(self) -> None:
        """DESCRIBES relationships must NOT appear in result.relationships (FR-08)."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        rel_types = {r.relationship_type for r in result.relationships}
        assert "DESCRIBES" not in rel_types

    def test_components_is_tuple(self) -> None:
        """result.components must be a tuple (frozen dataclass contract)."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        assert isinstance(result.components, tuple)

    def test_relationships_is_tuple(self) -> None:
        """result.relationships must be a tuple (frozen dataclass contract)."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        assert isinstance(result.relationships, tuple)

    def test_each_component_is_normalized_component_instance(self) -> None:
        """Each entry in result.components must be a NormalizedComponent instance."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        for component in result.components:
            assert isinstance(component, NormalizedComponent)

    def test_each_relationship_is_normalized_relationship_instance(self) -> None:
        """Each entry in result.relationships must be a NormalizedRelationship instance."""
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "valid-full.spdx3.jsonld")
        for rel in result.relationships:
            assert isinstance(rel, NormalizedRelationship)


# ---------------------------------------------------------------------------
# TestAuthorExtraction — createdBy cross-reference resolution
# ---------------------------------------------------------------------------


class TestAuthorExtraction:
    """Tests for createdBy → author resolution (FR-09)."""

    def test_created_by_tool_resolves_to_name(self, tmp_path: Path) -> None:
        """createdBy pointing to a tool_Tool element yields the tool name as author."""
        doc = _make_minimal_graph(
            created_by=["https://example.org/tool/gen"],
            extra_elements=[
                {
                    "type": "tool_Tool",
                    "spdxId": "https://example.org/tool/gen",
                    "name": "my-sbom-tool",
                }
            ],
        )
        f = tmp_path / "author-tool.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.author == "my-sbom-tool"

    def test_created_by_organization_resolves_to_name(self, tmp_path: Path) -> None:
        """createdBy pointing to an Organization element yields the org name as author."""
        doc = _make_minimal_graph(
            created_by=["https://example.org/org/acme"],
            extra_elements=[
                {
                    "type": "Organization",
                    "spdxId": "https://example.org/org/acme",
                    "name": "Acme Corp",
                }
            ],
        )
        f = tmp_path / "author-org.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.author == "Acme Corp"

    def test_multiple_created_by_joined_with_comma(self, tmp_path: Path) -> None:
        """Multiple createdBy refs must be resolved and joined with ', '."""
        doc = _make_minimal_graph(
            created_by=[
                "https://example.org/tool/gen",
                "https://example.org/org/acme",
            ],
            extra_elements=[
                {
                    "type": "tool_Tool",
                    "spdxId": "https://example.org/tool/gen",
                    "name": "my-sbom-tool",
                },
                {
                    "type": "Organization",
                    "spdxId": "https://example.org/org/acme",
                    "name": "Acme Corp",
                },
            ],
        )
        f = tmp_path / "author-multi.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.author is not None
        assert "my-sbom-tool" in result.author
        assert "Acme Corp" in result.author

    def test_empty_created_by_returns_none_author(self, tmp_path: Path) -> None:
        """An empty createdBy list must produce result.author == None (FR-09)."""
        doc = _make_minimal_graph(created_by=[])
        f = tmp_path / "author-empty.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.author is None

    def test_dangling_created_by_ref_returns_none(self, tmp_path: Path) -> None:
        """A createdBy spdxId not found in @graph must yield author == None (no exception).

        Missing refs must be silently ignored rather than raising ParseError.
        """
        doc = _make_minimal_graph(
            created_by=["https://example.org/tool/ghost"]
            # No element with that spdxId in @graph
        )
        f = tmp_path / "author-dangling.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.author is None


# ---------------------------------------------------------------------------
# TestTimestampExtraction — creationInfo.created mapping
# ---------------------------------------------------------------------------


class TestTimestampExtraction:
    """Tests for creationInfo.created → timestamp mapping (FR-10)."""

    def test_created_mapped_to_timestamp(self, tmp_path: Path) -> None:
        """creationInfo.created must appear verbatim in result.timestamp."""
        doc = _make_minimal_graph()
        f = tmp_path / "ts.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.timestamp == "2024-06-01T00:00:00Z"

    def test_missing_created_field_returns_none_timestamp(self, tmp_path: Path) -> None:
        """A SpdxDocument with no 'created' field must produce timestamp == None."""
        doc: dict[str, Any] = {
            "@context": _CONTEXT_URL,
            "@graph": [
                {
                    "type": "SpdxDocument",
                    "spdxId": "https://example.org/doc/test",
                    "creationInfo": {
                        "specVersion": "3.0.1",
                        "createdBy": [],
                        # 'created' deliberately absent
                    },
                    "name": "no-ts-doc",
                }
            ],
        }
        f = tmp_path / "no-ts.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.timestamp is None


# ---------------------------------------------------------------------------
# TestComponentParsing — software_Package → NormalizedComponent
# ---------------------------------------------------------------------------


class TestComponentParsing:
    """Tests for software_Package extraction (FR-05, FR-06, FR-04)."""

    def test_package_name_mapped(self, tmp_path: Path) -> None:
        """software_Package.name must map to NormalizedComponent.name (FR-05)."""
        doc = _make_minimal_graph(
            extra_elements=[
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/libfoo",
                    "name": "libfoo",
                    "packageVersion": "1.0.0",
                }
            ]
        )
        f = tmp_path / "pkg-name.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert len(result.components) == 1
        assert result.components[0].name == "libfoo"

    def test_package_version_mapped(self, tmp_path: Path) -> None:
        """software_Package.packageVersion must map to NormalizedComponent.version (FR-06)."""
        doc = _make_minimal_graph(
            extra_elements=[
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/libfoo",
                    "name": "libfoo",
                    "packageVersion": "3.7.2",
                }
            ]
        )
        f = tmp_path / "pkg-version.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.components[0].version == "3.7.2"

    def test_package_without_version_returns_none(self, tmp_path: Path) -> None:
        """A software_Package with no packageVersion must produce version == None (FR-06)."""
        doc = _make_minimal_graph(
            extra_elements=[
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/libfoo",
                    "name": "libfoo",
                    # packageVersion absent
                }
            ]
        )
        f = tmp_path / "pkg-no-version.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.components[0].version is None

    def test_package_spdxid_is_component_id(self, tmp_path: Path) -> None:
        """software_Package.spdxId must map to NormalizedComponent.component_id."""
        doc = _make_minimal_graph(
            extra_elements=[
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/libfoo",
                    "name": "libfoo",
                }
            ]
        )
        f = tmp_path / "pkg-id.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.components[0].component_id == "https://example.org/pkg/libfoo"

    def test_supplier_cross_reference_resolved(self, tmp_path: Path) -> None:
        """suppliedBy spdxId must resolve to the referenced element's name (FR-04)."""
        doc = _make_minimal_graph(
            extra_elements=[
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/libfoo",
                    "name": "libfoo",
                    "suppliedBy": ["https://example.org/org/acme"],
                },
                {
                    "type": "Organization",
                    "spdxId": "https://example.org/org/acme",
                    "name": "Acme Corp",
                },
            ]
        )
        f = tmp_path / "pkg-supplier.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.components[0].supplier == "Acme Corp"

    def test_dangling_supplied_by_ref_returns_none_supplier(self, tmp_path: Path) -> None:
        """A suppliedBy ref pointing to a missing spdxId must yield supplier == None.

        This must not raise ParseError (FR-04).
        """
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "missing-supplier.spdx3.jsonld")
        requests_pkg = next(c for c in result.components if c.name == "requests")
        assert requests_pkg.supplier is None

    def test_unicode_name_preserved(self, tmp_path: Path) -> None:
        """Unicode characters in package name must be preserved without modification."""
        doc = _make_minimal_graph(
            extra_elements=[
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/uni",
                    "name": "libfoo-éàü",
                    "packageVersion": "1.0",
                }
            ]
        )
        f = tmp_path / "pkg-unicode.spdx3.jsonld"
        f.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.components[0].name == "libfoo-éàü"

    def test_no_packages_returns_empty_components(self, tmp_path: Path) -> None:
        """A @graph with no software_Package elements must produce empty components tuple."""
        doc = _make_minimal_graph()  # Only SpdxDocument, no packages
        f = tmp_path / "no-pkgs.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.components == ()


# ---------------------------------------------------------------------------
# TestRelationshipParsing — Relationship → NormalizedRelationship
# ---------------------------------------------------------------------------


class TestRelationshipParsing:
    """Tests for DEPENDS_ON relationship extraction (FR-08)."""

    def test_no_relationships_returns_empty_tuple(self) -> None:
        """A document with no Relationship elements must yield relationships == () (FR-08).

        Uses the missing-relationships.spdx3.jsonld fixture.
        """
        result = parse_spdx3_jsonld(_FIXTURES_PATH / "missing-relationships.spdx3.jsonld")
        assert result.relationships == ()

    def test_only_describes_yields_empty_relationships(self, tmp_path: Path) -> None:
        """A document with only DESCRIBES relationships must yield relationships == () (FR-08)."""
        doc = _make_minimal_graph(
            extra_elements=[
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/foo",
                    "name": "foo",
                },
                {
                    "type": "Relationship",
                    "spdxId": "https://example.org/rel/1",
                    "from": "https://example.org/doc/test",
                    "to": ["https://example.org/pkg/foo"],
                    "relationshipType": "DESCRIBES",
                },
            ]
        )
        f = tmp_path / "describes-only.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.relationships == ()

    def test_depends_on_relationship_included(self, tmp_path: Path) -> None:
        """DEPENDS_ON relationships must appear in result.relationships (FR-08)."""
        doc = _make_minimal_graph(
            extra_elements=[
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/a",
                    "name": "pkg-a",
                },
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/b",
                    "name": "pkg-b",
                },
                {
                    "type": "Relationship",
                    "spdxId": "https://example.org/rel/dep",
                    "from": "https://example.org/pkg/a",
                    "to": ["https://example.org/pkg/b"],
                    "relationshipType": "DEPENDS_ON",
                },
            ]
        )
        f = tmp_path / "dep-rel.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert len(result.relationships) == 1
        assert result.relationships[0].from_id == "https://example.org/pkg/a"
        assert result.relationships[0].to_id == "https://example.org/pkg/b"
        assert result.relationships[0].relationship_type == "DEPENDS_ON"

    def test_relationship_to_uses_first_element(self, tmp_path: Path) -> None:
        """When Relationship.to has multiple entries, the first must map to to_id."""
        doc = _make_minimal_graph(
            extra_elements=[
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/a",
                    "name": "pkg-a",
                },
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/b",
                    "name": "pkg-b",
                },
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/c",
                    "name": "pkg-c",
                },
                {
                    "type": "Relationship",
                    "spdxId": "https://example.org/rel/multi",
                    "from": "https://example.org/pkg/a",
                    "to": [
                        "https://example.org/pkg/b",
                        "https://example.org/pkg/c",
                    ],
                    "relationshipType": "DEPENDS_ON",
                },
            ]
        )
        f = tmp_path / "multi-to.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        result = parse_spdx3_jsonld(f)
        assert result.relationships[0].to_id == "https://example.org/pkg/b"


# ---------------------------------------------------------------------------
# TestEdgeCases — structural / document-level edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Structural edge cases: empty graph, missing SpdxDocument, multiple SpdxDocuments."""

    def test_empty_graph_raises_parse_error(self, tmp_path: Path) -> None:
        """A document with '@graph': [] must raise ParseError (no SpdxDocument found)."""
        doc = {"@context": _CONTEXT_URL, "@graph": []}
        f = tmp_path / "empty-graph.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx3_jsonld(f)

    def test_no_spdx_document_element_raises_parse_error(self, tmp_path: Path) -> None:
        """A @graph with only software_Package but no SpdxDocument must raise ParseError."""
        doc = {
            "@context": _CONTEXT_URL,
            "@graph": [
                {
                    "type": "software_Package",
                    "spdxId": "https://example.org/pkg/only",
                    "name": "only-pkg",
                }
            ],
        }
        f = tmp_path / "no-spdx-doc.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx3_jsonld(f)

    def test_multiple_spdx_documents_uses_first_no_exception(self, tmp_path: Path) -> None:
        """Multiple SpdxDocument elements must not raise an exception; first is used."""
        doc = {
            "@context": _CONTEXT_URL,
            "@graph": [
                {
                    "type": "SpdxDocument",
                    "spdxId": "https://example.org/doc/first",
                    "creationInfo": {
                        "specVersion": "3.0.1",
                        "created": "2024-01-01T00:00:00Z",
                        "createdBy": [],
                    },
                    "name": "first-doc",
                },
                {
                    "type": "SpdxDocument",
                    "spdxId": "https://example.org/doc/second",
                    "creationInfo": {
                        "specVersion": "3.0.1",
                        "created": "2024-12-31T23:59:59Z",
                        "createdBy": [],
                    },
                    "name": "second-doc",
                },
            ],
        }
        f = tmp_path / "two-spdx-docs.spdx3.jsonld"
        f.write_text(json.dumps(doc), encoding="utf-8")
        # Must not raise — uses first SpdxDocument
        result = parse_spdx3_jsonld(f)
        assert isinstance(result, NormalizedSBOM)
        assert result.timestamp == "2024-01-01T00:00:00Z"

    def test_nonexistent_file_raises_parse_error(self, tmp_path: Path) -> None:
        """Passing a path to a file that does not exist must raise ParseError."""
        nonexistent = tmp_path / "does-not-exist.spdx3.jsonld"
        with pytest.raises(ParseError):
            parse_spdx3_jsonld(nonexistent)

    def test_invalid_json_raises_parse_error(self, tmp_path: Path) -> None:
        """A file containing invalid JSON must raise ParseError."""
        bad = tmp_path / "bad.spdx3.jsonld"
        bad.write_text("not valid json {{{", encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx3_jsonld(bad)

    def test_empty_file_raises_parse_error(self, tmp_path: Path) -> None:
        """An empty file must raise ParseError."""
        empty = tmp_path / "empty.spdx3.jsonld"
        empty.write_text("", encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx3_jsonld(empty)

    def test_parse_error_not_generic_exception(self, tmp_path: Path) -> None:
        """ParseError (not bare Exception or NotImplementedError) must be raised on bad input."""
        bad = tmp_path / "bad2.spdx3.jsonld"
        bad.write_text("{ bad json }", encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx3_jsonld(bad)

"""TDD unit tests for the SPDX 2.3 JSON parser (Task 2.B1).

These tests are written BEFORE the parser is implemented and are expected to
FAIL until the developer implements parse_spdx() in
sbom_validator/parsers/spdx_parser.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sbom_validator.exceptions import ParseError
from sbom_validator.models import NormalizedComponent, NormalizedRelationship, NormalizedSBOM
from sbom_validator.parsers.spdx_parser import parse_spdx

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def fixtures_path() -> Path:
    """Return the path to the SPDX fixture directory."""
    return Path("tests/fixtures/spdx")


# ---------------------------------------------------------------------------
# TestParseSpdxBasic — happy-path tests against valid-minimal.spdx.json
# ---------------------------------------------------------------------------


class TestParseSpdxBasic:
    """Basic parsing tests using the minimal valid SPDX fixture.

    valid-minimal.spdx.json contains:
      - creationInfo.created = "2024-01-15T10:00:00Z"
      - creationInfo.creators = ["Tool: sbom-generator-1.0", "Organization: AcmeCorp"]
      - packages: 1 entry (SPDXRef-Package-requests, name="requests",
          versionInfo="2.31.0", supplier="Organization: AcmeCorp",
          externalRefs=[PACKAGE-MANAGER purl pkg:pypi/requests@2.31.0])
      - relationships: 2 entries (DESCRIBES filtered out, DEPENDS_ON kept)
    """

    def test_returns_normalized_sbom_instance(self, fixtures_path: Path) -> None:
        """parse_spdx must return a NormalizedSBOM instance."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        assert isinstance(result, NormalizedSBOM)

    def test_format_is_spdx(self, fixtures_path: Path) -> None:
        """The format field must always be the literal string 'spdx'."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        assert result.format == "spdx"

    def test_author_extracted_from_creators(self, fixtures_path: Path) -> None:
        """Author is derived from creationInfo.creators entries with Tool:/Organization: prefix.

        The fixture has creators ["Tool: sbom-generator-1.0", "Organization: AcmeCorp"].
        Per the spec, all matching entries are stripped of their prefix and joined with ", ".
        The resulting author must contain "sbom-generator-1.0" (first matching entry).
        """
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        assert result.author is not None
        assert "sbom-generator-1.0" in result.author

    def test_author_strips_tool_prefix(self, fixtures_path: Path) -> None:
        """The 'Tool: ' prefix must be stripped from creator entries."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        assert result.author is not None
        # The raw prefix must not appear in the final author value
        assert "Tool: " not in result.author

    def test_timestamp_extracted(self, fixtures_path: Path) -> None:
        """creationInfo.created must be mapped to result.timestamp as-is."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        assert result.timestamp == "2024-01-15T10:00:00Z"

    def test_components_parsed(self, fixtures_path: Path) -> None:
        """At least one component must be present after parsing the minimal fixture."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        assert len(result.components) > 0

    def test_document_package_excluded(self, fixtures_path: Path) -> None:
        """The DOCUMENT pseudo-package (SPDXID=SPDXRef-DOCUMENT) must not appear in components.

        The minimal fixture does not include a package with SPDXID 'SPDXRef-DOCUMENT'
        in its packages array, but any implementation that treats the document root
        as a package must exclude it. We verify by checking component_ids.
        """
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        component_ids = [c.component_id for c in result.components]
        assert "SPDXRef-DOCUMENT" not in component_ids

    def test_component_id_mapped(self, fixtures_path: Path) -> None:
        """packages[*].SPDXID must map to NormalizedComponent.component_id."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        component_ids = [c.component_id for c in result.components]
        assert "SPDXRef-Package-requests" in component_ids

    def test_component_name_mapped(self, fixtures_path: Path) -> None:
        """packages[*].name must map to NormalizedComponent.name."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        requests_pkg = next(
            c for c in result.components if c.component_id == "SPDXRef-Package-requests"
        )
        assert requests_pkg.name == "requests"

    def test_component_version_mapped(self, fixtures_path: Path) -> None:
        """packages[*].versionInfo must map to NormalizedComponent.version."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        requests_pkg = next(
            c for c in result.components if c.component_id == "SPDXRef-Package-requests"
        )
        assert requests_pkg.version == "2.31.0"

    def test_component_supplier_mapped_strips_prefix(self, fixtures_path: Path) -> None:
        """'Organization: AcmeCorp' in supplier must be stripped to 'AcmeCorp'."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        requests_pkg = next(
            c for c in result.components if c.component_id == "SPDXRef-Package-requests"
        )
        assert requests_pkg.supplier == "AcmeCorp"

    def test_component_identifiers_include_purl(self, fixtures_path: Path) -> None:
        """externalRefs with PACKAGE-MANAGER category must be included in identifiers."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        requests_pkg = next(
            c for c in result.components if c.component_id == "SPDXRef-Package-requests"
        )
        assert "pkg:pypi/requests@2.31.0" in requests_pkg.identifiers

    def test_component_is_normalized_component_instance(self, fixtures_path: Path) -> None:
        """Each entry in result.components must be a NormalizedComponent instance."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        for component in result.components:
            assert isinstance(component, NormalizedComponent)

    def test_relationships_parsed(self, fixtures_path: Path) -> None:
        """Qualifying relationships (DEPENDS_ON etc.) must appear in result.relationships.

        The minimal fixture has one DESCRIBES (filtered out) and one DEPENDS_ON (kept).
        """
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        assert len(result.relationships) > 0

    def test_relationship_from_to_mapped(self, fixtures_path: Path) -> None:
        """Relationship spdxElementId and relatedSpdxElement must be mapped correctly."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        # The only qualifying relationship in the minimal fixture:
        # DEPENDS_ON: SPDXRef-DOCUMENT → SPDXRef-Package-requests
        depends_on_rels = [
            r for r in result.relationships if r.relationship_type == "DEPENDS_ON"
        ]
        assert len(depends_on_rels) >= 1
        rel = depends_on_rels[0]
        assert rel.from_id == "SPDXRef-DOCUMENT"
        assert rel.to_id == "SPDXRef-Package-requests"

    def test_relationship_type_mapped(self, fixtures_path: Path) -> None:
        """relationshipType must be preserved as-is in NormalizedRelationship.relationship_type."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        rel_types = {r.relationship_type for r in result.relationships}
        assert "DEPENDS_ON" in rel_types

    def test_non_qualifying_relationship_filtered_out(self, fixtures_path: Path) -> None:
        """DESCRIBES relationships must be filtered out; only dependency types are kept.

        The minimal fixture has a DESCRIBES relationship which must not appear
        in result.relationships because DESCRIBES is not a qualifying type.
        """
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        rel_types = {r.relationship_type for r in result.relationships}
        assert "DESCRIBES" not in rel_types

    def test_relationship_is_normalized_relationship_instance(self, fixtures_path: Path) -> None:
        """Each entry in result.relationships must be a NormalizedRelationship instance."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        for rel in result.relationships:
            assert isinstance(rel, NormalizedRelationship)

    def test_components_is_tuple(self, fixtures_path: Path) -> None:
        """result.components must be a tuple (frozen dataclass contract)."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        assert isinstance(result.components, tuple)

    def test_relationships_is_tuple(self, fixtures_path: Path) -> None:
        """result.relationships must be a tuple (frozen dataclass contract)."""
        result = parse_spdx(fixtures_path / "valid-minimal.spdx.json")
        assert isinstance(result.relationships, tuple)


# ---------------------------------------------------------------------------
# TestParseSpdxMissingFields — graceful handling of absent optional fields
# ---------------------------------------------------------------------------


class TestParseSpdxMissingFields:
    """Tests for optional-field absence and SPDX sentinel value normalization."""

    def test_missing_supplier_returns_none(self, fixtures_path: Path) -> None:
        """A package without a supplier field must produce component.supplier == None.

        missing-supplier.spdx.json: SPDXRef-Package-requests has no supplier key.
        """
        result = parse_spdx(fixtures_path / "missing-supplier.spdx.json")
        requests_pkg = next(
            c for c in result.components if c.component_id == "SPDXRef-Package-requests"
        )
        assert requests_pkg.supplier is None

    def test_missing_timestamp_returns_none(self, fixtures_path: Path) -> None:
        """An empty creationInfo.created string must produce result.timestamp == None.

        missing-timestamp.spdx.json has creationInfo.created = "".
        Per spec, empty string is normalized to None.
        """
        result = parse_spdx(fixtures_path / "missing-timestamp.spdx.json")
        assert result.timestamp is None

    def test_missing_relationships_returns_empty_tuple(self, fixtures_path: Path) -> None:
        """An empty relationships array must produce result.relationships == ().

        missing-relationships.spdx.json has relationships: [].
        """
        result = parse_spdx(fixtures_path / "missing-relationships.spdx.json")
        assert result.relationships == ()

    def test_missing_identifiers_returns_empty_tuple(self, fixtures_path: Path) -> None:
        """A package with no PACKAGE-MANAGER or SECURITY externalRefs must have identifiers == ().

        missing-identifiers.spdx.json: SPDXRef-Package-requests has only an OTHER
        category externalRef; SPDXRef-Package-urllib3 has no externalRefs at all.
        """
        result = parse_spdx(fixtures_path / "missing-identifiers.spdx.json")
        for component in result.components:
            assert component.identifiers == (), (
                f"Expected empty identifiers for {component.component_id}, "
                f"got {component.identifiers}"
            )

    def test_noassertion_version_returns_none(self, tmp_path: Path) -> None:
        """versionInfo='NOASSERTION' must be normalized to component.version == None."""
        fixture = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": "test-doc",
            "documentNamespace": "https://example.com/test",
            "creationInfo": {
                "created": "2024-01-01T00:00:00Z",
                "creators": ["Tool: test-tool"],
            },
            "packages": [
                {
                    "SPDXID": "SPDXRef-pkg-noassert",
                    "name": "no-version-pkg",
                    "versionInfo": "NOASSERTION",
                    "downloadLocation": "https://example.com/pkg",
                    "filesAnalyzed": False,
                }
            ],
            "relationships": [],
        }
        spdx_file = tmp_path / "noassertion.spdx.json"
        spdx_file.write_text(json.dumps(fixture))
        result = parse_spdx(spdx_file)
        pkg = next(
            c for c in result.components if c.component_id == "SPDXRef-pkg-noassert"
        )
        assert pkg.version is None

    def test_noassertion_supplier_returns_none(self, tmp_path: Path) -> None:
        """supplier='NOASSERTION' must be normalized to component.supplier == None."""
        fixture = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": "test-doc",
            "documentNamespace": "https://example.com/test",
            "creationInfo": {
                "created": "2024-01-01T00:00:00Z",
                "creators": ["Tool: test-tool"],
            },
            "packages": [
                {
                    "SPDXID": "SPDXRef-pkg-noassert",
                    "name": "no-supplier-pkg",
                    "versionInfo": "1.0.0",
                    "supplier": "NOASSERTION",
                    "downloadLocation": "https://example.com/pkg",
                    "filesAnalyzed": False,
                }
            ],
            "relationships": [],
        }
        spdx_file = tmp_path / "noassertion-supplier.spdx.json"
        spdx_file.write_text(json.dumps(fixture))
        result = parse_spdx(spdx_file)
        pkg = next(
            c for c in result.components if c.component_id == "SPDXRef-pkg-noassert"
        )
        assert pkg.supplier is None

    def test_only_security_external_ref_included_in_identifiers(
        self, tmp_path: Path
    ) -> None:
        """externalRefs with SECURITY category (CPEs) must appear in identifiers."""
        fixture = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": "test-doc",
            "documentNamespace": "https://example.com/test",
            "creationInfo": {
                "created": "2024-01-01T00:00:00Z",
                "creators": ["Tool: test-tool"],
            },
            "packages": [
                {
                    "SPDXID": "SPDXRef-pkg-cpe",
                    "name": "cpe-only-pkg",
                    "versionInfo": "1.0.0",
                    "downloadLocation": "https://example.com/pkg",
                    "filesAnalyzed": False,
                    "externalRefs": [
                        {
                            "referenceCategory": "SECURITY",
                            "referenceType": "cpe23Type",
                            "referenceLocator": "cpe:2.3:a:acme:pkg:1.0.0:*:*:*:*:*:*:*",
                        },
                        {
                            "referenceCategory": "OTHER",
                            "referenceType": "website",
                            "referenceLocator": "https://example.com",
                        },
                    ],
                }
            ],
            "relationships": [],
        }
        spdx_file = tmp_path / "cpe-only.spdx.json"
        spdx_file.write_text(json.dumps(fixture))
        result = parse_spdx(spdx_file)
        pkg = next(
            c for c in result.components if c.component_id == "SPDXRef-pkg-cpe"
        )
        assert "cpe:2.3:a:acme:pkg:1.0.0:*:*:*:*:*:*:*" in pkg.identifiers
        # The OTHER-category ref must not be included
        assert "https://example.com" not in pkg.identifiers


# ---------------------------------------------------------------------------
# TestParseSpdxFull — multi-component and multi-relationship fixture
# ---------------------------------------------------------------------------


class TestParseSpdxFull:
    """Tests using valid-full.spdx.json which contains 4 packages and 4 relationships.

    valid-full.spdx.json packages:
      - SPDXRef-Package-requests  (supplier: Organization: AcmeCorp)
      - SPDXRef-Package-urllib3   (supplier: Organization: AcmeCorp)
      - SPDXRef-Package-certifi   (supplier: Organization: ExampleSoft Ltd)
      - SPDXRef-Package-lodash    (supplier: Organization: ExampleSoft Ltd)

    valid-full.spdx.json relationships (4 total):
      - DESCRIBES: SPDXRef-DOCUMENT → SPDXRef-Package-requests  (filtered out)
      - DEPENDS_ON: SPDXRef-Package-requests → SPDXRef-Package-urllib3
      - DEPENDS_ON: SPDXRef-Package-requests → SPDXRef-Package-certifi
      - DEPENDS_ON: SPDXRef-DOCUMENT → SPDXRef-Package-lodash
    """

    def test_all_components_parsed(self, fixtures_path: Path) -> None:
        """All 4 packages in valid-full must be present in result.components."""
        result = parse_spdx(fixtures_path / "valid-full.spdx.json")
        assert len(result.components) == 4

    def test_all_component_ids_present(self, fixtures_path: Path) -> None:
        """Each package's SPDXID must appear as a component_id in result.components."""
        result = parse_spdx(fixtures_path / "valid-full.spdx.json")
        component_ids = {c.component_id for c in result.components}
        expected_ids = {
            "SPDXRef-Package-requests",
            "SPDXRef-Package-urllib3",
            "SPDXRef-Package-certifi",
            "SPDXRef-Package-lodash",
        }
        assert component_ids == expected_ids

    def test_all_relationships_parsed(self, fixtures_path: Path) -> None:
        """valid-full has 3 qualifying relationships (DESCRIBES is excluded).

        1 DESCRIBES (filtered) + 3 DEPENDS_ON (kept) = 3 in result.
        """
        result = parse_spdx(fixtures_path / "valid-full.spdx.json")
        assert len(result.relationships) == 3

    def test_full_relationship_from_to_values(self, fixtures_path: Path) -> None:
        """All three DEPENDS_ON relationships in valid-full must be correctly mapped."""
        result = parse_spdx(fixtures_path / "valid-full.spdx.json")
        rel_pairs = {(r.from_id, r.to_id) for r in result.relationships}
        expected_pairs = {
            ("SPDXRef-Package-requests", "SPDXRef-Package-urllib3"),
            ("SPDXRef-Package-requests", "SPDXRef-Package-certifi"),
            ("SPDXRef-DOCUMENT", "SPDXRef-Package-lodash"),
        }
        assert expected_pairs == rel_pairs

    def test_component_with_both_purl_and_cpe(self, fixtures_path: Path) -> None:
        """A package with PACKAGE-MANAGER and SECURITY refs must have both in identifiers.

        SPDXRef-Package-requests has a PURL and a CPE in valid-full.
        """
        result = parse_spdx(fixtures_path / "valid-full.spdx.json")
        requests_pkg = next(
            c for c in result.components if c.component_id == "SPDXRef-Package-requests"
        )
        assert "pkg:pypi/requests@2.31.0" in requests_pkg.identifiers
        assert "cpe:2.3:a:python-requests:requests:2.31.0:*:*:*:*:*:*:*" in requests_pkg.identifiers

    def test_supplier_stripped_for_all_components(self, fixtures_path: Path) -> None:
        """Organization: prefix must be stripped for every component in valid-full."""
        result = parse_spdx(fixtures_path / "valid-full.spdx.json")
        for component in result.components:
            assert component.supplier is not None
            assert not component.supplier.startswith("Organization: "), (
                f"Supplier prefix not stripped for {component.component_id}: "
                f"{component.supplier!r}"
            )
            assert not component.supplier.startswith("Tool: "), (
                f"Supplier prefix not stripped for {component.component_id}: "
                f"{component.supplier!r}"
            )

    def test_different_suppliers_in_full_fixture(self, fixtures_path: Path) -> None:
        """Both 'AcmeCorp' and 'ExampleSoft Ltd' must appear as supplier values."""
        result = parse_spdx(fixtures_path / "valid-full.spdx.json")
        suppliers = {c.supplier for c in result.components}
        assert "AcmeCorp" in suppliers
        assert "ExampleSoft Ltd" in suppliers


# ---------------------------------------------------------------------------
# TestParseSpdxErrors — file-level error handling
# ---------------------------------------------------------------------------


class TestParseSpdxErrors:
    """Tests that parse_spdx raises ParseError for unreadable or malformed inputs."""

    def test_nonexistent_file_raises_parse_error(self, tmp_path: Path) -> None:
        """Passing a path to a file that does not exist must raise ParseError."""
        nonexistent = tmp_path / "does-not-exist.spdx.json"
        with pytest.raises(ParseError):
            parse_spdx(nonexistent)

    def test_invalid_json_raises_parse_error(self, tmp_path: Path) -> None:
        """A file containing invalid JSON must raise ParseError."""
        bad_file = tmp_path / "bad.spdx.json"
        bad_file.write_text("not valid json {{{{")
        with pytest.raises(ParseError):
            parse_spdx(bad_file)

    def test_empty_file_raises_parse_error(self, tmp_path: Path) -> None:
        """An empty file (zero bytes) must raise ParseError."""
        empty_file = tmp_path / "empty.spdx.json"
        empty_file.write_text("")
        with pytest.raises(ParseError):
            parse_spdx(empty_file)

    def test_parse_error_is_raised_not_generic_exception(self, tmp_path: Path) -> None:
        """ParseError (not a bare Exception or NotImplementedError) must be raised.

        This test acts as a sentinel: once the parser is implemented it must
        raise the domain-specific ParseError, not propagate raw OSError or
        json.JSONDecodeError.
        """
        bad_file = tmp_path / "bad.spdx.json"
        bad_file.write_text("{ bad json }")
        with pytest.raises(ParseError):
            parse_spdx(bad_file)

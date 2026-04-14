"""Unit tests for the SPDX 2.3 Tag-Value parser.

Tests cover parse_spdx_tv(file_path: Path) -> NormalizedSBOM.
These tests are written before the implementation and follow TDD discipline.

Fixture files used:
  tests/fixtures/spdx/valid-full.spdx        — 3 packages, 3 DEPENDS_ON relationships
  tests/fixtures/spdx/valid-minimal.spdx     — 1 package, 1 DEPENDS_ON relationship
  tests/fixtures/spdx/missing-supplier.spdx  — 1 package with NOASSERTION supplier
  tests/fixtures/spdx/missing-relationships.spdx — 1 package, no qualifying relationships
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sbom_validator.exceptions import ParseError
from sbom_validator.models import NormalizedSBOM
from sbom_validator.parsers.spdx_tv_parser import parse_spdx_tv

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "spdx"


# ---------------------------------------------------------------------------
# Happy-path: valid-minimal.spdx
# ---------------------------------------------------------------------------


class TestParseSpdxTvMinimal:
    """Tests against the minimal valid Tag-Value fixture."""

    def test_returns_normalized_sbom(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert isinstance(result, NormalizedSBOM)

    def test_format_is_spdx_tv(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.format == "spdx-tv"

    def test_author_extracted_from_creator_tool(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.author is not None
        assert "sbom-generator-1.0" in result.author

    def test_author_strips_tool_prefix(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.author is not None
        assert "Tool: " not in result.author

    def test_author_includes_organization(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.author is not None
        assert "AcmeCorp" in result.author

    def test_timestamp_extracted(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.timestamp == "2024-01-15T10:00:00Z"

    def test_one_component_parsed(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert len(result.components) == 1

    def test_component_name(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.components[0].name == "requests"

    def test_component_id(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.components[0].component_id == "SPDXRef-Package-requests"

    def test_component_version(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.components[0].version == "2.31.0"

    def test_component_supplier_strips_organization_prefix(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.components[0].supplier == "AcmeCorp"

    def test_component_identifier_purl(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert "pkg:pypi/requests@2.31.0" in result.components[0].identifiers

    def test_one_qualifying_relationship(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert len(result.relationships) == 1

    def test_relationship_type_depends_on(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.relationships[0].relationship_type == "DEPENDS_ON"

    def test_relationship_from_id(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.relationships[0].from_id == "SPDXRef-DOCUMENT"

    def test_relationship_to_id(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert result.relationships[0].to_id == "SPDXRef-Package-requests"

    def test_components_is_tuple(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert isinstance(result.components, tuple)

    def test_relationships_is_tuple(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-minimal.spdx")
        assert isinstance(result.relationships, tuple)


# ---------------------------------------------------------------------------
# Happy-path: valid-full.spdx (3 packages, multiple relationships)
# ---------------------------------------------------------------------------


class TestParseSpdxTvFull:
    """Tests against the full valid Tag-Value fixture."""

    def test_three_components_parsed(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-full.spdx")
        assert len(result.components) == 3

    def test_three_relationships_parsed(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-full.spdx")
        assert len(result.relationships) == 3

    def test_component_names_present(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-full.spdx")
        names = {c.name for c in result.components}
        assert "requests" in names
        assert "urllib3" in names
        assert "certifi" in names

    def test_requests_has_two_identifiers(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-full.spdx")
        requests = next(c for c in result.components if c.name == "requests")
        assert len(requests.identifiers) == 2

    def test_requests_purl_identifier(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-full.spdx")
        requests = next(c for c in result.components if c.name == "requests")
        assert "pkg:pypi/requests@2.31.0" in requests.identifiers

    def test_requests_cpe_identifier(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-full.spdx")
        requests = next(c for c in result.components if c.name == "requests")
        assert any("cpe:" in ident for ident in requests.identifiers)

    def test_author_contains_both_creators(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "valid-full.spdx")
        assert result.author is not None
        assert "sbom-generator-1.0" in result.author
        assert "AcmeCorp" in result.author


# ---------------------------------------------------------------------------
# NOASSERTION handling
# ---------------------------------------------------------------------------


class TestParseSpdxTvNoAssertion:
    """Tests for NOASSERTION and empty field normalization."""

    def test_noassertion_supplier_normalized_to_none(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "missing-supplier.spdx")
        assert result.components[0].supplier is None

    def test_noassertion_supplier_does_not_contain_noassertion_string(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "missing-supplier.spdx")
        assert result.components[0].supplier != "NOASSERTION"


# ---------------------------------------------------------------------------
# Missing qualifying relationships
# ---------------------------------------------------------------------------


class TestParseSpdxTvMissingRelationships:
    def test_no_qualifying_relationships_returns_empty_tuple(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "missing-relationships.spdx")
        assert result.relationships == ()

    def test_components_still_parsed_when_no_relationships(self) -> None:
        result = parse_spdx_tv(FIXTURES_DIR / "missing-relationships.spdx")
        assert len(result.components) == 1


# ---------------------------------------------------------------------------
# Edge cases: programmatically constructed files
# ---------------------------------------------------------------------------


class TestParseSpdxTvEdgeCases:
    def test_empty_version_normalized_to_none(self, tmp_path: Path) -> None:
        content = (
            "SPDXVersion: SPDX-2.3\n"
            "DataLicense: CC0-1.0\n"
            "SPDXID: SPDXRef-DOCUMENT\n"
            "DocumentName: test\n"
            "DocumentNamespace: https://example.com/test\n"
            "Creator: Tool: test-tool\n"
            "Created: 2024-01-01T00:00:00Z\n\n"
            "PackageName: mylib\n"
            "SPDXID: SPDXRef-Package-mylib\n"
            "PackageVersion: NOASSERTION\n"
            "PackageSupplier: Organization: TestOrg\n"
            "PackageDownloadLocation: https://example.com\n"
            "FilesAnalyzed: false\n"
            "ExternalRef: PACKAGE-MANAGER purl pkg:pypi/mylib@0.1\n\n"
            "Relationship: SPDXRef-DOCUMENT DEPENDS_ON SPDXRef-Package-mylib\n"
        )
        f = tmp_path / "edge.spdx"
        f.write_text(content, encoding="utf-8")
        result = parse_spdx_tv(f)
        assert result.components[0].version is None

    def test_non_qualifying_relationship_type_excluded(self, tmp_path: Path) -> None:
        """DESCRIBES and CONTAINS are not qualifying; only DEPENDS_ON etc. are kept."""
        content = (
            "SPDXVersion: SPDX-2.3\n"
            "DataLicense: CC0-1.0\n"
            "SPDXID: SPDXRef-DOCUMENT\n"
            "DocumentName: test\n"
            "DocumentNamespace: https://example.com/test\n"
            "Creator: Tool: test-tool\n"
            "Created: 2024-01-01T00:00:00Z\n\n"
            "PackageName: mylib\n"
            "SPDXID: SPDXRef-Package-mylib\n"
            "PackageVersion: 1.0\n"
            "PackageSupplier: Organization: TestOrg\n"
            "PackageDownloadLocation: https://example.com\n"
            "FilesAnalyzed: false\n"
            "ExternalRef: PACKAGE-MANAGER purl pkg:pypi/mylib@1.0\n\n"
            "Relationship: SPDXRef-DOCUMENT DESCRIBES SPDXRef-Package-mylib\n"
            "Relationship: SPDXRef-DOCUMENT CONTAINS SPDXRef-Package-mylib\n"
        )
        f = tmp_path / "no_dep.spdx"
        f.write_text(content, encoding="utf-8")
        result = parse_spdx_tv(f)
        assert result.relationships == ()

    def test_multiple_qualifying_relationship_types(self, tmp_path: Path) -> None:
        """DYNAMIC_LINK, STATIC_LINK, RUNTIME_DEPENDENCY_OF, DEV_DEPENDENCY_OF should be kept."""
        content = (
            "SPDXVersion: SPDX-2.3\n"
            "DataLicense: CC0-1.0\n"
            "SPDXID: SPDXRef-DOCUMENT\n"
            "DocumentName: test\n"
            "DocumentNamespace: https://example.com/test\n"
            "Creator: Tool: test-tool\n"
            "Created: 2024-01-01T00:00:00Z\n\n"
            "PackageName: libA\n"
            "SPDXID: SPDXRef-Package-libA\n"
            "PackageVersion: 1.0\n"
            "PackageSupplier: Organization: TestOrg\n"
            "PackageDownloadLocation: https://example.com\n"
            "FilesAnalyzed: false\n"
            "ExternalRef: PACKAGE-MANAGER purl pkg:pypi/libA@1.0\n\n"
            "PackageName: libB\n"
            "SPDXID: SPDXRef-Package-libB\n"
            "PackageVersion: 2.0\n"
            "PackageSupplier: Organization: TestOrg\n"
            "PackageDownloadLocation: https://example.com\n"
            "FilesAnalyzed: false\n"
            "ExternalRef: PACKAGE-MANAGER purl pkg:pypi/libB@2.0\n\n"
            "Relationship: SPDXRef-Package-libA DYNAMIC_LINK SPDXRef-Package-libB\n"
            "Relationship: SPDXRef-Package-libA STATIC_LINK SPDXRef-Package-libB\n"
            "Relationship: SPDXRef-Package-libB RUNTIME_DEPENDENCY_OF SPDXRef-Package-libA\n"
            "Relationship: SPDXRef-Package-libB DEV_DEPENDENCY_OF SPDXRef-Package-libA\n"
        )
        f = tmp_path / "multi_rel.spdx"
        f.write_text(content, encoding="utf-8")
        result = parse_spdx_tv(f)
        assert len(result.relationships) == 4

    def test_security_external_ref_type_collected(self, tmp_path: Path) -> None:
        content = (
            "SPDXVersion: SPDX-2.3\n"
            "DataLicense: CC0-1.0\n"
            "SPDXID: SPDXRef-DOCUMENT\n"
            "DocumentName: test\n"
            "DocumentNamespace: https://example.com/test\n"
            "Creator: Tool: test-tool\n"
            "Created: 2024-01-01T00:00:00Z\n\n"
            "PackageName: openssl\n"
            "SPDXID: SPDXRef-Package-openssl\n"
            "PackageVersion: 3.0.0\n"
            "PackageSupplier: Organization: OpenSSL\n"
            "PackageDownloadLocation: https://example.com\n"
            "FilesAnalyzed: false\n"
            "ExternalRef: SECURITY cpe23Type cpe:2.3:a:openssl:openssl:3.0.0:*:*:*:*:*:*:*\n\n"
            "Relationship: SPDXRef-DOCUMENT DEPENDS_ON SPDXRef-Package-openssl\n"
        )
        f = tmp_path / "cpe_only.spdx"
        f.write_text(content, encoding="utf-8")
        result = parse_spdx_tv(f)
        assert any("cpe:" in ident for ident in result.components[0].identifiers)

    def test_no_creator_lines_yields_none_author(self, tmp_path: Path) -> None:
        content = (
            "SPDXVersion: SPDX-2.3\n"
            "DataLicense: CC0-1.0\n"
            "SPDXID: SPDXRef-DOCUMENT\n"
            "DocumentName: test\n"
            "DocumentNamespace: https://example.com/test\n"
            "Created: 2024-01-01T00:00:00Z\n\n"
            "PackageName: mylib\n"
            "SPDXID: SPDXRef-Package-mylib\n"
            "PackageVersion: 1.0\n"
            "PackageSupplier: Organization: TestOrg\n"
            "PackageDownloadLocation: https://example.com\n"
            "FilesAnalyzed: false\n"
            "ExternalRef: PACKAGE-MANAGER purl pkg:pypi/mylib@1.0\n\n"
            "Relationship: SPDXRef-DOCUMENT DEPENDS_ON SPDXRef-Package-mylib\n"
        )
        f = tmp_path / "no_creator.spdx"
        f.write_text(content, encoding="utf-8")
        result = parse_spdx_tv(f)
        assert result.author is None

    def test_empty_package_supplier_normalized_to_none(self, tmp_path: Path) -> None:
        content = (
            "SPDXVersion: SPDX-2.3\n"
            "DataLicense: CC0-1.0\n"
            "SPDXID: SPDXRef-DOCUMENT\n"
            "DocumentName: test\n"
            "DocumentNamespace: https://example.com/test\n"
            "Creator: Tool: test-tool\n"
            "Created: 2024-01-01T00:00:00Z\n\n"
            "PackageName: mylib\n"
            "SPDXID: SPDXRef-Package-mylib\n"
            "PackageVersion: 1.0\n"
            "PackageDownloadLocation: https://example.com\n"
            "FilesAnalyzed: false\n"
            "ExternalRef: PACKAGE-MANAGER purl pkg:pypi/mylib@1.0\n\n"
            "Relationship: SPDXRef-DOCUMENT DEPENDS_ON SPDXRef-Package-mylib\n"
        )
        f = tmp_path / "no_supplier.spdx"
        f.write_text(content, encoding="utf-8")
        result = parse_spdx_tv(f)
        assert result.components[0].supplier is None


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestParseSpdxTvErrorPaths:
    def test_nonexistent_file_raises_parse_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.spdx"
        with pytest.raises(ParseError):
            parse_spdx_tv(missing)

    def test_empty_file_raises_parse_error(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.spdx"
        f.write_text("", encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx_tv(f)

    def test_missing_package_spdxid_raises_parse_error(self, tmp_path: Path) -> None:
        """A package block without SPDXID cannot produce a valid component_id."""
        content = (
            "SPDXVersion: SPDX-2.3\n"
            "DataLicense: CC0-1.0\n"
            "SPDXID: SPDXRef-DOCUMENT\n"
            "DocumentName: test\n"
            "DocumentNamespace: https://example.com/test\n"
            "Creator: Tool: test-tool\n"
            "Created: 2024-01-01T00:00:00Z\n\n"
            "PackageName: mylib\n"
            # SPDXID deliberately omitted
            "PackageVersion: 1.0\n"
            "PackageDownloadLocation: https://example.com\n"
        )
        f = tmp_path / "no_spdxid.spdx"
        f.write_text(content, encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx_tv(f)

    def test_wrong_spdx_version_raises_parse_error(self, tmp_path: Path) -> None:
        content = "SPDXVersion: SPDX-2.2\nDataLicense: CC0-1.0\n"
        f = tmp_path / "spdx22.spdx"
        f.write_text(content, encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx_tv(f)

    def test_os_error_on_read_raises_parse_error(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        f = tmp_path / "unreadable.spdx"
        f.write_text("SPDXVersion: SPDX-2.3\n", encoding="utf-8")
        with patch.object(type(f), "read_text", side_effect=OSError("permission denied")):
            with pytest.raises(ParseError):
                parse_spdx_tv(f)

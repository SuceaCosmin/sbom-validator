"""Unit tests for the SPDX 2.3 YAML parser.

Tests cover parse_spdx_yaml(file_path: Path) -> NormalizedSBOM.
These tests are written before the implementation (TDD discipline).

The YAML format is structurally identical to SPDX JSON — same field names, same
nesting, just YAML syntax. The parser uses yaml.safe_load and then delegates
to the shared _parse_spdx_document helper from spdx_parser.py.

Fixture files used:
  tests/fixtures/spdx/valid-full.spdx.yaml        — 3 packages, 3 DEPENDS_ON relationships
  tests/fixtures/spdx/valid-minimal.spdx.yaml     — 1 package, 1 DEPENDS_ON relationship
  tests/fixtures/spdx/missing-supplier.spdx.yaml  — 1 package with NOASSERTION supplier
  tests/fixtures/spdx/invalid-schema.spdx.yaml    — structurally invalid (for schema tests)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sbom_validator.exceptions import ParseError
from sbom_validator.models import NormalizedSBOM
from sbom_validator.parsers.spdx_yaml_parser import parse_spdx_yaml

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "spdx"


# ---------------------------------------------------------------------------
# Happy-path: valid-minimal.spdx.yaml
# ---------------------------------------------------------------------------


class TestParseSpdxYamlMinimal:
    """Tests against the minimal valid YAML fixture."""

    def test_returns_normalized_sbom(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert isinstance(result, NormalizedSBOM)

    def test_format_is_spdx_yaml(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert result.format == "spdx-yaml"

    def test_author_extracted(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert result.author is not None
        assert "sbom-generator-1.0" in result.author

    def test_author_strips_tool_prefix(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert result.author is not None
        assert "Tool: " not in result.author

    def test_timestamp_extracted(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert result.timestamp == "2024-01-15T10:00:00Z"

    def test_one_component_parsed(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert len(result.components) == 1

    def test_component_name(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert result.components[0].name == "requests"

    def test_component_version(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert result.components[0].version == "2.31.0"

    def test_component_supplier_strips_organization_prefix(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert result.components[0].supplier == "AcmeCorp"

    def test_component_identifier_purl(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert "pkg:pypi/requests@2.31.0" in result.components[0].identifiers

    def test_one_qualifying_relationship(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert len(result.relationships) == 1

    def test_relationship_type(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert result.relationships[0].relationship_type == "DEPENDS_ON"

    def test_components_is_tuple(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert isinstance(result.components, tuple)

    def test_relationships_is_tuple(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-minimal.spdx.yaml")
        assert isinstance(result.relationships, tuple)


# ---------------------------------------------------------------------------
# Happy-path: valid-full.spdx.yaml (3 packages)
# ---------------------------------------------------------------------------


class TestParseSpdxYamlFull:
    """Tests against the full valid YAML fixture."""

    def test_three_components_parsed(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-full.spdx.yaml")
        assert len(result.components) == 3

    def test_three_relationships_parsed(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-full.spdx.yaml")
        assert len(result.relationships) == 3

    def test_component_names_present(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-full.spdx.yaml")
        names = {c.name for c in result.components}
        assert "requests" in names
        assert "urllib3" in names
        assert "certifi" in names

    def test_requests_has_two_identifiers(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-full.spdx.yaml")
        requests = next(c for c in result.components if c.name == "requests")
        assert len(requests.identifiers) == 2

    def test_requests_cpe_identifier(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "valid-full.spdx.yaml")
        requests = next(c for c in result.components if c.name == "requests")
        assert any("cpe:" in ident for ident in requests.identifiers)


# ---------------------------------------------------------------------------
# NOASSERTION handling
# ---------------------------------------------------------------------------


class TestParseSpdxYamlNoAssertion:
    def test_noassertion_supplier_normalized_to_none(self) -> None:
        result = parse_spdx_yaml(FIXTURES_DIR / "missing-supplier.spdx.yaml")
        assert result.components[0].supplier is None


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestParseSpdxYamlErrorPaths:
    def test_nonexistent_file_raises_parse_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.spdx.yaml"
        with pytest.raises(ParseError):
            parse_spdx_yaml(missing)

    def test_empty_file_raises_parse_error(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.spdx.yaml"
        f.write_text("", encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx_yaml(f)

    def test_non_yaml_content_raises_parse_error(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.spdx.yaml"
        f.write_text(":::: invalid:yaml: [content\n", encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx_yaml(f)

    def test_yaml_array_at_root_raises_parse_error(self, tmp_path: Path) -> None:
        """YAML that parses to a list instead of a dict must raise ParseError."""
        f = tmp_path / "array.spdx.yaml"
        f.write_text("- spdxVersion: SPDX-2.3\n- name: test\n", encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx_yaml(f)

    def test_yaml_missing_spdxid_in_package_raises_parse_error(self, tmp_path: Path) -> None:
        content = (
            "spdxVersion: SPDX-2.3\n"
            "dataLicense: CC0-1.0\n"
            "SPDXID: SPDXRef-DOCUMENT\n"
            "name: test\n"
            "documentNamespace: https://example.com/test\n"
            "creationInfo:\n"
            "  created: '2024-01-01T00:00:00Z'\n"
            "  creators:\n"
            "    - 'Tool: test-tool'\n"
            "packages:\n"
            "  - name: mylib\n"
            "    versionInfo: '1.0'\n"
            # SPDXID deliberately omitted
            "    downloadLocation: https://example.com\n"
            "    filesAnalyzed: false\n"
        )
        f = tmp_path / "no_spdxid.spdx.yaml"
        f.write_text(content, encoding="utf-8")
        with pytest.raises(ParseError):
            parse_spdx_yaml(f)

    def test_os_error_on_read_raises_parse_error(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        f = tmp_path / "unreadable.spdx.yaml"
        f.write_text("spdxVersion: SPDX-2.3\n", encoding="utf-8")
        with patch.object(type(f), "read_text", side_effect=OSError("permission denied")):
            with pytest.raises(ParseError):
                parse_spdx_yaml(f)

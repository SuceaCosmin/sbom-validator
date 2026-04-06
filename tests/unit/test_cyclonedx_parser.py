"""Unit tests for the CycloneDX 1.6 JSON parser (Task 2.C1).

These tests are written TDD-style: they specify the expected behaviour of
parse_cyclonedx() and will FAIL until the parser is implemented.

Fixtures used:
  tests/fixtures/cyclonedx/valid-minimal.cdx.json   – one component, one dep
  tests/fixtures/cyclonedx/valid-full.cdx.json       – four components, multiple deps, CPE
  tests/fixtures/cyclonedx/missing-supplier.cdx.json – component without supplier
  tests/fixtures/cyclonedx/missing-timestamp.cdx.json – no metadata.timestamp
  tests/fixtures/cyclonedx/missing-relationships.cdx.json – empty dependencies array
  tests/fixtures/cyclonedx/missing-identifiers.cdx.json – no purl / cpe on components
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sbom_validator.exceptions import ParseError
from sbom_validator.models import (
    NormalizedComponent,
    NormalizedRelationship,
    NormalizedSBOM,
)
from sbom_validator.parsers.cyclonedx_parser import parse_cyclonedx

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def fixtures_path() -> Path:
    """Return the path to the CycloneDX fixture directory."""
    return Path("tests/fixtures/cyclonedx")


# ---------------------------------------------------------------------------
# TestParseCycloneDXBasic – happy-path tests against valid-minimal.cdx.json
# ---------------------------------------------------------------------------


class TestParseCycloneDXBasic:
    """Basic parsing behaviour using the minimal valid fixture."""

    def test_returns_normalized_sbom_instance(self, fixtures_path: Path) -> None:
        """parse_cyclonedx must return a NormalizedSBOM instance."""
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        assert isinstance(result, NormalizedSBOM)

    def test_format_is_cyclonedx(self, fixtures_path: Path) -> None:
        """The format field must always be the string 'cyclonedx'."""
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        assert result.format == "cyclonedx"

    def test_author_extracted_from_metadata_authors(self, fixtures_path: Path) -> None:
        """Author must be taken from metadata.authors[0].name when present.

        valid-minimal has metadata.authors = [{"name": "AcmeCorp SBOM Team"}].
        """
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        assert result.author == "AcmeCorp SBOM Team"

    def test_timestamp_extracted(self, fixtures_path: Path) -> None:
        """timestamp must match metadata.timestamp verbatim."""
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        assert result.timestamp == "2024-01-15T10:00:00Z"

    def test_components_parsed(self, fixtures_path: Path) -> None:
        """components must be a tuple with one entry for valid-minimal."""
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        assert isinstance(result.components, tuple)
        assert len(result.components) == 1

    def test_component_name_mapped(self, fixtures_path: Path) -> None:
        """NormalizedComponent.name must equal components[0].name."""
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        component = result.components[0]
        assert isinstance(component, NormalizedComponent)
        assert component.name == "requests"

    def test_component_version_mapped(self, fixtures_path: Path) -> None:
        """NormalizedComponent.version must equal components[0].version."""
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        assert result.components[0].version == "2.31.0"

    def test_component_supplier_mapped(self, fixtures_path: Path) -> None:
        """NormalizedComponent.supplier must equal components[0].supplier.name."""
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        assert result.components[0].supplier == "AcmeCorp"

    def test_component_purl_in_identifiers(self, fixtures_path: Path) -> None:
        """identifiers must contain the purl string when purl is present."""
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        assert "pkg:pypi/requests@2.31.0" in result.components[0].identifiers

    def test_relationships_parsed_from_dependencies(self, fixtures_path: Path) -> None:
        """relationships must be a non-empty tuple for valid-minimal."""
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        assert isinstance(result.relationships, tuple)
        assert len(result.relationships) >= 1

    def test_each_depends_on_entry_becomes_relationship(
        self, fixtures_path: Path
    ) -> None:
        """Each dependsOn entry must produce one NormalizedRelationship.

        valid-minimal has one dependency: app-ref -> pkg:pypi/requests@2.31.0.
        """
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        rel = result.relationships[0]
        assert isinstance(rel, NormalizedRelationship)
        assert rel.from_id == "app-ref"
        assert rel.to_id == "pkg:pypi/requests@2.31.0"
        assert rel.relationship_type == "DEPENDS_ON"

    def test_component_id_uses_bom_ref(self, fixtures_path: Path) -> None:
        """component_id must be taken from bom-ref when present."""
        result = parse_cyclonedx(fixtures_path / "valid-minimal.cdx.json")
        assert result.components[0].component_id == "pkg:pypi/requests@2.31.0"


# ---------------------------------------------------------------------------
# TestParseCycloneDXMissingFields – graceful handling of absent optional fields
# ---------------------------------------------------------------------------


class TestParseCycloneDXMissingFields:
    """Parser must degrade gracefully when optional fields are absent."""

    def test_missing_supplier_returns_none(self, fixtures_path: Path) -> None:
        """supplier must be None when components[i].supplier is absent.

        missing-supplier.cdx.json has 'requests' without a supplier object.
        """
        result = parse_cyclonedx(fixtures_path / "missing-supplier.cdx.json")
        # Find the requests component (first component, which has no supplier)
        requests_component = next(
            c for c in result.components if c.name == "requests"
        )
        assert requests_component.supplier is None

    def test_missing_timestamp_returns_none(self, fixtures_path: Path) -> None:
        """timestamp must be None when metadata.timestamp is absent."""
        result = parse_cyclonedx(fixtures_path / "missing-timestamp.cdx.json")
        assert result.timestamp is None

    def test_missing_relationships_returns_empty_tuple(
        self, fixtures_path: Path
    ) -> None:
        """relationships must be an empty tuple when dependencies array is empty."""
        result = parse_cyclonedx(fixtures_path / "missing-relationships.cdx.json")
        assert result.relationships == ()

    def test_missing_identifiers_returns_empty_tuple(
        self, fixtures_path: Path
    ) -> None:
        """identifiers must be an empty tuple when both purl and cpe are absent.

        missing-identifiers.cdx.json has components with no purl or cpe fields.
        """
        result = parse_cyclonedx(fixtures_path / "missing-identifiers.cdx.json")
        for component in result.components:
            assert component.identifiers == ()

    def test_manufacture_fallback_for_author(self, tmp_path: Path) -> None:
        """author must fall back to metadata.manufacture.name when authors is absent."""
        doc = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "metadata": {
                "timestamp": "2024-06-01T00:00:00Z",
                "manufacture": {"name": "ManufactureCorp"},
            },
            "components": [],
            "dependencies": [],
        }
        sbom_file = tmp_path / "manufacture-fallback.cdx.json"
        sbom_file.write_text(json.dumps(doc), encoding="utf-8")

        result = parse_cyclonedx(sbom_file)
        assert result.author == "ManufactureCorp"

    def test_no_author_source_returns_none(self, tmp_path: Path) -> None:
        """author must be None when neither metadata.authors nor manufacture is present."""
        doc = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "metadata": {
                "timestamp": "2024-06-01T00:00:00Z",
            },
            "components": [],
            "dependencies": [],
        }
        sbom_file = tmp_path / "no-author.cdx.json"
        sbom_file.write_text(json.dumps(doc), encoding="utf-8")

        result = parse_cyclonedx(sbom_file)
        assert result.author is None

    def test_component_id_falls_back_to_name_at_version_when_bom_ref_absent(
        self, tmp_path: Path
    ) -> None:
        """component_id must fall back to 'name@version' when bom-ref is absent."""
        doc = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "metadata": {},
            "components": [
                {"type": "library", "name": "mylib", "version": "3.0.0"},
            ],
            "dependencies": [],
        }
        sbom_file = tmp_path / "no-bom-ref.cdx.json"
        sbom_file.write_text(json.dumps(doc), encoding="utf-8")

        result = parse_cyclonedx(sbom_file)
        assert result.components[0].component_id == "mylib@3.0.0"

    def test_missing_version_returns_none(self, tmp_path: Path) -> None:
        """version must be None when components[i].version is absent."""
        doc = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "metadata": {},
            "components": [
                {"type": "library", "bom-ref": "noversion-ref", "name": "noversion"},
            ],
            "dependencies": [],
        }
        sbom_file = tmp_path / "no-version.cdx.json"
        sbom_file.write_text(json.dumps(doc), encoding="utf-8")

        result = parse_cyclonedx(sbom_file)
        assert result.components[0].version is None


# ---------------------------------------------------------------------------
# TestParseCycloneDXFull – multi-component fixture assertions
# ---------------------------------------------------------------------------


class TestParseCycloneDXFull:
    """Tests using the full four-component fixture."""

    def test_all_components_parsed(self, fixtures_path: Path) -> None:
        """All four components in valid-full must be present."""
        result = parse_cyclonedx(fixtures_path / "valid-full.cdx.json")
        assert len(result.components) == 4

    def test_cpe_in_identifiers(self, fixtures_path: Path) -> None:
        """identifiers must include the cpe string when cpe is present.

        valid-full has a CPE on the 'requests' component.
        """
        result = parse_cyclonedx(fixtures_path / "valid-full.cdx.json")
        requests_component = next(
            c for c in result.components if c.name == "requests"
        )
        assert "cpe:2.3:a:python-requests:requests:2.31.0:*:*:*:*:*:*:*" in (
            requests_component.identifiers
        )

    def test_purl_and_cpe_both_in_identifiers(self, fixtures_path: Path) -> None:
        """A component with both purl and cpe must include both in identifiers."""
        result = parse_cyclonedx(fixtures_path / "valid-full.cdx.json")
        requests_component = next(
            c for c in result.components if c.name == "requests"
        )
        assert "pkg:pypi/requests@2.31.0" in requests_component.identifiers
        assert "cpe:2.3:a:python-requests:requests:2.31.0:*:*:*:*:*:*:*" in (
            requests_component.identifiers
        )

    def test_relationships_expanded_from_multi_depends_on(
        self, fixtures_path: Path
    ) -> None:
        """A dependsOn list with two entries must produce two NormalizedRelationships.

        valid-full: app-webapp-2.5.0 dependsOn [requests, lodash] → 2 relationships.
        """
        result = parse_cyclonedx(fixtures_path / "valid-full.cdx.json")
        app_rels = [r for r in result.relationships if r.from_id == "app-webapp-2.5.0"]
        assert len(app_rels) == 2
        to_ids = {r.to_id for r in app_rels}
        assert "pkg:pypi/requests@2.31.0" in to_ids
        assert "pkg:npm/lodash@4.17.21" in to_ids

    def test_all_relationships_have_depends_on_type(self, fixtures_path: Path) -> None:
        """Every relationship must have relationship_type == 'DEPENDS_ON'."""
        result = parse_cyclonedx(fixtures_path / "valid-full.cdx.json")
        for rel in result.relationships:
            assert rel.relationship_type == "DEPENDS_ON"

    def test_empty_depends_on_produces_no_relationships_for_that_ref(
        self, fixtures_path: Path
    ) -> None:
        """A dependency entry with an empty dependsOn must not produce any relationship.

        valid-full has urllib3, certifi, and lodash each with dependsOn: [].
        """
        result = parse_cyclonedx(fixtures_path / "valid-full.cdx.json")
        leaf_refs = {
            "pkg:pypi/urllib3@2.1.0",
            "pkg:pypi/certifi@2024.2.2",
            "pkg:npm/lodash@4.17.21",
        }
        leaf_rels = [r for r in result.relationships if r.from_id in leaf_refs]
        assert leaf_rels == []

    def test_total_relationship_count_in_full_fixture(
        self, fixtures_path: Path
    ) -> None:
        """valid-full must produce exactly 4 relationships in total.

        app->requests, app->lodash, requests->urllib3, requests->certifi.
        """
        result = parse_cyclonedx(fixtures_path / "valid-full.cdx.json")
        assert len(result.relationships) == 4

    def test_components_are_tuple_of_normalized_component(
        self, fixtures_path: Path
    ) -> None:
        """Every entry in components must be a NormalizedComponent instance."""
        result = parse_cyclonedx(fixtures_path / "valid-full.cdx.json")
        for component in result.components:
            assert isinstance(component, NormalizedComponent)

    def test_relationships_are_tuple_of_normalized_relationship(
        self, fixtures_path: Path
    ) -> None:
        """Every entry in relationships must be a NormalizedRelationship instance."""
        result = parse_cyclonedx(fixtures_path / "valid-full.cdx.json")
        for rel in result.relationships:
            assert isinstance(rel, NormalizedRelationship)

    def test_multiple_authors_concatenated(self, tmp_path: Path) -> None:
        """Multiple metadata.authors entries must be joined with ', '."""
        doc = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "metadata": {
                "authors": [
                    {"name": "Alice"},
                    {"name": "Bob"},
                ],
            },
            "components": [],
            "dependencies": [],
        }
        sbom_file = tmp_path / "multi-author.cdx.json"
        sbom_file.write_text(json.dumps(doc), encoding="utf-8")

        result = parse_cyclonedx(sbom_file)
        assert result.author == "Alice, Bob"


# ---------------------------------------------------------------------------
# TestParseCycloneDXErrors – error handling
# ---------------------------------------------------------------------------


class TestParseCycloneDXErrors:
    """parse_cyclonedx must raise ParseError for unreadable / malformed input."""

    def test_nonexistent_file_raises_parse_error(self, tmp_path: Path) -> None:
        """Passing a path that does not exist must raise ParseError."""
        missing = tmp_path / "does-not-exist.cdx.json"
        with pytest.raises(ParseError):
            parse_cyclonedx(missing)

    def test_invalid_json_raises_parse_error(self, tmp_path: Path) -> None:
        """A file containing invalid JSON must raise ParseError."""
        bad_file = tmp_path / "bad.cdx.json"
        bad_file.write_text("this is not json {{{", encoding="utf-8")
        with pytest.raises(ParseError):
            parse_cyclonedx(bad_file)

    def test_parse_error_is_raised_not_not_implemented_error(
        self, tmp_path: Path
    ) -> None:
        """parse_cyclonedx must not propagate NotImplementedError to callers.

        This assertion is intentionally strict: a stub raising NotImplementedError
        must fail this test, ensuring the developer replaces the stub.
        """
        bad_file = tmp_path / "bad.cdx.json"
        bad_file.write_text("{}", encoding="utf-8")
        # Either returns a NormalizedSBOM or raises ParseError — never NotImplementedError.
        try:
            parse_cyclonedx(bad_file)
        except ParseError:
            pass  # acceptable
        except NotImplementedError:
            pytest.fail(
                "parse_cyclonedx raised NotImplementedError — parser not yet implemented"
            )

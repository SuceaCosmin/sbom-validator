"""TDD unit tests for the NTIA minimum elements checker (Task 2.F1).

These tests are written BEFORE the checker is implemented and are expected to
FAIL until the developer implements check_ntia() in
sbom_validator/ntia_checker.py.
"""

from __future__ import annotations

from pathlib import Path

from sbom_validator.models import (
    IssueSeverity,
    NormalizedComponent,
    NormalizedRelationship,
    NormalizedSBOM,
    ValidationIssue,
)
from sbom_validator.ntia_checker import check_ntia
from sbom_validator.parsers.cyclonedx_parser import parse_cyclonedx
from sbom_validator.parsers.spdx_parser import parse_spdx

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

SPDX_FIXTURES = Path("tests/fixtures/spdx")
CDX_FIXTURES = Path("tests/fixtures/cyclonedx")


# ---------------------------------------------------------------------------
# Helpers for constructing minimal valid NormalizedSBOM objects inline
# ---------------------------------------------------------------------------


def _make_valid_component(
    component_id: str = "pkg-1",
    name: str = "some-pkg",
    version: str = "1.0.0",
    supplier: str = "AcmeCorp",
    identifiers: tuple[str, ...] = ("pkg:pypi/some-pkg@1.0.0",),
) -> NormalizedComponent:
    return NormalizedComponent(
        component_id=component_id,
        name=name,
        version=version,
        supplier=supplier,
        identifiers=identifiers,
    )


def _make_valid_sbom(
    *,
    format: str = "spdx",
    author: str | None = "test-tool",
    timestamp: str | None = "2024-01-01T00:00:00Z",
    components: tuple[NormalizedComponent, ...] | None = None,
    relationships: tuple[NormalizedRelationship, ...] | None = None,
) -> NormalizedSBOM:
    if components is None:
        components = (_make_valid_component(),)
    if relationships is None:
        relationships = (NormalizedRelationship(from_id="doc", to_id="pkg-1"),)
    return NormalizedSBOM(
        format=format,
        author=author,
        timestamp=timestamp,
        components=components,
        relationships=relationships,
    )


# ===========================================================================
# TestNtiaCheckerValidDocuments
# ===========================================================================


class TestNtiaCheckerValidDocuments:
    """Fully compliant documents must return an empty issue list."""

    def test_valid_spdx_minimal_returns_empty_list(self) -> None:
        sbom = parse_spdx(SPDX_FIXTURES / "valid-minimal.spdx.json")
        result = check_ntia(sbom)
        assert result == []

    def test_valid_spdx_full_returns_empty_list(self) -> None:
        sbom = parse_spdx(SPDX_FIXTURES / "valid-full.spdx.json")
        assert check_ntia(sbom) == []

    def test_valid_cyclonedx_minimal_returns_empty_list(self) -> None:
        sbom = parse_cyclonedx(CDX_FIXTURES / "valid-minimal.cdx.json")
        assert check_ntia(sbom) == []

    def test_valid_cyclonedx_full_returns_empty_list(self) -> None:
        sbom = parse_cyclonedx(CDX_FIXTURES / "valid-full.cdx.json")
        assert check_ntia(sbom) == []

    def test_inline_valid_sbom_returns_empty_list(self) -> None:
        sbom = _make_valid_sbom()
        assert check_ntia(sbom) == []


# ===========================================================================
# TestNtiaCheckerSupplier (FR-04)
# ===========================================================================


class TestNtiaCheckerSupplier:
    """FR-04: every component must have a non-None supplier."""

    def test_spdx_missing_supplier_returns_issue(self) -> None:
        sbom = parse_spdx(SPDX_FIXTURES / "missing-supplier.spdx.json")
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-04" for i in issues)

    def test_cdx_missing_supplier_returns_issue(self) -> None:
        sbom = parse_cyclonedx(CDX_FIXTURES / "missing-supplier.cdx.json")
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-04" for i in issues)

    def test_supplier_issue_references_component(self) -> None:
        """The FR-04 issue field_path must be non-empty (must name the component)."""
        sbom = parse_spdx(SPDX_FIXTURES / "missing-supplier.spdx.json")
        fr04_issues = [i for i in check_ntia(sbom) if i.rule == "FR-04"]
        assert len(fr04_issues) >= 1
        assert fr04_issues[0].field_path != ""

    def test_inline_supplier_none_detected(self) -> None:
        component = NormalizedComponent(
            component_id="pkg-1",
            name="some-pkg",
            version="1.0.0",
            supplier=None,
            identifiers=("pkg:pypi/some-pkg@1.0.0",),
        )
        sbom = _make_valid_sbom(components=(component,))
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-04" for i in issues)

    def test_valid_supplier_produces_no_fr04_issue(self) -> None:
        sbom = _make_valid_sbom()
        issues = check_ntia(sbom)
        assert not any(i.rule == "FR-04" for i in issues)


# ===========================================================================
# TestNtiaCheckerComponentName (FR-05)
# ===========================================================================


class TestNtiaCheckerComponentName:
    """FR-05: every component must have a non-empty name."""

    def test_inline_empty_name_detected(self) -> None:
        component = NormalizedComponent(
            component_id="pkg-1",
            name="",
            version="1.0.0",
            supplier="AcmeCorp",
            identifiers=("pkg:pypi/some-pkg@1.0.0",),
        )
        sbom = _make_valid_sbom(components=(component,))
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-05" for i in issues)

    def test_valid_name_produces_no_fr05_issue(self) -> None:
        sbom = _make_valid_sbom()
        issues = check_ntia(sbom)
        assert not any(i.rule == "FR-05" for i in issues)


# ===========================================================================
# TestNtiaCheckerVersion (FR-06)
# ===========================================================================


class TestNtiaCheckerVersion:
    """FR-06: every component must have a non-None version."""

    def test_spdx_missing_version_detected(self) -> None:
        """Construct a NormalizedSBOM with a component whose version is None."""
        component = NormalizedComponent(
            component_id="pkg-1",
            name="some-pkg",
            version=None,
            supplier="AcmeCorp",
            identifiers=("pkg:pypi/some-pkg@unknown",),
        )
        sbom = NormalizedSBOM(
            format="spdx",
            author="test-tool",
            timestamp="2024-01-01T00:00:00Z",
            components=(component,),
            relationships=(NormalizedRelationship(from_id="doc", to_id="pkg-1"),),
        )
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-06" for i in issues)

    def test_inline_version_none_detected(self) -> None:
        component = _make_valid_component(version=None)  # type: ignore[call-arg]
        sbom = _make_valid_sbom(components=(component,))
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-06" for i in issues)

    def test_valid_version_produces_no_fr06_issue(self) -> None:
        sbom = _make_valid_sbom()
        issues = check_ntia(sbom)
        assert not any(i.rule == "FR-06" for i in issues)

    def test_version_issue_references_component(self) -> None:
        component = _make_valid_component(version=None)  # type: ignore[call-arg]
        sbom = _make_valid_sbom(components=(component,))
        fr06_issues = [i for i in check_ntia(sbom) if i.rule == "FR-06"]
        assert len(fr06_issues) >= 1
        assert fr06_issues[0].field_path != ""


# ===========================================================================
# TestNtiaCheckerIdentifiers (FR-07)
# ===========================================================================


class TestNtiaCheckerIdentifiers:
    """FR-07: every component must have at least one entry in identifiers."""

    def test_spdx_missing_identifiers_detected(self) -> None:
        sbom = parse_spdx(SPDX_FIXTURES / "missing-identifiers.spdx.json")
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-07" for i in issues)

    def test_cdx_missing_identifiers_detected(self) -> None:
        sbom = parse_cyclonedx(CDX_FIXTURES / "missing-identifiers.cdx.json")
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-07" for i in issues)

    def test_inline_empty_identifiers_detected(self) -> None:
        component = NormalizedComponent(
            component_id="pkg-1",
            name="some-pkg",
            version="1.0.0",
            supplier="AcmeCorp",
            identifiers=(),
        )
        sbom = _make_valid_sbom(components=(component,))
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-07" for i in issues)

    def test_valid_identifiers_produce_no_fr07_issue(self) -> None:
        sbom = _make_valid_sbom()
        issues = check_ntia(sbom)
        assert not any(i.rule == "FR-07" for i in issues)

    def test_identifier_issue_references_component(self) -> None:
        component = NormalizedComponent(
            component_id="pkg-noref",
            name="noid-pkg",
            version="0.1.0",
            supplier="AcmeCorp",
            identifiers=(),
        )
        sbom = _make_valid_sbom(components=(component,))
        fr07_issues = [i for i in check_ntia(sbom) if i.rule == "FR-07"]
        assert len(fr07_issues) >= 1
        assert fr07_issues[0].field_path != ""


# ===========================================================================
# TestNtiaCheckerRelationships (FR-08)
# ===========================================================================


class TestNtiaCheckerRelationships:
    """FR-08: sbom.relationships must be non-empty."""

    def test_spdx_missing_relationships_detected(self) -> None:
        sbom = parse_spdx(SPDX_FIXTURES / "missing-relationships.spdx.json")
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-08" for i in issues)

    def test_cdx_missing_relationships_detected(self) -> None:
        sbom = parse_cyclonedx(CDX_FIXTURES / "missing-relationships.cdx.json")
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-08" for i in issues)

    def test_inline_empty_relationships_detected(self) -> None:
        sbom = _make_valid_sbom(relationships=())
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-08" for i in issues)

    def test_valid_relationships_produce_no_fr08_issue(self) -> None:
        sbom = _make_valid_sbom()
        issues = check_ntia(sbom)
        assert not any(i.rule == "FR-08" for i in issues)


# ===========================================================================
# TestNtiaCheckerAuthor (FR-09)
# ===========================================================================


class TestNtiaCheckerAuthor:
    """FR-09: sbom.author must not be None or empty string."""

    def test_missing_author_none_detected(self) -> None:
        sbom = _make_valid_sbom(author=None)
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-09" for i in issues)

    def test_missing_author_empty_string_detected(self) -> None:
        sbom = _make_valid_sbom(author="")
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-09" for i in issues)

    def test_missing_author_via_model_directly(self) -> None:
        """Explicit inline construction matches the spec in the task description."""
        component = NormalizedComponent(
            component_id="c1",
            name="pkg",
            version="1.0",
            supplier="Acme",
            identifiers=("pkg:pypi/pkg@1.0",),
        )
        sbom = NormalizedSBOM(
            format="spdx",
            author=None,
            timestamp="2024-01-01T00:00:00Z",
            components=(component,),
            relationships=(NormalizedRelationship(from_id="doc", to_id="c1"),),
        )
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-09" for i in issues)

    def test_valid_author_produces_no_fr09_issue(self) -> None:
        sbom = _make_valid_sbom(author="test-tool")
        issues = check_ntia(sbom)
        assert not any(i.rule == "FR-09" for i in issues)


# ===========================================================================
# TestNtiaCheckerTimestamp (FR-10)
# ===========================================================================


class TestNtiaCheckerTimestamp:
    """FR-10: sbom.timestamp must not be None or empty string."""

    def test_missing_timestamp_spdx_detected(self) -> None:
        sbom = parse_spdx(SPDX_FIXTURES / "missing-timestamp.spdx.json")
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-10" for i in issues)

    def test_missing_timestamp_cdx_detected(self) -> None:
        sbom = parse_cyclonedx(CDX_FIXTURES / "missing-timestamp.cdx.json")
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-10" for i in issues)

    def test_inline_timestamp_none_detected(self) -> None:
        sbom = _make_valid_sbom(timestamp=None)
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-10" for i in issues)

    def test_inline_timestamp_empty_string_detected(self) -> None:
        sbom = _make_valid_sbom(timestamp="")
        issues = check_ntia(sbom)
        assert any(i.rule == "FR-10" for i in issues)

    def test_valid_timestamp_produces_no_fr10_issue(self) -> None:
        sbom = _make_valid_sbom(timestamp="2024-01-15T10:30:00Z")
        issues = check_ntia(sbom)
        assert not any(i.rule == "FR-10" for i in issues)


# ===========================================================================
# TestNtiaCheckerCollectAll
# ===========================================================================


class TestNtiaCheckerCollectAll:
    """Structural and completeness tests for the checker as a whole."""

    def _make_maximally_broken_sbom(self) -> NormalizedSBOM:
        """Build an SBOM that fails FR-04, FR-06, FR-07, FR-08, FR-09, FR-10.

        The component has no supplier (FR-04), no version (FR-06), and no
        identifiers (FR-07).  The document has no relationships (FR-08), no
        author (FR-09), and no timestamp (FR-10).
        Note: FR-05 is satisfied because the component does have a name.
        """
        broken_component = NormalizedComponent(
            component_id="broken-pkg",
            name="broken-pkg",
            version=None,
            supplier=None,
            identifiers=(),
        )
        return NormalizedSBOM(
            format="spdx",
            author=None,
            timestamp=None,
            components=(broken_component,),
            relationships=(),
        )

    def test_multiple_issues_all_reported(self) -> None:
        """All six failing rules must appear in the returned issue list."""
        sbom = self._make_maximally_broken_sbom()
        issues = check_ntia(sbom)
        rules_found = {i.rule for i in issues}
        for expected_rule in ("FR-04", "FR-06", "FR-07", "FR-08", "FR-09", "FR-10"):
            assert (
                expected_rule in rules_found
            ), f"{expected_rule} not reported; rules found: {rules_found}"

    def test_each_issue_has_severity_error(self) -> None:
        """Every issue returned by check_ntia must carry ERROR severity."""
        sbom = self._make_maximally_broken_sbom()
        issues = check_ntia(sbom)
        assert len(issues) > 0, "Expected at least one issue from a broken SBOM"
        for issue in issues:
            assert (
                issue.severity == IssueSeverity.ERROR
            ), f"Issue {issue.rule!r} has severity {issue.severity!r}; expected ERROR"

    def test_each_issue_has_non_empty_message(self) -> None:
        """Every issue must carry a non-empty human-readable message."""
        sbom = self._make_maximally_broken_sbom()
        issues = check_ntia(sbom)
        assert len(issues) > 0, "Expected at least one issue from a broken SBOM"
        for issue in issues:
            assert issue.message != "", f"Issue {issue.rule!r} has an empty message"

    def test_returns_list_type(self) -> None:
        """check_ntia must return a plain list, not a tuple or generator."""
        sbom = _make_valid_sbom()
        result = check_ntia(sbom)
        assert isinstance(result, list), f"Expected list, got {type(result).__name__}"

    def test_returns_list_of_validation_issue_instances(self) -> None:
        """Every element in the returned list must be a ValidationIssue."""
        sbom = self._make_maximally_broken_sbom()
        issues = check_ntia(sbom)
        for item in issues:
            assert isinstance(
                item, ValidationIssue
            ), f"Expected ValidationIssue, got {type(item).__name__}"

    def test_each_issue_has_non_empty_rule(self) -> None:
        """Every issue must carry a non-empty rule identifier (e.g., 'FR-04')."""
        sbom = self._make_maximally_broken_sbom()
        issues = check_ntia(sbom)
        assert len(issues) > 0, "Expected at least one issue from a broken SBOM"
        for issue in issues:
            assert issue.rule != "", f"An issue has an empty rule field: {issue}"

    def test_no_duplicate_rules_for_document_level_checks(self) -> None:
        """FR-08, FR-09, FR-10 are document-level: each should appear at most once."""
        sbom = self._make_maximally_broken_sbom()
        issues = check_ntia(sbom)
        for doc_level_rule in ("FR-08", "FR-09", "FR-10"):
            count = sum(1 for i in issues if i.rule == doc_level_rule)
            assert count <= 1, f"{doc_level_rule} appeared {count} times; expected at most 1"

    def test_per_component_rules_reported_once_per_component(self) -> None:
        """FR-04, FR-06, FR-07 are per-component: two broken components → two issues each."""
        c1 = NormalizedComponent(
            component_id="c1",
            name="pkg-a",
            version=None,
            supplier=None,
            identifiers=(),
        )
        c2 = NormalizedComponent(
            component_id="c2",
            name="pkg-b",
            version=None,
            supplier=None,
            identifiers=(),
        )
        sbom = NormalizedSBOM(
            format="spdx",
            author="test-tool",
            timestamp="2024-01-01T00:00:00Z",
            components=(c1, c2),
            relationships=(NormalizedRelationship(from_id="doc", to_id="c1"),),
        )
        issues = check_ntia(sbom)
        for per_component_rule in ("FR-04", "FR-06", "FR-07"):
            count = sum(1 for i in issues if i.rule == per_component_rule)
            assert count == 2, (
                f"{per_component_rule} reported {count} time(s); expected 2 "
                f"(one per broken component)"
            )

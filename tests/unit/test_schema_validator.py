"""Unit tests for sbom_validator.schema_validator.validate_schema (Task 2.E1).

These tests are written TDD-style and will FAIL until the developer implements
validate_schema in src/sbom_validator/schema_validator.py.

Function under test
-------------------
    validate_schema(raw_doc: dict, format_name: str) -> list[ValidationIssue]

Contract:
- Accepts a parsed JSON dict (not a file path) and a format string ("spdx" or
  "cyclonedx").
- Returns an empty list when the document is schema-valid.
- Returns one or more ValidationIssue objects when the document violates the
  schema.
- Raises ValueError for an unrecognised format_name.
- Every issue produced for an SPDX document carries rule="FR-02".
- Every issue produced for a CycloneDX document carries rule="FR-03".
- All issues have severity=IssueSeverity.ERROR.
- All schema violations are collected in a single pass (non-fail-fast, FR-14).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from sbom_validator.models import IssueSeverity, ValidationIssue
from sbom_validator.schema_validator import validate_schema

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def spdx_fixtures() -> Path:
    return FIXTURES_DIR / "spdx"


@pytest.fixture
def cdx_fixtures() -> Path:
    return FIXTURES_DIR / "cyclonedx"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict:
    """Load a JSON fixture file and return the parsed dict."""
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# TestValidateSchemaSPDX
# ---------------------------------------------------------------------------


class TestValidateSchemaSPDX:
    """Schema-validation tests for SPDX 2.3 JSON documents (FR-02)."""

    def test_valid_spdx_minimal_returns_empty_list(self, spdx_fixtures: Path) -> None:
        """A well-formed minimal SPDX document must produce no issues."""
        doc = _load(spdx_fixtures / "valid-minimal.spdx.json")
        result = validate_schema(doc, "spdx")
        assert result == []

    def test_valid_spdx_full_returns_empty_list(self, spdx_fixtures: Path) -> None:
        """A well-formed full SPDX document with multiple packages must produce no issues."""
        doc = _load(spdx_fixtures / "valid-full.spdx.json")
        result = validate_schema(doc, "spdx")
        assert result == []

    def test_invalid_spdx_returns_issues(self, spdx_fixtures: Path) -> None:
        """A schema-invalid SPDX document must produce at least one issue."""
        doc = _load(spdx_fixtures / "invalid-schema.spdx.json")
        result = validate_schema(doc, "spdx")
        assert len(result) > 0

    def test_invalid_spdx_issues_have_error_severity(self, spdx_fixtures: Path) -> None:
        """Every issue reported for a schema-invalid SPDX document must have ERROR severity."""
        doc = _load(spdx_fixtures / "invalid-schema.spdx.json")
        result = validate_schema(doc, "spdx")
        assert len(result) > 0, "Expected at least one issue for invalid-schema fixture"
        for issue in result:
            assert (
                issue.severity == IssueSeverity.ERROR
            ), f"Expected severity ERROR, got {issue.severity!r} for issue: {issue}"

    def test_invalid_spdx_issues_have_non_empty_message(self, spdx_fixtures: Path) -> None:
        """Every issue reported for a schema-invalid SPDX document must carry a
        non-empty, human-readable message string."""
        doc = _load(spdx_fixtures / "invalid-schema.spdx.json")
        result = validate_schema(doc, "spdx")
        assert len(result) > 0, "Expected at least one issue for invalid-schema fixture"
        for issue in result:
            assert isinstance(
                issue.message, str
            ), f"issue.message must be a str, got {type(issue.message)}"
            assert issue.message.strip() != "", "issue.message must not be empty or whitespace-only"

    def test_invalid_spdx_issues_have_rule_fr02(self, spdx_fixtures: Path) -> None:
        """Every issue reported for a schema-invalid SPDX document must reference FR-02."""
        doc = _load(spdx_fixtures / "invalid-schema.spdx.json")
        result = validate_schema(doc, "spdx")
        assert len(result) > 0, "Expected at least one issue for invalid-schema fixture"
        for issue in result:
            assert (
                issue.rule == "FR-02"
            ), f"Expected rule 'FR-02', got {issue.rule!r} for issue: {issue}"

    def test_invalid_spdx_issues_have_field_path(self, spdx_fixtures: Path) -> None:
        """Every issue reported for a schema-invalid SPDX document must carry a
        non-empty field_path identifying the problem location."""
        doc = _load(spdx_fixtures / "invalid-schema.spdx.json")
        result = validate_schema(doc, "spdx")
        assert len(result) > 0, "Expected at least one issue for invalid-schema fixture"
        for issue in result:
            assert isinstance(
                issue.field_path, str
            ), f"issue.field_path must be a str, got {type(issue.field_path)}"
            assert (
                issue.field_path.strip() != ""
            ), "issue.field_path must not be empty or whitespace-only"


# ---------------------------------------------------------------------------
# TestValidateSchemaCycloneDX
# ---------------------------------------------------------------------------


class TestValidateSchemaCycloneDX:
    """Schema-validation tests for CycloneDX 1.6 JSON documents (FR-03)."""

    def test_valid_cyclonedx_minimal_returns_empty_list(self, cdx_fixtures: Path) -> None:
        """A well-formed minimal CycloneDX document must produce no issues."""
        doc = _load(cdx_fixtures / "valid-minimal.cdx.json")
        result = validate_schema(doc, "cyclonedx")
        assert result == []

    def test_valid_cyclonedx_full_returns_empty_list(self, cdx_fixtures: Path) -> None:
        """A well-formed full CycloneDX document with multiple components must
        produce no issues."""
        doc = _load(cdx_fixtures / "valid-full.cdx.json")
        result = validate_schema(doc, "cyclonedx")
        assert result == []

    def test_invalid_cyclonedx_returns_issues(self, cdx_fixtures: Path) -> None:
        """A schema-invalid CycloneDX document must produce at least one issue."""
        doc = _load(cdx_fixtures / "invalid-schema.cdx.json")
        result = validate_schema(doc, "cyclonedx")
        assert len(result) > 0

    def test_invalid_cyclonedx_issues_have_error_severity(self, cdx_fixtures: Path) -> None:
        """Every issue reported for a schema-invalid CycloneDX document must have
        ERROR severity."""
        doc = _load(cdx_fixtures / "invalid-schema.cdx.json")
        result = validate_schema(doc, "cyclonedx")
        assert len(result) > 0, "Expected at least one issue for invalid-schema fixture"
        for issue in result:
            assert (
                issue.severity == IssueSeverity.ERROR
            ), f"Expected severity ERROR, got {issue.severity!r} for issue: {issue}"

    def test_invalid_cyclonedx_issues_have_non_empty_message(self, cdx_fixtures: Path) -> None:
        """Every issue reported for a schema-invalid CycloneDX document must carry a
        non-empty, human-readable message string."""
        doc = _load(cdx_fixtures / "invalid-schema.cdx.json")
        result = validate_schema(doc, "cyclonedx")
        assert len(result) > 0, "Expected at least one issue for invalid-schema fixture"
        for issue in result:
            assert isinstance(
                issue.message, str
            ), f"issue.message must be a str, got {type(issue.message)}"
            assert issue.message.strip() != "", "issue.message must not be empty or whitespace-only"

    def test_invalid_cyclonedx_issues_have_rule_fr03(self, cdx_fixtures: Path) -> None:
        """Every issue reported for a schema-invalid CycloneDX document must reference FR-03."""
        doc = _load(cdx_fixtures / "invalid-schema.cdx.json")
        result = validate_schema(doc, "cyclonedx")
        assert len(result) > 0, "Expected at least one issue for invalid-schema fixture"
        for issue in result:
            assert (
                issue.rule == "FR-03"
            ), f"Expected rule 'FR-03', got {issue.rule!r} for issue: {issue}"

    def test_invalid_cyclonedx_issues_have_field_path(self, cdx_fixtures: Path) -> None:
        """Every issue reported for a schema-invalid CycloneDX document must carry a
        non-empty field_path identifying the problem location."""
        doc = _load(cdx_fixtures / "invalid-schema.cdx.json")
        result = validate_schema(doc, "cyclonedx")
        assert len(result) > 0, "Expected at least one issue for invalid-schema fixture"
        for issue in result:
            assert isinstance(
                issue.field_path, str
            ), f"issue.field_path must be a str, got {type(issue.field_path)}"
            assert (
                issue.field_path.strip() != ""
            ), "issue.field_path must not be empty or whitespace-only"


# ---------------------------------------------------------------------------
# TestValidateSchemaReturnType
# ---------------------------------------------------------------------------


class TestValidateSchemaReturnType:
    """Tests that verify the return type contract of validate_schema."""

    def test_returns_list_for_valid_spdx(self, spdx_fixtures: Path) -> None:
        """validate_schema must return a list (not a generator, tuple, or other
        iterable) even when the document is valid."""
        doc = _load(spdx_fixtures / "valid-minimal.spdx.json")
        result = validate_schema(doc, "spdx")
        assert isinstance(result, list), f"Expected list, got {type(result).__name__}"

    def test_returns_list_for_valid_cyclonedx(self, cdx_fixtures: Path) -> None:
        """validate_schema must return a list for a valid CycloneDX document."""
        doc = _load(cdx_fixtures / "valid-minimal.cdx.json")
        result = validate_schema(doc, "cyclonedx")
        assert isinstance(result, list), f"Expected list, got {type(result).__name__}"

    def test_returns_list_for_invalid_spdx(self, spdx_fixtures: Path) -> None:
        """validate_schema must return a list even when the document is invalid."""
        doc = _load(spdx_fixtures / "invalid-schema.spdx.json")
        result = validate_schema(doc, "spdx")
        assert isinstance(result, list), f"Expected list, got {type(result).__name__}"

    def test_issues_are_validation_issue_instances(self, spdx_fixtures: Path) -> None:
        """Each item in the returned list must be a ValidationIssue instance."""
        doc = _load(spdx_fixtures / "invalid-schema.spdx.json")
        result = validate_schema(doc, "spdx")
        assert len(result) > 0, "Expected at least one issue for invalid-schema fixture"
        for item in result:
            assert isinstance(
                item, ValidationIssue
            ), f"Expected ValidationIssue instance, got {type(item).__name__}: {item!r}"

    def test_unknown_format_raises_value_error(self) -> None:
        """Passing an unrecognised format_name must raise ValueError."""
        with pytest.raises(ValueError):
            validate_schema({}, "unknown")

    def test_unknown_format_raises_value_error_with_arbitrary_string(self) -> None:
        """Any non-supported format string must raise ValueError, not silently
        return an empty list or produce a schema issue."""
        with pytest.raises(ValueError):
            validate_schema({"spdxVersion": "SPDX-2.3"}, "xml")

    def test_empty_dict_spdx_returns_issues(self) -> None:
        """An empty dict is not a valid SPDX document; validate_schema must
        return at least one issue rather than an empty list."""
        result = validate_schema({}, "spdx")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_empty_dict_cyclonedx_returns_issues(self) -> None:
        """An empty dict is not a valid CycloneDX document; validate_schema must
        return at least one issue rather than an empty list."""
        result = validate_schema({}, "cyclonedx")
        assert isinstance(result, list)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# TestValidateSchemaCollectsAll
# ---------------------------------------------------------------------------


class TestValidateSchemaCollectsAll:
    """Tests verifying the non-fail-fast (collect-all) behaviour mandated by
    FR-14 for schema validation."""

    def test_spdx_multiple_violations_all_reported(self) -> None:
        """A document missing multiple required SPDX root properties must
        produce at least one issue per missing property (i.e. >= 2 issues).

        The invalid-schema.spdx.json fixture is missing spdxVersion and the
        package SPDXID, but here we craft an even more broken document to be
        explicit about the collect-all requirement.
        """
        # Missing: spdxVersion, SPDXID, dataLicense — three required root fields
        doc: dict = {
            "name": "broken-spdx",
            "documentNamespace": "https://example.com/broken",
            "creationInfo": {
                "created": "2024-01-15T10:00:00Z",
                "creators": ["Tool: test"],
            },
            "packages": [],
            "relationships": [],
        }
        result = validate_schema(doc, "spdx")
        assert isinstance(result, list)
        assert (
            len(result) >= 2
        ), f"Expected >= 2 schema issues (collect-all), got {len(result)}: {result}"

    def test_cyclonedx_multiple_violations_all_reported(self) -> None:
        """A document missing multiple required CycloneDX root properties must
        produce at least one issue per missing property (i.e. >= 2 issues)."""
        # Missing: bomFormat, specVersion — two required root fields
        doc: dict = {
            "version": 1,
            "serialNumber": "urn:uuid:3e671687-395b-41f5-a30f-a58921a69b79",
            "metadata": {
                "timestamp": "2024-01-15T10:00:00Z",
            },
            "components": [],
        }
        result = validate_schema(doc, "cyclonedx")
        assert isinstance(result, list)
        assert (
            len(result) >= 2
        ), f"Expected >= 2 schema issues (collect-all), got {len(result)}: {result}"

    def test_spdx_invalid_fixture_all_issues_use_fr02(self, spdx_fixtures: Path) -> None:
        """When multiple schema issues are collected for an SPDX document, all
        of them must use FR-02 (not a mix of FR-02 and FR-03)."""
        doc = _load(spdx_fixtures / "invalid-schema.spdx.json")
        result = validate_schema(doc, "spdx")
        assert len(result) > 0
        rules = {issue.rule for issue in result}
        assert rules == {"FR-02"}, f"Expected only FR-02 issues for SPDX, got rules: {rules}"

    def test_cyclonedx_invalid_fixture_all_issues_use_fr03(self, cdx_fixtures: Path) -> None:
        """When multiple schema issues are collected for a CycloneDX document,
        all of them must use FR-03 (not a mix)."""
        doc = _load(cdx_fixtures / "invalid-schema.cdx.json")
        result = validate_schema(doc, "cyclonedx")
        assert len(result) > 0
        rules = {issue.rule for issue in result}
        assert rules == {"FR-03"}, f"Expected only FR-03 issues for CycloneDX, got rules: {rules}"

    def test_spdx_no_issues_for_different_format_name(self, cdx_fixtures: Path) -> None:
        """A valid CycloneDX document passed as "spdx" must NOT return an
        empty list — it should fail schema validation because it lacks required
        SPDX fields such as spdxVersion and dataLicense."""
        doc = _load(cdx_fixtures / "valid-minimal.cdx.json")
        result = validate_schema(doc, "spdx")
        assert isinstance(result, list)
        assert len(result) > 0, "A CycloneDX document validated as SPDX must produce schema errors"


# ---------------------------------------------------------------------------
# TestSchemaValidatorFrozenPath
# ---------------------------------------------------------------------------


class TestSchemaValidatorFrozenPath:
    """_schemas_dir() returns the PyInstaller _MEIPASS path when sys.frozen is set.

    Covers lines 25-26 of schema_validator.py (_schemas_dir frozen branch).
    """

    def test_frozen_mode_uses_meipass_schemas_dir(self, tmp_path: Path) -> None:
        """When sys.frozen == True and sys._MEIPASS is set, _schemas_dir() must
        return Path(_MEIPASS) / 'schemas' rather than the package path."""
        from sbom_validator.schema_validator import _schemas_dir

        fake_meipass = str(tmp_path / "pyinstaller_bundle")
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", fake_meipass, create=True),
        ):
            result = _schemas_dir()

        assert result == Path(fake_meipass) / "schemas"

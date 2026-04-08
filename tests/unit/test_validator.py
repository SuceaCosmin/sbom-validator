"""TDD unit tests for the validator orchestrator (Task 2.G1).

These tests are written BEFORE the orchestrator is implemented and are expected
to FAIL until the developer implements validate() in
sbom_validator/validator.py.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sbom_validator.models import ValidationResult, ValidationStatus
from sbom_validator.validator import validate

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

SPDX_FIXTURES = Path("tests/fixtures/spdx")
CDX_FIXTURES = Path("tests/fixtures/cyclonedx")


# ===========================================================================
# TestValidatorPassScenarios
# ===========================================================================


class TestValidatorPassScenarios:
    """validate() returns PASS for fully valid, NTIA-compliant SBOM files."""

    def test_valid_spdx_minimal_returns_pass(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert result.status == ValidationStatus.PASS

    def test_valid_spdx_minimal_has_no_issues(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert result.issues == ()

    def test_valid_spdx_full_returns_pass(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-full.spdx.json")
        assert result.status == ValidationStatus.PASS

    def test_valid_spdx_full_has_no_issues(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-full.spdx.json")
        assert result.issues == ()

    def test_valid_cyclonedx_minimal_returns_pass(self) -> None:
        result = validate(CDX_FIXTURES / "valid-minimal.cdx.json")
        assert result.status == ValidationStatus.PASS

    def test_valid_cyclonedx_minimal_has_no_issues(self) -> None:
        result = validate(CDX_FIXTURES / "valid-minimal.cdx.json")
        assert result.issues == ()

    def test_valid_cyclonedx_full_returns_pass(self) -> None:
        result = validate(CDX_FIXTURES / "valid-full.cdx.json")
        assert result.status == ValidationStatus.PASS

    def test_valid_cyclonedx_full_has_no_issues(self) -> None:
        result = validate(CDX_FIXTURES / "valid-full.cdx.json")
        assert result.issues == ()

    def test_pass_result_has_correct_file_path(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert "valid-minimal.spdx.json" in result.file_path

    def test_pass_result_has_format_detected_spdx(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert result.format_detected == "spdx"

    def test_pass_cyclonedx_has_format_detected(self) -> None:
        result = validate(CDX_FIXTURES / "valid-minimal.cdx.json")
        assert result.format_detected == "cyclonedx"

    def test_pass_result_status_is_pass_not_fail(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert result.status != ValidationStatus.FAIL
        assert result.status != ValidationStatus.ERROR


# ===========================================================================
# TestValidatorSchemaFailScenarios
# ===========================================================================


class TestValidatorSchemaFailScenarios:
    """validate() returns FAIL (with schema issues) when the SBOM document
    does not conform to its format's JSON schema.  The NTIA stage must NOT
    run in this case.
    """

    def test_invalid_spdx_schema_returns_fail(self) -> None:
        result = validate(SPDX_FIXTURES / "invalid-schema.spdx.json")
        assert result.status == ValidationStatus.FAIL

    def test_invalid_spdx_schema_has_issues(self) -> None:
        result = validate(SPDX_FIXTURES / "invalid-schema.spdx.json")
        assert len(result.issues) > 0

    def test_invalid_spdx_schema_issues_have_fr02_rule(self) -> None:
        result = validate(SPDX_FIXTURES / "invalid-schema.spdx.json")
        assert all(i.rule == "FR-02" for i in result.issues)

    def test_invalid_cdx_schema_returns_fail(self) -> None:
        result = validate(CDX_FIXTURES / "invalid-schema.cdx.json")
        assert result.status == ValidationStatus.FAIL

    def test_invalid_cdx_schema_has_issues(self) -> None:
        result = validate(CDX_FIXTURES / "invalid-schema.cdx.json")
        assert len(result.issues) > 0

    def test_invalid_cdx_schema_issues_have_fr03_rule(self) -> None:
        result = validate(CDX_FIXTURES / "invalid-schema.cdx.json")
        assert all(i.rule == "FR-03" for i in result.issues)

    def test_schema_fail_has_no_ntia_issues(self) -> None:
        # When schema fails, NTIA is NOT run — so no FR-04 through FR-10 issues
        result = validate(SPDX_FIXTURES / "invalid-schema.spdx.json")
        ntia_rules = {"FR-04", "FR-05", "FR-06", "FR-07", "FR-08", "FR-09", "FR-10"}
        issue_rules = {i.rule for i in result.issues}
        assert issue_rules.isdisjoint(ntia_rules)

    def test_invalid_spdx_schema_format_detected_is_spdx(self) -> None:
        result = validate(SPDX_FIXTURES / "invalid-schema.spdx.json")
        assert result.format_detected == "spdx"

    def test_invalid_cdx_schema_format_detected_is_cyclonedx(self) -> None:
        result = validate(CDX_FIXTURES / "invalid-schema.cdx.json")
        assert result.format_detected == "cyclonedx"


# ===========================================================================
# TestValidatorNtiaFailScenarios
# ===========================================================================


class TestValidatorNtiaFailScenarios:
    """validate() returns FAIL (with NTIA issues) when the SBOM is
    schema-valid but is missing required NTIA minimum elements.
    """

    def test_missing_supplier_spdx_returns_fail(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        assert result.status == ValidationStatus.FAIL

    def test_missing_supplier_has_fr04_issue(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        assert any(i.rule == "FR-04" for i in result.issues)

    def test_missing_timestamp_spdx_returns_fail(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-timestamp.spdx.json")
        assert result.status == ValidationStatus.FAIL

    def test_missing_timestamp_has_fr10_issue(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-timestamp.spdx.json")
        assert any(i.rule == "FR-10" for i in result.issues)

    def test_missing_relationships_spdx_returns_fail(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-relationships.spdx.json")
        assert result.status == ValidationStatus.FAIL

    def test_missing_relationships_has_fr08_issue(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-relationships.spdx.json")
        assert any(i.rule == "FR-08" for i in result.issues)

    def test_missing_identifiers_spdx_returns_fail(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-identifiers.spdx.json")
        assert result.status == ValidationStatus.FAIL

    def test_missing_identifiers_has_fr07_issue(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-identifiers.spdx.json")
        assert any(i.rule == "FR-07" for i in result.issues)

    def test_missing_supplier_cdx_returns_fail(self) -> None:
        result = validate(CDX_FIXTURES / "missing-supplier.cdx.json")
        assert result.status == ValidationStatus.FAIL

    def test_missing_timestamp_cdx_returns_fail(self) -> None:
        result = validate(CDX_FIXTURES / "missing-timestamp.cdx.json")
        assert result.status == ValidationStatus.FAIL

    def test_missing_relationships_cdx_returns_fail(self) -> None:
        result = validate(CDX_FIXTURES / "missing-relationships.cdx.json")
        assert result.status == ValidationStatus.FAIL

    def test_missing_identifiers_cdx_returns_fail(self) -> None:
        result = validate(CDX_FIXTURES / "missing-identifiers.cdx.json")
        assert result.status == ValidationStatus.FAIL

    def test_ntia_fail_has_no_schema_issues(self) -> None:
        # When schema passes but NTIA fails, there are no FR-02 or FR-03 issues
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        assert not any(i.rule in ("FR-02", "FR-03") for i in result.issues)

    def test_all_ntia_failures_collected(self) -> None:
        # A doc missing multiple NTIA elements should have multiple issues;
        # at minimum FR-04 is reported for missing-supplier
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        assert len(result.issues) >= 1

    def test_ntia_fail_format_detected_is_spdx(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        assert result.format_detected == "spdx"

    def test_ntia_fail_file_path_recorded(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        assert "missing-supplier.spdx.json" in result.file_path

    def test_ntia_issues_do_not_include_fr02_or_fr03(self) -> None:
        # Any NTIA-only fixture must produce no schema-rule issues
        for fixture in (
            SPDX_FIXTURES / "missing-timestamp.spdx.json",
            SPDX_FIXTURES / "missing-relationships.spdx.json",
            SPDX_FIXTURES / "missing-identifiers.spdx.json",
        ):
            result = validate(fixture)
            for issue in result.issues:
                assert issue.rule not in (
                    "FR-02",
                    "FR-03",
                ), f"Unexpected schema rule {issue.rule} for fixture {fixture}"


# ===========================================================================
# TestValidatorErrorScenarios
# ===========================================================================


class TestValidatorErrorScenarios:
    """validate() returns ERROR (never raises) for all unrecoverable input
    problems: missing file, bad JSON, unrecognised format, parse failure.
    """

    def test_nonexistent_file_returns_error(self, tmp_path: Path) -> None:
        result = validate(tmp_path / "nonexistent.json")
        assert result.status == ValidationStatus.ERROR

    def test_nonexistent_file_does_not_raise(self, tmp_path: Path) -> None:
        # The orchestrator must convert all exceptions to ERROR results
        try:
            validate(tmp_path / "nonexistent.json")
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"validate() raised unexpectedly: {exc}")

    def test_nonexistent_file_issues_is_tuple(self, tmp_path: Path) -> None:
        result = validate(tmp_path / "nonexistent.json")
        assert isinstance(result.issues, tuple)

    def test_invalid_json_file_returns_error(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json", encoding="utf-8")
        result = validate(bad_file)
        assert result.status == ValidationStatus.ERROR

    def test_invalid_json_does_not_raise(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json", encoding="utf-8")
        try:
            validate(bad_file)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"validate() raised unexpectedly: {exc}")

    def test_unknown_format_returns_error(self, tmp_path: Path) -> None:
        unknown = tmp_path / "unknown.json"
        unknown.write_text('{"neither": "spdx nor cyclonedx"}', encoding="utf-8")
        result = validate(unknown)
        assert result.status == ValidationStatus.ERROR

    def test_unknown_format_does_not_raise(self, tmp_path: Path) -> None:
        unknown = tmp_path / "unknown.json"
        unknown.write_text('{"neither": "spdx nor cyclonedx"}', encoding="utf-8")
        try:
            validate(unknown)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"validate() raised unexpectedly: {exc}")

    def test_error_result_format_detected_is_none_for_unknown_format(self, tmp_path: Path) -> None:
        unknown = tmp_path / "unknown.json"
        unknown.write_text('{"neither": "spdx nor cyclonedx"}', encoding="utf-8")
        result = validate(unknown)
        assert result.format_detected is None

    def test_error_result_format_detected_is_none_for_nonexistent_file(
        self, tmp_path: Path
    ) -> None:
        result = validate(tmp_path / "nonexistent.json")
        assert result.format_detected is None

    def test_error_result_has_correct_file_path(self, tmp_path: Path) -> None:
        unknown = tmp_path / "my-unknown.json"
        unknown.write_text('{"neither": "spdx nor cyclonedx"}', encoding="utf-8")
        result = validate(unknown)
        assert "my-unknown.json" in result.file_path

    def test_empty_json_object_returns_error(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.json"
        empty.write_text("{}", encoding="utf-8")
        result = validate(empty)
        assert result.status == ValidationStatus.ERROR

    def test_json_array_returns_error(self, tmp_path: Path) -> None:
        arr = tmp_path / "array.json"
        arr.write_text("[1, 2, 3]", encoding="utf-8")
        result = validate(arr)
        assert result.status == ValidationStatus.ERROR


# ===========================================================================
# TestValidatorResultStructure
# ===========================================================================


class TestValidatorResultStructure:
    """validate() always returns a properly typed ValidationResult regardless
    of the outcome.
    """

    def test_result_is_validation_result_instance(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert isinstance(result, ValidationResult)

    def test_result_issues_is_tuple_on_pass(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert isinstance(result.issues, tuple)

    def test_result_issues_is_tuple_on_fail(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        assert isinstance(result.issues, tuple)

    def test_result_issues_is_tuple_on_schema_fail(self) -> None:
        result = validate(SPDX_FIXTURES / "invalid-schema.spdx.json")
        assert isinstance(result.issues, tuple)

    def test_result_is_validation_result_on_error(self, tmp_path: Path) -> None:
        result = validate(tmp_path / "nonexistent.json")
        assert isinstance(result, ValidationResult)

    def test_result_status_is_validation_status_enum(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert isinstance(result.status, ValidationStatus)

    def test_result_file_path_is_str(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert isinstance(result.file_path, str)

    def test_result_format_detected_is_str_or_none_on_pass(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert result.format_detected is None or isinstance(result.format_detected, str)

    def test_pass_result_issues_is_empty_tuple(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert result.issues == ()

    def test_pass_result_issues_length_is_zero(self) -> None:
        result = validate(SPDX_FIXTURES / "valid-minimal.spdx.json")
        assert len(result.issues) == 0

    def test_each_issue_has_rule_attribute(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        for issue in result.issues:
            assert hasattr(issue, "rule")

    def test_each_issue_has_message_attribute(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        for issue in result.issues:
            assert hasattr(issue, "message")

    def test_each_issue_has_severity_attribute(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        for issue in result.issues:
            assert hasattr(issue, "severity")

    def test_each_issue_has_field_path_attribute(self) -> None:
        result = validate(SPDX_FIXTURES / "missing-supplier.spdx.json")
        for issue in result.issues:
            assert hasattr(issue, "field_path")


# ===========================================================================
# TestValidatorUnexpectedExceptions
# ===========================================================================


class TestValidatorUnexpectedExceptions:
    """validate() converts unexpected (non-domain) exceptions to ERROR results
    at each pipeline stage, and never lets them propagate to the caller.

    Covers lines 55-57, 75-77, and 111-113 of validator.py.
    """

    def test_unexpected_exception_in_detect_format_returns_error(self, tmp_path: Path) -> None:
        """An unexpected exception (not ParseError/UnsupportedFormatError) raised
        inside detect_format must be caught at lines 55-57 and returned as an
        ERROR ValidationResult with an issue describing the error.
        """
        # Arrange: a valid JSON file so the file-not-found path is not taken,
        # but patch detect_format to raise a generic RuntimeError.
        f = tmp_path / "any.json"
        f.write_text("{}", encoding="utf-8")
        with patch(
            "sbom_validator.validator.detect_format",
            side_effect=RuntimeError("unexpected boom"),
        ):
            result = validate(f)

        assert result.status == ValidationStatus.ERROR
        assert len(result.issues) == 1
        assert "unexpected boom" in result.issues[0].message
        assert result.format_detected is None

    def test_unexpected_exception_in_detect_format_does_not_raise(self, tmp_path: Path) -> None:
        """validate() must not propagate a RuntimeError from detect_format."""
        f = tmp_path / "any.json"
        f.write_text("{}", encoding="utf-8")
        with patch(
            "sbom_validator.validator.detect_format",
            side_effect=RuntimeError("boom"),
        ):
            try:
                validate(f)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"validate() raised unexpectedly: {exc}")

    def test_unexpected_exception_reading_raw_json_returns_error(self, tmp_path: Path) -> None:
        """An unexpected exception raised while reading the raw JSON (lines 75-77)
        must be returned as an ERROR ValidationResult with format_detected set.

        Stage 0 (detect_format) reads the file independently; Stage 1 calls
        file_path.read_text() again to decode the raw JSON.  We patch
        Path.read_text so the *second* call (inside the validator) raises an
        OSError, while the first call (inside detect_format) succeeds normally.
        """
        valid_spdx = SPDX_FIXTURES / "valid-minimal.spdx.json"
        original_read_text = Path.read_text
        call_count = {"n": 0}

        def read_text_side_effect(self, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # First call is from detect_format — let it succeed.
                return original_read_text(self, *args, **kwargs)
            # Second call is Stage 1 inside validate() — raise unexpectedly.
            raise RuntimeError("read_text boom on second call")

        with patch.object(Path, "read_text", read_text_side_effect):
            result = validate(valid_spdx)

        assert result.status == ValidationStatus.ERROR
        assert len(result.issues) == 1
        assert "read_text boom on second call" in result.issues[0].message
        # format_detected must be set because Stage 0 already passed
        assert result.format_detected == "spdx"

    def test_parse_error_from_parser_after_schema_pass_returns_error(self, tmp_path: Path) -> None:
        """A ParseError raised by parse_spdx / parse_cyclonedx after schema
        validation passes must be caught at lines 111-113 and returned as an
        ERROR ValidationResult (covers the ParseError branch in Stage 3).
        """
        from sbom_validator.exceptions import ParseError

        valid_spdx = SPDX_FIXTURES / "valid-minimal.spdx.json"
        with patch(
            "sbom_validator.validator.parse_spdx",
            side_effect=ParseError("parser blew up"),
        ):
            result = validate(valid_spdx)

        assert result.status == ValidationStatus.ERROR
        assert len(result.issues) == 1
        assert "parser blew up" in result.issues[0].message
        assert result.format_detected == "spdx"

    def test_parse_error_from_parser_does_not_raise(self, tmp_path: Path) -> None:
        """validate() must not propagate a ParseError from the parser stage."""
        from sbom_validator.exceptions import ParseError

        valid_spdx = SPDX_FIXTURES / "valid-minimal.spdx.json"
        with patch(
            "sbom_validator.validator.parse_spdx",
            side_effect=ParseError("parser blew up"),
        ):
            try:
                validate(valid_spdx)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"validate() raised unexpectedly: {exc}")

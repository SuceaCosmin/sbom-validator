"""Unit tests for the CLI (Task 3.1).

These tests are written TDD-style: they define the expected behaviour of the
fully-implemented CLI and will FAIL until the Developer completes the
implementation in ``sbom_validator/cli.py``.

Test layout
-----------
TestCliVersion              -- --version flag
TestCliHelp                 -- --help / validate --help
TestCliValidatePassTextOutput  -- text output, passing files
TestCliValidateFailTextOutput  -- text output, failing files
TestCliValidateErrorCases   -- error cases (exit 2)
TestCliJsonOutputPass       -- --format json, passing file
TestCliJsonOutputFail       -- --format json, failing file
TestCliJsonOutputError      -- --format json, error conditions
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from sbom_validator.cli import main

# ---------------------------------------------------------------------------
# Fixture root paths
# ---------------------------------------------------------------------------

SPDX_FIXTURES = Path("tests/fixtures/spdx")
CDX_FIXTURES = Path("tests/fixtures/cyclonedx")


# ---------------------------------------------------------------------------
# Shared pytest fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    """Return a Click CliRunner for invoking the CLI in tests."""
    return CliRunner()


# ===========================================================================
# TestCliVersion
# ===========================================================================


class TestCliVersion:
    """Tests for the ``--version`` flag."""

    def test_version_flag_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0

    def test_version_output_contains_version_string(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert "0.1.0" in result.output


# ===========================================================================
# TestCliHelp
# ===========================================================================


class TestCliHelp:
    """Tests for the ``--help`` flags."""

    def test_help_flag_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0

    def test_help_output_is_non_empty(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert len(result.output.strip()) > 0

    def test_validate_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", "--help"])
        assert result.exit_code == 0

    def test_validate_help_shows_format_option(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", "--help"])
        assert "--format" in result.output

    def test_validate_help_shows_file_argument(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", "--help"])
        assert "FILE" in result.output


# ===========================================================================
# TestCliValidatePassTextOutput
# ===========================================================================


class TestCliValidatePassTextOutput:
    """Tests for text output when a valid SBOM file is supplied."""

    def test_valid_spdx_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json")])
        assert result.exit_code == 0

    def test_valid_spdx_output_contains_pass(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json")])
        assert "PASS" in result.output

    def test_valid_spdx_output_mentions_spdx_format(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json")])
        # The human-readable output should identify the detected format.
        assert "spdx" in result.output.lower()

    def test_valid_cyclonedx_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "valid-minimal.cdx.json")])
        assert result.exit_code == 0

    def test_valid_cyclonedx_output_contains_pass(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "valid-minimal.cdx.json")])
        assert "PASS" in result.output

    def test_valid_cyclonedx_output_mentions_cyclonedx_format(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "valid-minimal.cdx.json")])
        assert "cyclonedx" in result.output.lower()

    def test_valid_spdx_full_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "valid-full.spdx.json")])
        assert result.exit_code == 0

    def test_valid_cyclonedx_full_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "valid-full.cdx.json")])
        assert result.exit_code == 0


# ===========================================================================
# TestCliValidateFailTextOutput
# ===========================================================================


class TestCliValidateFailTextOutput:
    """Tests for text output when validation issues are found."""

    # --- missing-supplier ---------------------------------------------------

    def test_missing_supplier_exits_one(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["validate", str(SPDX_FIXTURES / "missing-supplier.spdx.json")]
        )
        assert result.exit_code == 1

    def test_missing_supplier_output_contains_fail(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["validate", str(SPDX_FIXTURES / "missing-supplier.spdx.json")]
        )
        assert "FAIL" in result.output

    def test_missing_supplier_output_contains_issue_message(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["validate", str(SPDX_FIXTURES / "missing-supplier.spdx.json")]
        )
        # There must be at least some non-trivial issue text beyond just "FAIL".
        # Strip the status line and confirm remaining content is non-empty.
        lines = [ln for ln in result.output.splitlines() if ln.strip()]
        assert len(lines) > 1, "Expected issue details beyond the status line"

    def test_missing_supplier_output_contains_supplier_reference(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["validate", str(SPDX_FIXTURES / "missing-supplier.spdx.json")]
        )
        # The output should contain a hint about the supplier field.
        assert "supplier" in result.output.lower()

    # --- missing-timestamp --------------------------------------------------

    def test_missing_timestamp_exits_one(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["validate", str(SPDX_FIXTURES / "missing-timestamp.spdx.json")]
        )
        assert result.exit_code == 1

    def test_missing_timestamp_output_contains_fail(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["validate", str(SPDX_FIXTURES / "missing-timestamp.spdx.json")]
        )
        assert "FAIL" in result.output

    # --- missing-relationships ----------------------------------------------

    def test_missing_relationships_exits_one(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "missing-relationships.spdx.json")],
        )
        assert result.exit_code == 1

    def test_missing_relationships_output_contains_fail(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "missing-relationships.spdx.json")],
        )
        assert "FAIL" in result.output

    # --- missing-identifiers ------------------------------------------------

    def test_missing_identifiers_exits_one(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "missing-identifiers.spdx.json")],
        )
        assert result.exit_code == 1

    def test_missing_identifiers_output_contains_fail(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "missing-identifiers.spdx.json")],
        )
        assert "FAIL" in result.output

    # --- invalid schema (FAIL at stage 1) -----------------------------------

    def test_invalid_schema_spdx_exits_one(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "invalid-schema.spdx.json")])
        assert result.exit_code == 1

    def test_invalid_schema_spdx_output_contains_fail(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "invalid-schema.spdx.json")])
        assert "FAIL" in result.output


# ===========================================================================
# TestCliValidateErrorCases
# ===========================================================================


class TestCliValidateErrorCases:
    """Tests for exit code 2 (tool/input errors)."""

    def test_nonexistent_file_exits_two(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(main, ["validate", str(tmp_path / "no-such-file.json")])
        assert result.exit_code == 2

    def test_nonexistent_file_output_contains_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        result = runner.invoke(main, ["validate", str(tmp_path / "no-such-file.json")])
        assert "error" in result.output.lower() or "Error" in result.output

    def test_unknown_format_exits_two(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f)])
        assert result.exit_code == 2

    def test_unknown_format_output_contains_error(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f)])
        assert "error" in result.output.lower() or "ERROR" in result.output

    def test_invalid_json_exits_two(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "broken.json"
        f.write_text("this is { not valid json >>>")
        result = runner.invoke(main, ["validate", str(f)])
        assert result.exit_code == 2

    def test_invalid_json_output_contains_error(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "broken.json"
        f.write_text("this is { not valid json >>>")
        result = runner.invoke(main, ["validate", str(f)])
        assert "error" in result.output.lower() or "ERROR" in result.output

    def test_empty_json_object_exits_two(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "empty.json"
        f.write_text("{}")
        result = runner.invoke(main, ["validate", str(f)])
        assert result.exit_code == 2


# ===========================================================================
# TestCliJsonOutputPass
# ===========================================================================


class TestCliJsonOutputPass:
    """Tests for ``--format json`` output when validation passes."""

    def _invoke_valid_spdx(self, runner: CliRunner) -> dict:
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--format",
                "json",
            ],
        )
        return result

    def test_valid_spdx_json_format_exits_zero(self, runner: CliRunner) -> None:
        result = self._invoke_valid_spdx(runner)
        assert result.exit_code == 0

    def test_valid_spdx_json_output_is_valid_json(self, runner: CliRunner) -> None:
        result = self._invoke_valid_spdx(runner)
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_valid_spdx_json_status_is_pass(self, runner: CliRunner) -> None:
        result = self._invoke_valid_spdx(runner)
        data = json.loads(result.output)
        assert data["status"] == "PASS"

    def test_valid_spdx_json_has_file_key(self, runner: CliRunner) -> None:
        result = self._invoke_valid_spdx(runner)
        data = json.loads(result.output)
        assert "file" in data

    def test_valid_spdx_json_file_value_is_string(self, runner: CliRunner) -> None:
        result = self._invoke_valid_spdx(runner)
        data = json.loads(result.output)
        assert isinstance(data["file"], str)
        assert len(data["file"]) > 0

    def test_valid_spdx_json_has_issues_key(self, runner: CliRunner) -> None:
        result = self._invoke_valid_spdx(runner)
        data = json.loads(result.output)
        assert "issues" in data

    def test_valid_spdx_json_issues_is_empty_list(self, runner: CliRunner) -> None:
        result = self._invoke_valid_spdx(runner)
        data = json.loads(result.output)
        assert data["issues"] == []

    def test_valid_spdx_json_has_format_detected(self, runner: CliRunner) -> None:
        result = self._invoke_valid_spdx(runner)
        data = json.loads(result.output)
        assert "format_detected" in data

    def test_valid_spdx_json_format_detected_is_spdx(self, runner: CliRunner) -> None:
        result = self._invoke_valid_spdx(runner)
        data = json.loads(result.output)
        assert data["format_detected"] == "spdx"

    def test_valid_cyclonedx_json_format_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(CDX_FIXTURES / "valid-minimal.cdx.json"),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_valid_cyclonedx_json_status_is_pass(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(CDX_FIXTURES / "valid-minimal.cdx.json"),
                "--format",
                "json",
            ],
        )
        data = json.loads(result.output)
        assert data["status"] == "PASS"

    def test_valid_cyclonedx_json_format_detected_is_cyclonedx(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(CDX_FIXTURES / "valid-minimal.cdx.json"),
                "--format",
                "json",
            ],
        )
        data = json.loads(result.output)
        assert data["format_detected"] == "cyclonedx"

    def test_valid_cyclonedx_json_issues_is_empty_list(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(CDX_FIXTURES / "valid-minimal.cdx.json"),
                "--format",
                "json",
            ],
        )
        data = json.loads(result.output)
        assert data["issues"] == []


# ===========================================================================
# TestCliJsonOutputFail
# ===========================================================================


class TestCliJsonOutputFail:
    """Tests for ``--format json`` output when validation fails."""

    def _invoke_missing_supplier(self, runner: CliRunner):
        return runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "missing-supplier.spdx.json"),
                "--format",
                "json",
            ],
        )

    def test_failing_spdx_json_exits_one(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        assert result.exit_code == 1

    def test_failing_spdx_json_output_is_valid_json(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_failing_spdx_json_status_is_fail(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        assert data["status"] == "FAIL"

    def test_failing_spdx_json_has_file_key(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        assert "file" in data

    def test_failing_spdx_json_format_detected_is_spdx(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        assert data["format_detected"] == "spdx"

    def test_failing_spdx_json_issues_non_empty(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        assert len(data["issues"]) > 0

    def test_failing_spdx_json_issue_has_severity_key(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        issue = data["issues"][0]
        assert "severity" in issue

    def test_failing_spdx_json_issue_has_field_path_key(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        issue = data["issues"][0]
        assert "field_path" in issue

    def test_failing_spdx_json_issue_has_message_key(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        issue = data["issues"][0]
        assert "message" in issue

    def test_failing_spdx_json_issue_has_rule_key(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        issue = data["issues"][0]
        assert "rule" in issue

    def test_failing_spdx_json_issue_required_keys_all_present(self, runner: CliRunner) -> None:
        """Single assertion verifying all four required keys exist on every issue."""
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        for issue in data["issues"]:
            for key in ("severity", "field_path", "message", "rule"):
                assert key in issue, f"Issue is missing key '{key}': {issue}"

    def test_failing_spdx_json_issue_severity_is_valid_value(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        valid_severities = {"ERROR", "WARNING", "INFO"}
        for issue in data["issues"]:
            assert issue["severity"] in valid_severities

    def test_failing_spdx_json_issue_message_is_non_empty_string(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        for issue in data["issues"]:
            assert isinstance(issue["message"], str)
            assert len(issue["message"]) > 0

    def test_failing_spdx_json_issue_field_path_is_string(self, runner: CliRunner) -> None:
        result = self._invoke_missing_supplier(runner)
        data = json.loads(result.output)
        for issue in data["issues"]:
            assert isinstance(issue["field_path"], str)

    def test_missing_timestamp_json_exits_one(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "missing-timestamp.spdx.json"),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 1

    def test_missing_timestamp_json_status_is_fail(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "missing-timestamp.spdx.json"),
                "--format",
                "json",
            ],
        )
        data = json.loads(result.output)
        assert data["status"] == "FAIL"

    def test_missing_relationships_json_exits_one(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "missing-relationships.spdx.json"),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 1

    def test_missing_identifiers_json_exits_one(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "missing-identifiers.spdx.json"),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 1


# ===========================================================================
# TestCliJsonOutputError
# ===========================================================================


class TestCliJsonOutputError:
    """Tests for ``--format json`` output on tool/input error conditions.

    Even when the tool exits with code 2, the JSON output contract must be
    upheld: the output must be valid JSON with a ``status`` of ``"ERROR"``.
    """

    def test_unknown_format_json_exits_two(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        assert result.exit_code == 2

    def test_unknown_format_json_output_is_valid_json(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        # Must not raise even on error
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_unknown_format_json_status_is_error(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        data = json.loads(result.output)
        assert data["status"] == "ERROR"

    def test_unknown_format_json_has_file_key(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        data = json.loads(result.output)
        assert "file" in data

    def test_unknown_format_json_has_issues_key(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        data = json.loads(result.output)
        assert "issues" in data

    def test_unknown_format_json_format_detected_is_null(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        data = json.loads(result.output)
        # format_detected must be null/None when format is unrecognised
        assert data["format_detected"] is None

    def test_invalid_json_format_exits_two(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "broken.json"
        f.write_text("this is { not valid json >>>")
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        assert result.exit_code == 2

    def test_invalid_json_format_output_is_valid_json(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        f = tmp_path / "broken.json"
        f.write_text("this is { not valid json >>>")
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_invalid_json_format_status_is_error(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "broken.json"
        f.write_text("this is { not valid json >>>")
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        data = json.loads(result.output)
        assert data["status"] == "ERROR"

    def test_nonexistent_file_json_exits_two(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(tmp_path / "no-such-file.json"),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 2

    def test_nonexistent_file_json_output_is_valid_json(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(tmp_path / "no-such-file.json"),
                "--format",
                "json",
            ],
        )
        # Click's Path(exists=True) fires before our code; we still need valid JSON
        # output. If Click has not yet been wired to produce JSON on path errors,
        # this test will fail until the developer handles the case.
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_nonexistent_file_json_status_is_error(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(tmp_path / "no-such-file.json"),
                "--format",
                "json",
            ],
        )
        data = json.loads(result.output)
        assert data["status"] == "ERROR"


# ===========================================================================
# TestCliLogLevelOption
# ===========================================================================


class TestCliLogLevelOption:
    """Tests for the ``--log-level`` option on the ``validate`` subcommand.

    Per ADR-006, ``--log-level`` is a Choice of DEBUG/INFO/WARNING/ERROR,
    case-insensitive, defaulting to WARNING.  These tests are TDD red-phase:
    they WILL fail until the Developer adds the option to cli.py.
    """

    # -----------------------------------------------------------------------
    # Accepted values
    # -----------------------------------------------------------------------

    def test_log_level_debug_is_accepted(self, runner: CliRunner) -> None:
        """--log-level DEBUG must not cause a Click usage error (exit 2)."""
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json"), "--log-level", "DEBUG"],
        )
        # Should exit with 0 (PASS), not 2 (bad parameter)
        assert result.exit_code == 0

    def test_log_level_info_is_accepted(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json"), "--log-level", "INFO"],
        )
        assert result.exit_code == 0

    def test_log_level_warning_is_accepted(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json"), "--log-level", "WARNING"],
        )
        assert result.exit_code == 0

    def test_log_level_error_is_accepted(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json"), "--log-level", "ERROR"],
        )
        assert result.exit_code == 0

    def test_log_level_lowercase_is_accepted(self, runner: CliRunner) -> None:
        """ADR-006: case_sensitive=False — lowercase values must be accepted."""
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json"), "--log-level", "debug"],
        )
        assert result.exit_code == 0

    # -----------------------------------------------------------------------
    # Invalid value
    # -----------------------------------------------------------------------

    def test_log_level_invalid_exits_two(self, runner: CliRunner) -> None:
        """An unrecognised log level value must cause Click to exit with code 2."""
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json"), "--log-level", "INVALID"],
        )
        assert result.exit_code == 2

    # -----------------------------------------------------------------------
    # Default behaviour (option omitted)
    # -----------------------------------------------------------------------

    def test_log_level_omitted_still_passes(self, runner: CliRunner) -> None:
        """Backward compatibility: omitting --log-level must not break the command."""
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json")],
        )
        assert result.exit_code == 0

    # -----------------------------------------------------------------------
    # stdout purity: log output must NOT appear on stdout
    # -----------------------------------------------------------------------

    def test_log_level_debug_json_output_is_valid_json(self, runner: CliRunner) -> None:
        """When --log-level DEBUG and --format json, the output must be parseable JSON.

        ADR-006 stdout-purity guarantee: log output goes to stderr only.
        CliRunner in Click 8 combines stdout+stderr in result.output; the
        real guarantee is verified by asserting the output parses as JSON.
        If log text leaked onto stdout it would appear before the opening
        brace and json.loads would raise.
        """
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--format",
                "json",
                "--log-level",
                "DEBUG",
            ],
        )
        # Should still exit 0 for a valid file
        assert result.exit_code == 0
        # output must be parseable JSON — stdout contamination would break this
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_log_level_debug_json_status_is_pass(self, runner: CliRunner) -> None:
        """JSON output integrity: status field must be PASS even with DEBUG logging."""
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--format",
                "json",
                "--log-level",
                "DEBUG",
            ],
        )
        data = json.loads(result.output)
        assert data["status"] == "PASS"

    def test_log_level_debug_text_format_exit_code_unchanged(self, runner: CliRunner) -> None:
        """--log-level DEBUG with text output must not affect the exit code."""
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--log-level",
                "DEBUG",
            ],
        )
        assert result.exit_code == 0

    # -----------------------------------------------------------------------
    # Help text
    # -----------------------------------------------------------------------

    def test_validate_help_shows_log_level_option(self, runner: CliRunner) -> None:
        """--help output must document the --log-level option."""
        result = runner.invoke(main, ["validate", "--help"])
        assert "--log-level" in result.output

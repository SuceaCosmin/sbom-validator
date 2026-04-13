"""Unit tests for CLI JSON-format output: passing files, failing files, and error conditions."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from sbom_validator.cli import main

SPDX_FIXTURES = Path("tests/fixtures/spdx")
CDX_FIXTURES = Path("tests/fixtures/cyclonedx")


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

    def test_valid_cyclonedx_xml_json_format_detected_is_cyclonedx(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "validate",
                str(CDX_FIXTURES / "valid-minimal.cdx.xml"),
                "--format",
                "json",
            ],
        )
        data = json.loads(result.output)
        assert data["status"] == "PASS"
        assert data["format_detected"] == "cyclonedx"


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

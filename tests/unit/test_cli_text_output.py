"""Unit tests for CLI text-format output: passing files, failing files, and error cases."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sbom_validator.cli import main

SPDX_FIXTURES = Path("tests/fixtures/spdx")
CDX_FIXTURES = Path("tests/fixtures/cyclonedx")


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

    def test_valid_cyclonedx_xml_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "valid-minimal.cdx.xml")])
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

    def test_invalid_cyclonedx_xml_output_uses_human_friendly_field_path(
        self, runner: CliRunner
    ) -> None:
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "invalid-schema.cdx.xml")])
        assert result.exit_code == 1
        assert "/bom/components/component" in result.output
        assert "{http://cyclonedx.org/schema/bom/1.6}" not in result.output

    def test_conformance_failure_hides_ntia_rule_and_shows_hint(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "missing-supplier.cdx.json")])
        assert result.exit_code == 1
        assert "NTIA FR-" not in result.output
        assert "Hint: provide a supplier/organization name" in result.output


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

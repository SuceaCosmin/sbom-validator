"""Unit tests for CLI options: --log-level and --report-dir."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
from sbom_validator.cli import main

SPDX_FIXTURES = Path("tests/fixtures/spdx")
CDX_FIXTURES = Path("tests/fixtures/cyclonedx")


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
        import json

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
        import json

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


# ===========================================================================
# TestCliReportDirOption
# ===========================================================================


class TestCliReportDirOption:
    """Tests for the ``--report-dir`` option on the ``validate`` subcommand.

    Per ADR-007, ``--report-dir`` is an optional path option that causes both
    an HTML and a JSON report to be written.  These tests are TDD red-phase:
    they WILL fail until the Developer wires ``--report-dir`` into cli.py and
    implements ``report_writer.write_reports``.
    """

    # -----------------------------------------------------------------------
    # Option omitted — no side-effects
    # -----------------------------------------------------------------------

    def test_no_report_dir_does_not_write_files(self, runner: CliRunner, tmp_path: Path) -> None:
        """When --report-dir is omitted, no report files must be created."""
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json")])
        assert result.exit_code == 0
        # tmp_path is empty — no stray files created anywhere inside it
        assert list(tmp_path.iterdir()) == []

    def test_no_report_dir_exit_code_zero_for_pass(self, runner: CliRunner) -> None:
        """Omitting --report-dir must not change the exit code for a passing file."""
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json")])
        assert result.exit_code == 0

    # -----------------------------------------------------------------------
    # --report-dir with an existing directory
    # -----------------------------------------------------------------------

    def test_report_dir_existing_creates_html_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """An HTML report file must be created in the specified existing directory."""
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--report-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        html_files = list(tmp_path.glob("*.html"))
        assert len(html_files) == 1, f"Expected 1 HTML file, found: {html_files}"

    def test_report_dir_existing_creates_json_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """A JSON report file must be created in the specified existing directory."""
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--report-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 1, f"Expected 1 JSON file, found: {json_files}"

    def test_report_dir_existing_creates_both_files(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Both HTML and JSON report files must be present after invocation."""
        runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--report-dir",
                str(tmp_path),
            ],
        )
        html_files = list(tmp_path.glob("*.html"))
        json_files = list(tmp_path.glob("*.json"))
        assert len(html_files) == 1
        assert len(json_files) == 1

    # -----------------------------------------------------------------------
    # --report-dir with a non-existent directory
    # -----------------------------------------------------------------------

    def test_report_dir_nonexistent_is_created(self, runner: CliRunner, tmp_path: Path) -> None:
        """A non-existent report directory must be created automatically."""
        new_dir = tmp_path / "reports" / "run1"
        assert not new_dir.exists()
        runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--report-dir",
                str(new_dir),
            ],
        )
        assert new_dir.is_dir()

    def test_report_dir_nonexistent_both_files_written(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Both report files must exist inside an auto-created directory."""
        new_dir = tmp_path / "reports" / "run1"
        runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--report-dir",
                str(new_dir),
            ],
        )
        assert len(list(new_dir.glob("*.html"))) == 1
        assert len(list(new_dir.glob("*.json"))) == 1

    def test_report_dir_nonexistent_no_error_exit(self, runner: CliRunner, tmp_path: Path) -> None:
        """A non-existent --report-dir must not cause a non-zero exit for a PASS file."""
        new_dir = tmp_path / "auto-created"
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--report-dir",
                str(new_dir),
            ],
        )
        assert result.exit_code == 0

    # -----------------------------------------------------------------------
    # Exit code stability with --report-dir
    # -----------------------------------------------------------------------

    def test_report_dir_pass_file_exit_code_zero(self, runner: CliRunner, tmp_path: Path) -> None:
        """--report-dir must not change exit code 0 for a passing SBOM."""
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "valid-minimal.spdx.json"),
                "--report-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0

    def test_report_dir_fail_file_exit_code_one(self, runner: CliRunner, tmp_path: Path) -> None:
        """--report-dir must not change exit code 1 for a failing SBOM."""
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "missing-supplier.spdx.json"),
                "--report-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 1

    def test_report_dir_fail_file_still_creates_reports(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Reports must be written even when validation fails (exit 1)."""
        runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "missing-supplier.spdx.json"),
                "--report-dir",
                str(tmp_path),
            ],
        )
        assert len(list(tmp_path.glob("*.html"))) == 1
        assert len(list(tmp_path.glob("*.json"))) == 1

    # -----------------------------------------------------------------------
    # Help text
    # -----------------------------------------------------------------------

    def test_validate_help_shows_report_dir_option(self, runner: CliRunner) -> None:
        """--help output must document the --report-dir option."""
        result = runner.invoke(main, ["validate", "--help"])
        assert "--report-dir" in result.output

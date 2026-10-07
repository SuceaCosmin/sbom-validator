"""Unit tests for CLI handling of missing/non-file FILE arguments (ADR-005 Amendment 1).

Requirement coverage: FR-01 (unreadable input is an ERROR), FR-11 (valid JSON on stdout even
on failure), FR-12 (text output), FR-13 (exit code 2). ``--report-dir`` has no dedicated FR ID
in docs/requirements.md; its tests are tagged FR-11/FR-13 (stable output contract).
"""

from __future__ import annotations

import json
from pathlib import Path

import click
from click.testing import CliRunner

from sbom_validator import cli
from sbom_validator.cli import main

SPDX_FIXTURES = Path("tests/fixtures/spdx")
JSON_KEYS = {"status", "file", "format_detected", "issues"}


def _missing(tmp_path: Path) -> str:
    return str(tmp_path / "no-such-file.spdx.json")


class TestCliMissingFileJson:
    """Missing FILE with ``--format json`` yields a structured ERROR on stdout."""

    def test_missing_file_json_is_valid_json_with_error_status(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """FR-11: output is valid JSON with status ERROR."""
        result = runner.invoke(main, ["validate", _missing(tmp_path), "--format", "json"])
        data = json.loads(result.stdout)
        assert data["status"] == "ERROR"

    def test_missing_file_json_has_contract_keys(self, runner: CliRunner, tmp_path: Path) -> None:
        """FR-11: stable JSON keys are present."""
        result = runner.invoke(main, ["validate", _missing(tmp_path), "--format", "json"])
        assert JSON_KEYS <= set(json.loads(result.stdout))

    def test_missing_file_json_file_field_equals_raw_argument(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """FR-11: ``file`` is the raw argument, unaltered."""
        arg = _missing(tmp_path)
        result = runner.invoke(main, ["validate", arg, "--format", "json"])
        assert json.loads(result.stdout)["file"] == arg

    def test_missing_file_json_has_at_least_one_issue(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """FR-01: the failure is reported as an issue."""
        result = runner.invoke(main, ["validate", _missing(tmp_path), "--format", "json"])
        assert len(json.loads(result.stdout)["issues"]) >= 1

    def test_missing_file_json_stdout_contains_only_json(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """FR-11: no usage text or other noise on stdout."""
        result = runner.invoke(main, ["validate", _missing(tmp_path), "--format", "json"])
        assert result.stdout.strip().startswith("{")
        assert result.stdout.strip().endswith("}")
        assert "Usage" not in result.stdout
        assert "Error: Invalid value" not in result.stdout

    def test_missing_file_json_exits_two(self, runner: CliRunner, tmp_path: Path) -> None:
        """FR-13: exit code 2."""
        result = runner.invoke(main, ["validate", _missing(tmp_path), "--format", "json"])
        assert result.exit_code == 2


class TestCliMissingFileText:
    """Missing FILE with the default text format yields a structured ERROR block."""

    def test_missing_file_text_shows_error_status_and_raw_path(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """FR-12: text output includes ``ERROR`` status and the raw file argument."""
        arg = _missing(tmp_path)
        result = runner.invoke(main, ["validate", arg])
        assert "Status:  ERROR" in result.stdout
        assert arg in result.stdout

    def test_missing_file_text_has_no_click_usage_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """FR-12: the Click usage error is not emitted."""
        result = runner.invoke(main, ["validate", _missing(tmp_path)])
        assert "Usage:" not in result.output
        assert "Invalid value" not in result.output

    def test_missing_file_text_exits_two(self, runner: CliRunner, tmp_path: Path) -> None:
        """FR-13: exit code 2."""
        result = runner.invoke(main, ["validate", _missing(tmp_path)])
        assert result.exit_code == 2


class TestCliMissingFileReportDir:
    """``--report-dir`` still writes fixed-name reports for a missing FILE."""

    def test_missing_file_with_report_dir_writes_html_and_json(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """FR-11/FR-13: reports named ``sbom-report-<stem>.html/.json`` are written."""
        report_dir = tmp_path / "reports"
        result = runner.invoke(
            main,
            ["validate", _missing(tmp_path), "--format", "json", "--report-dir", str(report_dir)],
        )
        stem = Path(_missing(tmp_path)).stem
        assert result.exit_code == 2
        assert (report_dir / f"sbom-report-{stem}.html").is_file()
        assert (report_dir / f"sbom-report-{stem}.json").is_file()

    def test_missing_file_report_json_records_error_status(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """FR-11: the written JSON report records ERROR."""
        report_dir = tmp_path / "reports"
        runner.invoke(main, ["validate", _missing(tmp_path), "--report-dir", str(report_dir)])
        stem = Path(_missing(tmp_path)).stem
        data = json.loads((report_dir / f"sbom-report-{stem}.json").read_text(encoding="utf-8"))
        assert "ERROR" in json.dumps(data)


class TestCliDirectoryAsFile:
    """A directory passed as FILE is a structured ERROR, exit 2."""

    def test_directory_json_is_error_exit_two(self, runner: CliRunner, tmp_path: Path) -> None:
        """FR-01/FR-11/FR-13: structured ERROR, raw path echoed, exit 2."""
        result = runner.invoke(main, ["validate", str(tmp_path), "--format", "json"])
        data = json.loads(result.stdout)
        assert result.exit_code == 2
        assert data["status"] == "ERROR"
        assert data["file"] == str(tmp_path)

    def test_directory_text_is_error_exit_two(self, runner: CliRunner, tmp_path: Path) -> None:
        """FR-12/FR-13: text ERROR block, exit 2."""
        result = runner.invoke(main, ["validate", str(tmp_path)])
        assert result.exit_code == 2
        assert "Status:  ERROR" in result.stdout


class TestCliExistingFileRegression:
    """Existing files are unaffected by the lenient path type."""

    def test_valid_file_still_passes(self, runner: CliRunner) -> None:
        """FR-13: valid SBOM exits 0 with status PASS."""
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json"), "--format", "json"],
        )
        assert result.exit_code == 0
        assert json.loads(result.stdout)["status"] == "PASS"

    def test_invalid_file_still_fails(self, runner: CliRunner) -> None:
        """FR-13: invalid SBOM exits 1 with status FAIL."""
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "missing-supplier.spdx.json"), "--format", "json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.stdout)["status"] == "FAIL"


class TestLenientExistingPath:
    """Unit tests of the private ``_LenientExistingPath`` parameter type."""

    def test_is_click_path_subclass(self) -> None:
        """FR-13: type is a click.Path subclass."""
        assert issubclass(cli._LenientExistingPath, click.Path)

    def test_declares_exists_true(self) -> None:
        """FR-13: declared semantics are exists=True, dir_okay=True."""
        param_type = cli._LenientExistingPath()
        assert param_type.exists is True
        assert param_type.dir_okay is True
        assert param_type.file_okay is True

    def test_convert_existing_file_returns_raw_str(self, tmp_path: Path) -> None:
        """FR-13: an existing file is returned unchanged as str."""
        target = tmp_path / "bom.json"
        target.write_text("{}", encoding="utf-8")
        converted = cli._LenientExistingPath().convert(str(target), None, None)
        assert converted == str(target)
        assert isinstance(converted, str)

    def test_convert_missing_path_returns_raw_str_without_raising(self, tmp_path: Path) -> None:
        """FR-13: a missing path does not raise click.BadParameter."""
        missing = _missing(tmp_path)
        converted = cli._LenientExistingPath().convert(missing, None, None)
        assert converted == missing
        assert isinstance(converted, str)

    def test_convert_directory_returns_raw_str(self, tmp_path: Path) -> None:
        """FR-13: a directory is accepted and returned unchanged."""
        converted = cli._LenientExistingPath().convert(str(tmp_path), None, None)
        assert converted == str(tmp_path)
        assert isinstance(converted, str)

    def test_convert_relative_missing_path_is_not_resolved(self) -> None:
        """FR-11: raw argument is preserved (no resolution) for ``file`` echo."""
        converted = cli._LenientExistingPath().convert("rel/none.json", None, None)
        assert converted == "rel/none.json"

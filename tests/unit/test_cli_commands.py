"""Unit tests for CLI meta-commands: --version and --help flags."""

from __future__ import annotations

from click.testing import CliRunner
from sbom_validator import __version__
from sbom_validator.cli import main

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
        assert __version__ in result.output


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

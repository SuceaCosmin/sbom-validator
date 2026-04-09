"""Integration tests for sbom-validator CLI end-to-end pipeline.

These tests exercise the full pipeline from CLI invocation through
format detection, schema validation, parsing, and NTIA checking.
They are distinct from unit tests in that they test real fixture files
and cross-module interactions.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from click.testing import CliRunner
from sbom_validator.cli import main

SPDX_FIXTURES = Path("tests/fixtures/spdx")
CDX_FIXTURES = Path("tests/fixtures/cyclonedx")
INTEGRATION_FIXTURES = Path("tests/fixtures/integration")


@pytest.fixture
def runner():
    return CliRunner()


class TestFullPassPipeline:
    """End-to-end PASS scenarios: valid SBOM → exit 0, correct output."""

    def test_valid_spdx_minimal_full_pipeline(self, runner):
        """Full pipeline for a minimal valid SPDX 2.3 SBOM."""
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json")])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_valid_spdx_full_pipeline(self, runner):
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "valid-full.spdx.json")])
        assert result.exit_code == 0

    def test_valid_cyclonedx_minimal_full_pipeline(self, runner):
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "valid-minimal.cdx.json")])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_valid_cyclonedx_full_pipeline(self, runner):
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "valid-full.cdx.json")])
        assert result.exit_code == 0

    def test_valid_cyclonedx_xml_minimal_full_pipeline(self, runner):
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "valid-minimal.cdx.xml")])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_pass_json_output_structure(self, runner):
        """JSON output for a passing SBOM has all required keys."""
        result = runner.invoke(
            main, ["validate", str(SPDX_FIXTURES / "valid-minimal.spdx.json"), "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "PASS"
        assert data["issues"] == []
        assert data["format_detected"] == "spdx"
        assert "file" in data

    def test_pass_cdx_json_output_structure(self, runner):
        result = runner.invoke(
            main, ["validate", str(CDX_FIXTURES / "valid-minimal.cdx.json"), "--format", "json"]
        )
        data = json.loads(result.output)
        assert data["status"] == "PASS"
        assert data["format_detected"] == "cyclonedx"


class TestSchemaFailurePipeline:
    """Schema validation failure stops the pipeline — no NTIA issues reported."""

    def test_invalid_spdx_schema_exits_one(self, runner):
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "invalid-schema.spdx.json")])
        assert result.exit_code == 1

    def test_invalid_spdx_schema_reports_fail(self, runner):
        result = runner.invoke(main, ["validate", str(SPDX_FIXTURES / "invalid-schema.spdx.json")])
        assert "FAIL" in result.output

    def test_invalid_spdx_schema_json_has_fr02_issues(self, runner):
        result = runner.invoke(
            main, ["validate", str(SPDX_FIXTURES / "invalid-schema.spdx.json"), "--format", "json"]
        )
        data = json.loads(result.output)
        assert data["status"] == "FAIL"
        assert all(i["rule"] == "FR-02" for i in data["issues"])

    def test_schema_failure_no_ntia_rules_in_output(self, runner):
        """When schema fails, no NTIA rules (FR-04 through FR-10) should appear."""
        result = runner.invoke(
            main, ["validate", str(SPDX_FIXTURES / "invalid-schema.spdx.json"), "--format", "json"]
        )
        data = json.loads(result.output)
        ntia_rules = {"FR-04", "FR-05", "FR-06", "FR-07", "FR-08", "FR-09", "FR-10"}
        issue_rules = {i["rule"] for i in data["issues"]}
        assert issue_rules.isdisjoint(ntia_rules)

    def test_invalid_cdx_schema_exits_one(self, runner):
        result = runner.invoke(main, ["validate", str(CDX_FIXTURES / "invalid-schema.cdx.json")])
        assert result.exit_code == 1

    def test_invalid_cdx_schema_json_has_fr03_issues(self, runner):
        result = runner.invoke(
            main, ["validate", str(CDX_FIXTURES / "invalid-schema.cdx.json"), "--format", "json"]
        )
        data = json.loads(result.output)
        assert data["status"] == "FAIL"
        assert all(i["rule"] == "FR-03" for i in data["issues"])

    def test_invalid_cdx_xml_schema_json_has_fr03_issues(self, runner):
        result = runner.invoke(
            main, ["validate", str(CDX_FIXTURES / "invalid-schema.cdx.xml"), "--format", "json"]
        )
        data = json.loads(result.output)
        assert data["status"] == "FAIL"
        assert all(i["rule"] == "FR-03" for i in data["issues"])


class TestNtiaFailurePipeline:
    """NTIA failures: schema passes, NTIA issues are all reported."""

    def test_all_ntia_failures_reported_spdx_missing_supplier(self, runner):
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "missing-supplier.spdx.json"), "--format", "json"],
        )
        data = json.loads(result.output)
        assert data["status"] == "FAIL"
        rules = {i["rule"] for i in data["issues"]}
        assert "FR-04" in rules

    def test_ntia_fail_no_schema_rules(self, runner):
        """When schema passes but NTIA fails, no schema rules in output."""
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "missing-supplier.spdx.json"), "--format", "json"],
        )
        data = json.loads(result.output)
        assert not any(i["rule"] in ("FR-02", "FR-03") for i in data["issues"])

    def test_missing_timestamp_spdx_reported(self, runner):
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "missing-timestamp.spdx.json"), "--format", "json"],
        )
        data = json.loads(result.output)
        rules = {i["rule"] for i in data["issues"]}
        assert "FR-10" in rules

    def test_missing_relationships_spdx_reported(self, runner):
        result = runner.invoke(
            main,
            [
                "validate",
                str(SPDX_FIXTURES / "missing-relationships.spdx.json"),
                "--format",
                "json",
            ],
        )
        data = json.loads(result.output)
        rules = {i["rule"] for i in data["issues"]}
        assert "FR-08" in rules

    def test_missing_identifiers_spdx_reported(self, runner):
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "missing-identifiers.spdx.json"), "--format", "json"],
        )
        data = json.loads(result.output)
        rules = {i["rule"] for i in data["issues"]}
        assert "FR-07" in rules

    def test_missing_supplier_cdx_reported(self, runner):
        result = runner.invoke(
            main, ["validate", str(CDX_FIXTURES / "missing-supplier.cdx.json"), "--format", "json"]
        )
        data = json.loads(result.output)
        rules = {i["rule"] for i in data["issues"]}
        assert "FR-04" in rules

    def test_missing_timestamp_cdx_reported(self, runner):
        result = runner.invoke(
            main, ["validate", str(CDX_FIXTURES / "missing-timestamp.cdx.json"), "--format", "json"]
        )
        data = json.loads(result.output)
        rules = {i["rule"] for i in data["issues"]}
        assert "FR-10" in rules

    def test_each_issue_has_required_json_keys(self, runner):
        result = runner.invoke(
            main,
            ["validate", str(SPDX_FIXTURES / "missing-supplier.spdx.json"), "--format", "json"],
        )
        data = json.loads(result.output)
        for issue in data["issues"]:
            assert "severity" in issue
            assert "field_path" in issue
            assert "message" in issue
            assert "rule" in issue


class TestErrorPipeline:
    """Error scenarios: tool errors return exit 2, valid JSON even on error."""

    def test_nonexistent_file_exits_two(self, runner, tmp_path):
        result = runner.invoke(main, ["validate", str(tmp_path / "no-such-file.json")])
        assert result.exit_code == 2

    def test_unknown_format_exits_two(self, runner, tmp_path):
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f)])
        assert result.exit_code == 2

    def test_error_json_output_is_valid_json(self, runner, tmp_path):
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        data = json.loads(result.output)  # must not raise
        assert data["status"] == "ERROR"

    def test_error_json_format_detected_is_null(self, runner, tmp_path):
        f = tmp_path / "unknown.json"
        f.write_text('{"neither": "spdx nor cyclonedx"}')
        result = runner.invoke(main, ["validate", str(f), "--format", "json"])
        data = json.loads(result.output)
        assert data["format_detected"] is None


class TestLargeFixturePipeline:
    """Performance and correctness tests using realistic large fixtures (20+ components).

    These fixtures are created by Task 4.2. Tests are skipped if fixtures don't exist yet.
    """

    @pytest.mark.skipif(
        not (Path("tests/fixtures/integration/real-world-spdx.spdx.json")).exists(),
        reason="Integration fixtures not yet created (Task 4.2 pending)",
    )
    def test_large_spdx_validates_within_five_seconds(self, runner):
        """NFR-03: 100-component SBOM must validate in < 5 seconds."""
        start = time.time()
        runner.invoke(main, ["validate", str(INTEGRATION_FIXTURES / "real-world-spdx.spdx.json")])
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Validation took {elapsed:.2f}s, expected < 5s"

    @pytest.mark.skipif(
        not (Path("tests/fixtures/integration/real-world-cdx.cdx.json")).exists(),
        reason="Integration fixtures not yet created (Task 4.2 pending)",
    )
    def test_large_cyclonedx_validates_within_five_seconds(self, runner):
        start = time.time()
        runner.invoke(main, ["validate", str(INTEGRATION_FIXTURES / "real-world-cdx.cdx.json")])
        elapsed = time.time() - start
        assert elapsed < 5.0

    @pytest.mark.skipif(
        not (Path("tests/fixtures/integration/real-world-spdx.spdx.json")).exists(),
        reason="Integration fixtures not yet created",
    )
    def test_large_spdx_returns_pass(self, runner):
        result = runner.invoke(
            main, ["validate", str(INTEGRATION_FIXTURES / "real-world-spdx.spdx.json")]
        )
        assert result.exit_code == 0

    @pytest.mark.skipif(
        not (Path("tests/fixtures/integration/real-world-cdx.cdx.json")).exists(),
        reason="Integration fixtures not yet created",
    )
    def test_large_cyclonedx_returns_pass(self, runner):
        result = runner.invoke(
            main, ["validate", str(INTEGRATION_FIXTURES / "real-world-cdx.cdx.json")]
        )
        assert result.exit_code == 0

    @pytest.mark.skipif(
        not (Path("tests/fixtures/integration/edge-case-empty-packages.spdx.json")).exists(),
        reason="Integration fixtures not yet created",
    )
    def test_edge_case_empty_packages_fails_ntia(self, runner):
        result = runner.invoke(
            main,
            [
                "validate",
                str(INTEGRATION_FIXTURES / "edge-case-empty-packages.spdx.json"),
                "--format",
                "json",
            ],
        )
        data = json.loads(result.output)
        assert data["status"] == "FAIL"

    @pytest.mark.skipif(
        not (Path("tests/fixtures/integration/edge-case-no-deps.cdx.json")).exists(),
        reason="Integration fixtures not yet created",
    )
    def test_edge_case_no_deps_cdx_fails_ntia(self, runner):
        result = runner.invoke(
            main,
            [
                "validate",
                str(INTEGRATION_FIXTURES / "edge-case-no-deps.cdx.json"),
                "--format",
                "json",
            ],
        )
        data = json.loads(result.output)
        assert data["status"] == "FAIL"
        rules = {i["rule"] for i in data["issues"]}
        assert "FR-08" in rules

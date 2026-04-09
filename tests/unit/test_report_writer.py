"""Unit tests for report_writer.write_reports (TDD red phase).

These tests describe the intended behaviour of the not-yet-implemented
``report_writer`` module (FR-15).  They WILL fail until the Developer
creates ``src/sbom_validator/report_writer.py``.

Test layout
-----------
TestFileCreation        -- files exist with correct names
TestJsonReportContent   -- JSON schema / field values
TestHtmlReportContent   -- HTML structure and content
TestReturnValue         -- (html_path, json_path) tuple semantics
"""

from __future__ import annotations

import importlib.metadata
import json
import re
from pathlib import Path
from unittest.mock import patch

from sbom_validator.models import IssueSeverity, ValidationIssue, ValidationResult, ValidationStatus
from sbom_validator.report_writer import write_reports  # will cause ImportError until implemented

# ---------------------------------------------------------------------------
# Helpers — build ValidationResult objects without touching the real pipeline
# ---------------------------------------------------------------------------

_ISSUE_ERROR = ValidationIssue(
    severity=IssueSeverity.ERROR,
    field_path="packages.0.name",
    message="Field 'name' is required",
    rule="FR-02",
)
_ISSUE_WARNING = ValidationIssue(
    severity=IssueSeverity.WARNING,
    field_path="packages.0.supplier",
    message="Supplier is missing",
    rule="FR-06",
)
_ISSUE_INFO = ValidationIssue(
    severity=IssueSeverity.INFO,
    field_path="creationInfo",
    message="Optional field absent",
    rule="FR-09",
)


def _pass_result(file_path: str = "/tmp/bom.json") -> ValidationResult:
    return ValidationResult(
        status=ValidationStatus.PASS,
        file_path=file_path,
        format_detected="spdx",
        issues=(),
    )


def _fail_result(file_path: str = "/tmp/bom.json") -> ValidationResult:
    return ValidationResult(
        status=ValidationStatus.FAIL,
        file_path=file_path,
        format_detected="spdx",
        issues=(_ISSUE_ERROR, _ISSUE_WARNING),
    )


def _error_result(file_path: str = "/tmp/bom.json") -> ValidationResult:
    return ValidationResult(
        status=ValidationStatus.ERROR,
        file_path=file_path,
        format_detected=None,
        issues=(),
    )


def _multi_issue_result(file_path: str = "/tmp/bom.json") -> ValidationResult:
    return ValidationResult(
        status=ValidationStatus.FAIL,
        file_path=file_path,
        format_detected="cyclonedx",
        issues=(_ISSUE_INFO, _ISSUE_WARNING, _ISSUE_ERROR),
    )


# ===========================================================================
# TestFileCreation
# ===========================================================================


class TestFileCreation:
    """Both HTML and JSON files are created with the expected naming convention."""

    def test_both_files_are_created(self, tmp_path: Path) -> None:
        """write_reports must produce exactly two files in report_dir."""
        # Arrange
        result = _pass_result()
        # Act
        html_path, json_path = write_reports(result, tmp_path)
        # Assert
        assert html_path.exists()
        assert json_path.exists()

    def test_html_filename_matches_pattern(self, tmp_path: Path) -> None:
        """HTML filename must follow ``sbom-report-<stem>-<YYYYMMDD-HHMMSS>.html``."""
        result = _pass_result(file_path="/data/bom.json")
        html_path, _ = write_reports(result, tmp_path)
        pattern = re.compile(r"^sbom-report-bom-\d{8}-\d{6}\.html$")
        assert pattern.match(html_path.name), f"Unexpected HTML filename: {html_path.name}"

    def test_json_filename_matches_pattern(self, tmp_path: Path) -> None:
        """JSON filename must follow ``sbom-report-<stem>-<YYYYMMDD-HHMMSS>.json``."""
        result = _pass_result(file_path="/data/bom.json")
        _, json_path = write_reports(result, tmp_path)
        pattern = re.compile(r"^sbom-report-bom-\d{8}-\d{6}\.json$")
        assert pattern.match(json_path.name), f"Unexpected JSON filename: {json_path.name}"

    def test_html_and_json_share_timestamp_in_name(self, tmp_path: Path) -> None:
        """Both files must carry the identical <YYYYMMDD-HHMMSS> timestamp stem."""
        result = _pass_result(file_path="/data/bom.json")
        html_path, json_path = write_reports(result, tmp_path)
        # Extract the timestamp portion from each name
        ts_pattern = re.compile(r"sbom-report-bom-(\d{8}-\d{6})\.")
        html_ts = ts_pattern.search(html_path.name)
        json_ts = ts_pattern.search(json_path.name)
        assert html_ts is not None, f"Could not extract timestamp from HTML name: {html_path.name}"
        assert json_ts is not None, f"Could not extract timestamp from JSON name: {json_path.name}"
        assert html_ts.group(1) == json_ts.group(1), "HTML and JSON timestamps must be identical"

    def test_stem_derived_from_file_path(self, tmp_path: Path) -> None:
        """The filename stem must be Path(result.file_path).stem."""
        result = _pass_result(file_path="/data/my-sbom.cdx.json")
        html_path, _ = write_reports(result, tmp_path)
        # Path("my-sbom.cdx.json").stem == "my-sbom.cdx"
        assert html_path.name.startswith(
            "sbom-report-my-sbom.cdx-"
        ), f"Expected stem 'my-sbom.cdx' in filename, got: {html_path.name}"

    def test_report_dir_created_if_not_exists(self, tmp_path: Path) -> None:
        """write_reports must create report_dir (and parents) when it doesn't exist."""
        subdir = tmp_path / "new" / "nested" / "dir"
        assert not subdir.exists()
        result = _pass_result()
        write_reports(result, subdir)
        assert subdir.is_dir()

    def test_files_written_inside_report_dir(self, tmp_path: Path) -> None:
        """Both returned paths must be children of report_dir."""
        result = _pass_result()
        html_path, json_path = write_reports(result, tmp_path)
        assert html_path.parent == tmp_path
        assert json_path.parent == tmp_path


# ===========================================================================
# TestJsonReportContent
# ===========================================================================


class TestJsonReportContent:
    """JSON report content matches the ADR-007 schema."""

    def _load_json(self, result: ValidationResult, tmp_path: Path) -> dict:
        _, json_path = write_reports(result, tmp_path)
        return json.loads(json_path.read_text(encoding="utf-8"))

    def test_json_is_parseable(self, tmp_path: Path) -> None:
        """The JSON file must be valid parseable JSON."""
        _, json_path = write_reports(_pass_result(), tmp_path)
        # Should not raise
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_json_has_generated_at_key(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert "generated_at" in data

    def test_json_has_tool_version_key(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert "tool_version" in data

    def test_json_has_file_path_key(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert "file_path" in data

    def test_json_has_format_detected_key(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert "format_detected" in data

    def test_json_has_status_key(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert "status" in data

    def test_json_has_summary_key(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert "summary" in data

    def test_json_has_issues_key(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert "issues" in data

    def test_json_status_pass_for_passing_result(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert data["status"] == "PASS"

    def test_json_status_fail_for_failing_result(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert data["status"] == "FAIL"

    def test_json_status_error_for_error_result(self, tmp_path: Path) -> None:
        data = self._load_json(_error_result(), tmp_path)
        assert data["status"] == "ERROR"

    def test_json_file_path_matches_result(self, tmp_path: Path) -> None:
        result = _pass_result(file_path="/some/path/bom.json")
        data = self._load_json(result, tmp_path)
        assert data["file_path"] == "/some/path/bom.json"

    def test_json_format_detected_spdx_expanded(self, tmp_path: Path) -> None:
        """Internal token 'spdx' must be expanded to 'spdx-2.3'."""
        result = ValidationResult(
            status=ValidationStatus.PASS,
            file_path="/tmp/bom.json",
            format_detected="spdx",
            issues=(),
        )
        data = self._load_json(result, tmp_path)
        assert data["format_detected"] == "spdx-2.3"

    def test_json_format_detected_cyclonedx_expanded(self, tmp_path: Path) -> None:
        """Internal token 'cyclonedx' must be expanded to 'cyclonedx-1.6'."""
        result = ValidationResult(
            status=ValidationStatus.PASS,
            file_path="/tmp/bom.json",
            format_detected="cyclonedx",
            issues=(),
        )
        data = self._load_json(result, tmp_path)
        assert data["format_detected"] == "cyclonedx-1.6"

    def test_json_format_detected_null_when_none(self, tmp_path: Path) -> None:
        """format_detected must be JSON null when result.format_detected is None."""
        data = self._load_json(_error_result(), tmp_path)
        assert data["format_detected"] is None

    def test_json_tool_version_is_non_empty_string(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert isinstance(data["tool_version"], str)
        assert len(data["tool_version"]) > 0

    def test_json_generated_at_is_iso8601_utc(self, tmp_path: Path) -> None:
        """generated_at must match the format ``YYYY-MM-DDTHH:MM:SSZ``."""
        data = self._load_json(_pass_result(), tmp_path)
        iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        assert iso_pattern.match(
            data["generated_at"]
        ), f"generated_at is not ISO 8601 UTC: {data['generated_at']}"

    def test_json_summary_has_error_count(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert "error_count" in data["summary"]

    def test_json_summary_has_warning_count(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert "warning_count" in data["summary"]

    def test_json_summary_has_info_count(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert "info_count" in data["summary"]

    def test_json_summary_error_count_correct(self, tmp_path: Path) -> None:
        # _fail_result has 1 ERROR and 1 WARNING
        data = self._load_json(_fail_result(), tmp_path)
        assert data["summary"]["error_count"] == 1

    def test_json_summary_warning_count_correct(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert data["summary"]["warning_count"] == 1

    def test_json_summary_info_count_correct(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert data["summary"]["info_count"] == 0

    def test_json_summary_all_zero_for_pass(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert data["summary"]["error_count"] == 0
        assert data["summary"]["warning_count"] == 0
        assert data["summary"]["info_count"] == 0

    def test_json_summary_counts_all_severities(self, tmp_path: Path) -> None:
        """When result has all three severities, counts must be correct."""
        data = self._load_json(_multi_issue_result(), tmp_path)
        assert data["summary"]["error_count"] == 1
        assert data["summary"]["warning_count"] == 1
        assert data["summary"]["info_count"] == 1

    def test_json_issues_is_list(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert isinstance(data["issues"], list)

    def test_json_issues_empty_for_pass(self, tmp_path: Path) -> None:
        data = self._load_json(_pass_result(), tmp_path)
        assert data["issues"] == []

    def test_json_issues_length_matches_result(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert len(data["issues"]) == 2

    def test_json_issue_has_severity_key(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert "severity" in data["issues"][0]

    def test_json_issue_has_rule_key(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert "rule" in data["issues"][0]

    def test_json_issue_has_field_path_key(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert "field_path" in data["issues"][0]

    def test_json_issue_has_message_key(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        assert "message" in data["issues"][0]

    def test_json_issue_severity_value_is_string(self, tmp_path: Path) -> None:
        data = self._load_json(_fail_result(), tmp_path)
        for issue in data["issues"]:
            assert isinstance(issue["severity"], str)
            assert issue["severity"] in ("ERROR", "WARNING", "INFO")

    def test_json_issues_sorted_errors_first(self, tmp_path: Path) -> None:
        """Issues must be sorted: ERROR first, then WARNING, then INFO."""
        data = self._load_json(_multi_issue_result(), tmp_path)
        severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
        severities = [severity_order[i["severity"]] for i in data["issues"]]
        assert severities == sorted(
            severities
        ), f"Issues not sorted by severity: {[i['severity'] for i in data['issues']]}"


# ===========================================================================
# TestHtmlReportContent
# ===========================================================================


class TestHtmlReportContent:
    """HTML report contains the required structural elements and data."""

    def _load_html(self, result: ValidationResult, tmp_path: Path) -> str:
        html_path, _ = write_reports(result, tmp_path)
        return html_path.read_text(encoding="utf-8")

    def test_html_contains_html_tag(self, tmp_path: Path) -> None:
        html = self._load_html(_pass_result(), tmp_path)
        assert "<html" in html.lower()

    def test_html_contains_body_tag(self, tmp_path: Path) -> None:
        html = self._load_html(_pass_result(), tmp_path)
        assert "<body" in html.lower()

    def test_html_contains_file_path(self, tmp_path: Path) -> None:
        result = _pass_result(file_path="/data/my-bom.json")
        html = self._load_html(result, tmp_path)
        assert "/data/my-bom.json" in html

    def test_html_contains_pass_status(self, tmp_path: Path) -> None:
        html = self._load_html(_pass_result(), tmp_path)
        assert "PASS" in html

    def test_html_contains_fail_status(self, tmp_path: Path) -> None:
        html = self._load_html(_fail_result(), tmp_path)
        assert "FAIL" in html

    def test_html_contains_error_status(self, tmp_path: Path) -> None:
        html = self._load_html(_error_result(), tmp_path)
        assert "ERROR" in html

    def test_html_contains_generated_at_timestamp(self, tmp_path: Path) -> None:
        """The HTML must include the generated_at value (ISO 8601 pattern)."""
        html = self._load_html(_pass_result(), tmp_path)
        iso_pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
        assert iso_pattern.search(html), "HTML does not contain an ISO 8601 timestamp"

    def test_html_contains_issues_table_structure(self, tmp_path: Path) -> None:
        """When there are issues, the HTML must contain a table element."""
        html = self._load_html(_fail_result(), tmp_path)
        assert (
            "<table" in html.lower() or "<th" in html.lower()
        ), "HTML does not contain a table or table-header element"

    def test_html_contains_issue_message(self, tmp_path: Path) -> None:
        """Each issue message must appear in the HTML body."""
        html = self._load_html(_fail_result(), tmp_path)
        assert _ISSUE_ERROR.message in html
        assert _ISSUE_WARNING.message in html

    def test_html_contains_no_issues_indication_on_pass(self, tmp_path: Path) -> None:
        """When status is PASS with no issues, an appropriate indication is present."""
        html = self._load_html(_pass_result(), tmp_path)
        # Could be "No issues found." or similar — just verify something positive
        assert "no issues" in html.lower() or "PASS" in html

    def test_html_contains_all_issue_messages_multi(self, tmp_path: Path) -> None:
        """All three severity-level messages appear in the HTML."""
        html = self._load_html(_multi_issue_result(), tmp_path)
        assert _ISSUE_ERROR.message in html
        assert _ISSUE_WARNING.message in html
        assert _ISSUE_INFO.message in html

    def test_html_is_non_empty(self, tmp_path: Path) -> None:
        html = self._load_html(_pass_result(), tmp_path)
        assert len(html.strip()) > 0

    def test_html_humanizes_xml_field_paths_and_messages(self, tmp_path: Path) -> None:
        xml_issue = ValidationIssue(
            severity=IssueSeverity.ERROR,
            field_path=(
                "/{http://cyclonedx.org/schema/bom/1.6}bom/"
                "{http://cyclonedx.org/schema/bom/1.6}components/"
                "{http://cyclonedx.org/schema/bom/1.6}component"
            ),
            message=(
                "Unexpected child with tag '{http://cyclonedx.org/schema/bom/1.6}version' "
                "at position 2. Tag 'bom:name' expected."
            ),
            rule="FR-03",
        )
        result = ValidationResult(
            status=ValidationStatus.FAIL,
            file_path="/tmp/bom.xml",
            format_detected="cyclonedx",
            issues=(xml_issue,),
        )
        html = self._load_html(result, tmp_path)
        assert "/bom/components/component" in html
        assert "{http://cyclonedx.org/schema/bom/1.6}" not in html
        assert "Element &#x27;name&#x27;" in html or "Element 'name'" in html

    def test_html_hides_ntia_rule_ids_and_adds_supplier_hint(self, tmp_path: Path) -> None:
        ntia_issue = ValidationIssue(
            severity=IssueSeverity.ERROR,
            field_path="components[0].supplier",
            message="Component 'requests' is missing a supplier name (NTIA FR-04)",
            rule="FR-04",
        )
        result = ValidationResult(
            status=ValidationStatus.FAIL,
            file_path="/tmp/bom.json",
            format_detected="cyclonedx",
            issues=(ntia_issue,),
        )
        html = self._load_html(result, tmp_path)
        assert "NTIA FR-04" not in html
        assert "provide a supplier/organization name" in html
        assert "<th>Hint</th>" in html
        assert (
            "Component &#x27;requests&#x27; is missing a supplier name." in html
            or "Component 'requests' is missing a supplier name." in html
        )

    def test_html_places_message_and_hint_in_separate_columns(self, tmp_path: Path) -> None:
        xml_issue = ValidationIssue(
            severity=IssueSeverity.ERROR,
            field_path="packages.0",
            message="'SPDXID' is a required property",
            rule="FR-02",
        )
        result = ValidationResult(
            status=ValidationStatus.FAIL,
            file_path="/tmp/bom.json",
            format_detected="spdx",
            issues=(xml_issue,),
        )
        html = self._load_html(result, tmp_path)
        assert (
            "Missing required field &#x27;SPDXID&#x27;." in html
            or "Missing required field 'SPDXID'." in html
        )
        assert (
            "add &#x27;SPDXID&#x27; at this location." in html
            or "add 'SPDXID' at this location." in html
        )


# ===========================================================================
# TestReturnValue
# ===========================================================================


class TestReturnValue:
    """write_reports returns (html_path, json_path) and both files exist."""

    def test_returns_tuple_of_two_paths(self, tmp_path: Path) -> None:
        result = _pass_result()
        rv = write_reports(result, tmp_path)
        assert isinstance(rv, tuple)
        assert len(rv) == 2

    def test_first_element_is_html_path(self, tmp_path: Path) -> None:
        result = _pass_result()
        html_path, _ = write_reports(result, tmp_path)
        assert isinstance(html_path, Path)
        assert html_path.suffix == ".html"

    def test_second_element_is_json_path(self, tmp_path: Path) -> None:
        result = _pass_result()
        _, json_path = write_reports(result, tmp_path)
        assert isinstance(json_path, Path)
        assert json_path.suffix == ".json"

    def test_returned_html_path_exists(self, tmp_path: Path) -> None:
        result = _pass_result()
        html_path, _ = write_reports(result, tmp_path)
        assert html_path.exists()

    def test_returned_json_path_exists(self, tmp_path: Path) -> None:
        result = _pass_result()
        _, json_path = write_reports(result, tmp_path)
        assert json_path.exists()


# ===========================================================================
# TestToolVersionFallback
# ===========================================================================


class TestToolVersionFallback:
    """_tool_version() returns the fallback string when the package is not installed.

    Covers lines 169-170 of report_writer.py: the PackageNotFoundError branch
    inside _tool_version().
    """

    def test_tool_version_fallback_when_package_not_found(self, tmp_path: Path) -> None:
        """When importlib.metadata.version raises PackageNotFoundError,
        _tool_version() must return the fallback 'unknown'."""
        from sbom_validator.report_writer import _tool_version

        with patch(
            "sbom_validator.report_writer.importlib.metadata.version",
            side_effect=importlib.metadata.PackageNotFoundError("sbom-validator"),
        ):
            version = _tool_version()

        assert version == "unknown"

    def test_write_reports_uses_fallback_version_in_json(self, tmp_path: Path) -> None:
        """When the package is not installed, write_reports must still produce a
        valid JSON report containing the fallback version string."""
        with patch(
            "sbom_validator.report_writer.importlib.metadata.version",
            side_effect=importlib.metadata.PackageNotFoundError("sbom-validator"),
        ):
            _, json_path = write_reports(_pass_result(), tmp_path)

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["tool_version"] == "unknown"

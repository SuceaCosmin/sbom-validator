"""Unit tests for sbom_validator.format_detector.

Tests cover the detect_format(file_path: Path) -> str function, which inspects
JSON/XML input to determine whether the SBOM is in SPDX or CycloneDX format.

Expected behaviour:
- Returns "spdx" when the JSON contains a top-level "spdxVersion" key.
- Returns "cyclonedx" when the JSON contains "bomFormat": "CycloneDX".
- Raises UnsupportedFormatError when neither key is present or bomFormat has
  an unrecognised value.
- Raises ParseError when the file does not exist or cannot be read.
- Raises UnsupportedFormatError for malformed/unknown content.

Real fixture files are used for the happy-path detection tests; temporary
files (via the pytest `tmp_path` fixture) are used for edge-case scenarios.
"""

import json
from pathlib import Path

import pytest

from sbom_validator.exceptions import ParseError, UnsupportedFormatError
from sbom_validator.format_detector import detect_format

# ---------------------------------------------------------------------------
# Paths to real fixture files
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SPDX_FIXTURE = FIXTURES_DIR / "spdx" / "valid-minimal.spdx.json"
CYCLONEDX_FIXTURE = FIXTURES_DIR / "cyclonedx" / "valid-minimal.cdx.json"
CYCLONEDX_XML_FIXTURE = FIXTURES_DIR / "cyclonedx" / "valid-minimal.cdx.xml"


# ---------------------------------------------------------------------------
# Detection from real fixture files
# ---------------------------------------------------------------------------


class TestDetectFormatFromFixtures:
    def test_valid_spdx_fixture_returns_spdx(self):
        assert detect_format(SPDX_FIXTURE) == "spdx"

    def test_valid_cyclonedx_fixture_returns_cyclonedx(self):
        assert detect_format(CYCLONEDX_FIXTURE) == "cyclonedx"

    def test_valid_cyclonedx_xml_fixture_returns_cyclonedx(self):
        assert detect_format(CYCLONEDX_XML_FIXTURE) == "cyclonedx"


# ---------------------------------------------------------------------------
# Detection edge cases using temporary JSON files
# ---------------------------------------------------------------------------


class TestDetectFormatEdgeCases:
    def test_json_with_only_spdx_version_key_returns_spdx(self, tmp_path: Path):
        f = tmp_path / "minimal.spdx.json"
        f.write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
        assert detect_format(f) == "spdx"

    def test_json_with_bom_format_cyclonedx_returns_cyclonedx(self, tmp_path: Path):
        f = tmp_path / "minimal.cdx.json"
        f.write_text(
            json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.6"}),
            encoding="utf-8",
        )
        assert detect_format(f) == "cyclonedx"

    def test_json_with_both_keys_returns_spdx(self, tmp_path: Path):
        """When both spdxVersion and bomFormat are present, spdxVersion takes
        precedence and the function returns "spdx"."""
        f = tmp_path / "ambiguous.json"
        f.write_text(
            json.dumps({"spdxVersion": "SPDX-2.3", "bomFormat": "CycloneDX"}),
            encoding="utf-8",
        )
        assert detect_format(f) == "spdx"

    def test_json_with_neither_key_raises_unsupported_format_error(self, tmp_path: Path):
        f = tmp_path / "unknown.json"
        f.write_text(json.dumps({"name": "my-sbom", "version": "1.0"}), encoding="utf-8")
        with pytest.raises(UnsupportedFormatError):
            detect_format(f)

    def test_json_with_bom_format_other_value_raises_unsupported_format_error(self, tmp_path: Path):
        f = tmp_path / "other_format.json"
        f.write_text(json.dumps({"bomFormat": "SomethingElse"}), encoding="utf-8")
        with pytest.raises(UnsupportedFormatError):
            detect_format(f)

    def test_json_with_empty_object_raises_unsupported_format_error(self, tmp_path: Path):
        f = tmp_path / "empty_object.json"
        f.write_text(json.dumps({}), encoding="utf-8")
        with pytest.raises(UnsupportedFormatError):
            detect_format(f)

    def test_spdx_version_22_raises_unsupported_format_error(self, tmp_path: Path):
        """SPDX 2.2 is not supported; only SPDX-2.3 is accepted."""
        f = tmp_path / "spdx22.json"
        f.write_text(json.dumps({"spdxVersion": "SPDX-2.2", "name": "test"}), encoding="utf-8")
        with pytest.raises(UnsupportedFormatError):
            detect_format(f)

    def test_cyclonedx_spec_version_15_returns_cyclonedx(self, tmp_path: Path):
        """CycloneDX 1.5 is now supported."""
        f = tmp_path / "cdx15.json"
        f.write_text(
            json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.5"}),
            encoding="utf-8",
        )
        assert detect_format(f) == "cyclonedx"

    def test_cyclonedx_spec_version_14_returns_cyclonedx(self, tmp_path: Path):
        """CycloneDX 1.4 is supported."""
        f = tmp_path / "cdx14.json"
        f.write_text(
            json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.4"}),
            encoding="utf-8",
        )
        assert detect_format(f) == "cyclonedx"

    def test_cyclonedx_spec_version_13_returns_cyclonedx(self, tmp_path: Path):
        """CycloneDX 1.3 is supported."""
        f = tmp_path / "cdx13.json"
        f.write_text(
            json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.3"}),
            encoding="utf-8",
        )
        assert detect_format(f) == "cyclonedx"

    def test_cyclonedx_spec_version_12_raises_unsupported_format_error(self, tmp_path: Path):
        """CycloneDX 1.2 is not supported; only 1.3–1.6 are accepted."""
        f = tmp_path / "cdx12.json"
        f.write_text(
            json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.2"}),
            encoding="utf-8",
        )
        with pytest.raises(UnsupportedFormatError):
            detect_format(f)

    def test_cyclonedx_missing_spec_version_raises_unsupported_format_error(self, tmp_path: Path):
        """CycloneDX without specVersion is not supported."""
        f = tmp_path / "cdx_no_spec.json"
        f.write_text(json.dumps({"bomFormat": "CycloneDX"}), encoding="utf-8")
        with pytest.raises(UnsupportedFormatError):
            detect_format(f)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestDetectFormatErrorCases:
    def test_nonexistent_file_raises_parse_error(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist.json"
        with pytest.raises(ParseError):
            detect_format(missing)

    def test_file_with_invalid_json_raises_unsupported_format_error(self, tmp_path: Path):
        f = tmp_path / "bad.json"
        f.write_text("not json {{{{", encoding="utf-8")
        with pytest.raises(UnsupportedFormatError):
            detect_format(f)

    def test_empty_file_raises_parse_error(self, tmp_path: Path):
        f = tmp_path / "empty.json"
        f.write_text("", encoding="utf-8")
        with pytest.raises(UnsupportedFormatError):
            detect_format(f)

    def test_xml_with_unsupported_namespace_raises_unsupported_format_error(self, tmp_path: Path):
        f = tmp_path / "bad-version.cdx.xml"
        f.write_text(
            '<bom xmlns="http://cyclonedx.org/schema/bom/1.2" version="1" />',
            encoding="utf-8",
        )
        with pytest.raises(UnsupportedFormatError):
            detect_format(f)

    def test_xml_with_supported_13_namespace_returns_cyclonedx(self, tmp_path: Path):
        f = tmp_path / "cdx13.cdx.xml"
        f.write_text(
            '<bom xmlns="http://cyclonedx.org/schema/bom/1.3" version="1" />',
            encoding="utf-8",
        )
        assert detect_format(f) == "cyclonedx"

    def test_xml_with_supported_14_namespace_returns_cyclonedx(self, tmp_path: Path):
        f = tmp_path / "cdx14.cdx.xml"
        f.write_text(
            '<bom xmlns="http://cyclonedx.org/schema/bom/1.4" version="1" />',
            encoding="utf-8",
        )
        assert detect_format(f) == "cyclonedx"

    def test_xml_with_supported_15_namespace_returns_cyclonedx(self, tmp_path: Path):
        f = tmp_path / "cdx15.cdx.xml"
        f.write_text(
            '<bom xmlns="http://cyclonedx.org/schema/bom/1.5" version="1" />',
            encoding="utf-8",
        )
        assert detect_format(f) == "cyclonedx"

    def test_file_with_json_array_raises_unsupported_format_error_or_parse_error(
        self, tmp_path: Path
    ):
        """A JSON array at the root has no top-level keys; the function should
        signal that the format is unrecognisable (either UnsupportedFormatError
        or ParseError is acceptable here)."""
        f = tmp_path / "array.json"
        f.write_text(json.dumps([{"spdxVersion": "SPDX-2.3"}]), encoding="utf-8")
        with pytest.raises((UnsupportedFormatError, ParseError)):
            detect_format(f)

    def test_file_with_json_string_raises_parse_error_or_unsupported_format_error(
        self, tmp_path: Path
    ):
        """A bare JSON string is valid JSON but not a mapping; the function
        must not return a format string."""
        f = tmp_path / "string.json"
        f.write_text(json.dumps("spdxVersion"), encoding="utf-8")
        with pytest.raises((UnsupportedFormatError, ParseError)):
            detect_format(f)

    def test_os_error_on_read_raises_parse_error(self, tmp_path: Path):
        """An OSError raised by read_text (e.g. permission denied) must be
        wrapped in a ParseError (covers lines 26-27 of format_detector.py)."""
        from unittest.mock import patch

        f = tmp_path / "unreadable.json"
        f.write_text("{}", encoding="utf-8")
        with patch.object(type(f), "read_text", side_effect=OSError("permission denied")):
            with pytest.raises(ParseError):
                detect_format(f)

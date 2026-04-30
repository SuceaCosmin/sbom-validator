"""Tests for SPDX 3.x constants added in v0.6.0 (task 2.C1)."""

from __future__ import annotations

from sbom_validator import constants


def test_format_spdx3_jsonld_value() -> None:
    assert constants.FORMAT_SPDX3_JSONLD == "spdx3-jsonld"


def test_spdx3_context_url_value() -> None:
    assert constants.SPDX3_CONTEXT_URL == "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"


def test_spdx3_schema_file_value() -> None:
    assert constants.SPDX3_SCHEMA_FILE == "spdx-3.0.1.schema.json"


def test_rule_spdx3_schema_value() -> None:
    assert constants.RULE_SPDX3_SCHEMA == "FR-15"


def test_spdx3_constants_are_strings() -> None:
    assert isinstance(constants.FORMAT_SPDX3_JSONLD, str)
    assert isinstance(constants.SPDX3_CONTEXT_URL, str)
    assert isinstance(constants.SPDX3_SCHEMA_FILE, str)
    assert isinstance(constants.RULE_SPDX3_SCHEMA, str)


def test_spdx3_format_distinct_from_spdx2() -> None:
    assert constants.FORMAT_SPDX3_JSONLD != constants.FORMAT_SPDX
    assert constants.FORMAT_SPDX3_JSONLD != constants.FORMAT_SPDX_TV
    assert constants.FORMAT_SPDX3_JSONLD != constants.FORMAT_SPDX_YAML


def test_rule_spdx3_schema_distinct_from_spdx2_rule() -> None:
    assert constants.RULE_SPDX3_SCHEMA != constants.RULE_SPDX_SCHEMA

"""Unit tests for sbom_validator.models.

Tests cover all data model types: ValidationStatus, IssueSeverity,
ValidationIssue, NormalizedComponent, NormalizedRelationship, NormalizedSBOM,
and ValidationResult. All dataclasses are frozen, so immutability is verified
for each. Enum string values, default field values, and equality semantics are
also exercised.
"""

from dataclasses import FrozenInstanceError

import pytest
from sbom_validator.models import (
    IssueSeverity,
    NormalizedComponent,
    NormalizedRelationship,
    NormalizedSBOM,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)

# ---------------------------------------------------------------------------
# ValidationStatus
# ---------------------------------------------------------------------------


class TestValidationStatus:
    def test_pass_value_equals_string(self):
        assert ValidationStatus.PASS.value == "PASS"

    def test_fail_value_equals_string(self):
        assert ValidationStatus.FAIL.value == "FAIL"

    def test_error_value_equals_string(self):
        assert ValidationStatus.ERROR.value == "ERROR"

    def test_has_exactly_three_members(self):
        assert len(ValidationStatus) == 3


# ---------------------------------------------------------------------------
# IssueSeverity
# ---------------------------------------------------------------------------


class TestIssueSeverity:
    def test_error_value_equals_string(self):
        assert IssueSeverity.ERROR.value == "ERROR"

    def test_warning_value_equals_string(self):
        assert IssueSeverity.WARNING.value == "WARNING"

    def test_info_value_equals_string(self):
        assert IssueSeverity.INFO.value == "INFO"


# ---------------------------------------------------------------------------
# ValidationIssue
# ---------------------------------------------------------------------------


class TestValidationIssue:
    def test_instantiation_with_all_fields(self):
        issue = ValidationIssue(
            severity=IssueSeverity.ERROR,
            field_path="packages[0].name",
            message="Name is missing",
            rule="PKG-001",
        )
        assert issue.severity == IssueSeverity.ERROR
        assert issue.field_path == "packages[0].name"
        assert issue.message == "Name is missing"
        assert issue.rule == "PKG-001"

    def test_instantiation_with_required_fields_only_rule_defaults_to_empty_string(self):
        issue = ValidationIssue(
            severity=IssueSeverity.WARNING,
            field_path="metadata.author",
            message="Author not provided",
        )
        assert issue.rule == ""

    def test_immutability_raises_frozen_instance_error(self):
        issue = ValidationIssue(
            severity=IssueSeverity.INFO,
            field_path="root",
            message="Info note",
        )
        with pytest.raises(FrozenInstanceError):
            issue.message = "changed"  # type: ignore[misc]

    def test_equality_same_fields_are_equal(self):
        issue_a = ValidationIssue(
            severity=IssueSeverity.ERROR,
            field_path="foo.bar",
            message="Something wrong",
            rule="R-01",
        )
        issue_b = ValidationIssue(
            severity=IssueSeverity.ERROR,
            field_path="foo.bar",
            message="Something wrong",
            rule="R-01",
        )
        assert issue_a == issue_b

    def test_equality_different_fields_are_not_equal(self):
        issue_a = ValidationIssue(
            severity=IssueSeverity.ERROR,
            field_path="foo",
            message="msg",
        )
        issue_b = ValidationIssue(
            severity=IssueSeverity.WARNING,
            field_path="foo",
            message="msg",
        )
        assert issue_a != issue_b


# ---------------------------------------------------------------------------
# NormalizedComponent
# ---------------------------------------------------------------------------


class TestNormalizedComponent:
    def test_instantiation_with_required_fields_only(self):
        comp = NormalizedComponent(component_id="comp-1", name="requests")
        assert comp.component_id == "comp-1"
        assert comp.name == "requests"
        assert comp.version is None
        assert comp.supplier is None

    def test_identifiers_defaults_to_empty_tuple(self):
        comp = NormalizedComponent(component_id="comp-1", name="requests")
        assert comp.identifiers == ()
        assert isinstance(comp.identifiers, tuple)

    def test_instantiation_with_all_fields(self):
        comp = NormalizedComponent(
            component_id="comp-2",
            name="flask",
            version="3.0.0",
            supplier="Pallets Projects",
            identifiers=("pkg:pypi/flask@3.0.0",),
        )
        assert comp.version == "3.0.0"
        assert comp.supplier == "Pallets Projects"
        assert comp.identifiers == ("pkg:pypi/flask@3.0.0",)

    def test_immutability_raises_frozen_instance_error(self):
        comp = NormalizedComponent(component_id="comp-1", name="requests")
        with pytest.raises(FrozenInstanceError):
            comp.name = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# NormalizedRelationship
# ---------------------------------------------------------------------------


class TestNormalizedRelationship:
    def test_instantiation_with_required_fields(self):
        rel = NormalizedRelationship(from_id="comp-a", to_id="comp-b")
        assert rel.from_id == "comp-a"
        assert rel.to_id == "comp-b"

    def test_relationship_type_defaults_to_depends_on(self):
        rel = NormalizedRelationship(from_id="comp-a", to_id="comp-b")
        assert rel.relationship_type == "DEPENDS_ON"

    def test_relationship_type_can_be_overridden(self):
        rel = NormalizedRelationship(
            from_id="comp-a", to_id="comp-b", relationship_type="DESCRIBES"
        )
        assert rel.relationship_type == "DESCRIBES"

    def test_immutability_raises_frozen_instance_error(self):
        rel = NormalizedRelationship(from_id="comp-a", to_id="comp-b")
        with pytest.raises(FrozenInstanceError):
            rel.from_id = "comp-x"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# NormalizedSBOM
# ---------------------------------------------------------------------------


class TestNormalizedSBOM:
    def test_instantiation_with_format_only(self):
        sbom = NormalizedSBOM(format="spdx")
        assert sbom.format == "spdx"

    def test_components_defaults_to_empty_tuple(self):
        sbom = NormalizedSBOM(format="spdx")
        assert sbom.components == ()
        assert isinstance(sbom.components, tuple)

    def test_relationships_defaults_to_empty_tuple(self):
        sbom = NormalizedSBOM(format="spdx")
        assert sbom.relationships == ()
        assert isinstance(sbom.relationships, tuple)

    def test_author_defaults_to_none(self):
        sbom = NormalizedSBOM(format="cyclonedx")
        assert sbom.author is None

    def test_timestamp_defaults_to_none(self):
        sbom = NormalizedSBOM(format="cyclonedx")
        assert sbom.timestamp is None

    def test_immutability_raises_frozen_instance_error(self):
        sbom = NormalizedSBOM(format="spdx")
        with pytest.raises(FrozenInstanceError):
            sbom.format = "cyclonedx"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_instantiation_with_status_and_file_path(self):
        result = ValidationResult(status=ValidationStatus.PASS, file_path="/path/to/sbom.json")
        assert result.status == ValidationStatus.PASS
        assert result.file_path == "/path/to/sbom.json"

    def test_issues_defaults_to_empty_tuple(self):
        result = ValidationResult(status=ValidationStatus.PASS, file_path="/path/to/sbom.json")
        assert result.issues == ()
        assert isinstance(result.issues, tuple)

    def test_format_detected_defaults_to_none(self):
        result = ValidationResult(status=ValidationStatus.FAIL, file_path="/path/to/sbom.json")
        assert result.format_detected is None

    def test_instantiation_with_all_fields(self):
        issue = ValidationIssue(
            severity=IssueSeverity.ERROR,
            field_path="root",
            message="Missing required field",
        )
        result = ValidationResult(
            status=ValidationStatus.FAIL,
            file_path="/path/to/sbom.json",
            issues=(issue,),
            format_detected="spdx",
        )
        assert result.issues == (issue,)
        assert result.format_detected == "spdx"

    def test_immutability_raises_frozen_instance_error(self):
        result = ValidationResult(status=ValidationStatus.PASS, file_path="/path/to/sbom.json")
        with pytest.raises(FrozenInstanceError):
            result.status = ValidationStatus.FAIL  # type: ignore[misc]

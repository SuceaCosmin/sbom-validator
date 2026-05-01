"""Schema bundle integrity tests.

Verifies that every JSON schema in src/sbom_validator/schemas/ is self-contained:
all external $ref URIs declared within each schema must resolve against the local
bundle without any network access.

This test was introduced after the CycloneDX auxiliary schemas (spdx.schema.json
and jsf-0.82.schema.json) were missing from the bundle from v0.3.0 through v0.5.0,
causing jsonschema to silently fall back to remote HTTP fetches during validation.
A missing auxiliary schema would fail here at CI time rather than at runtime in an
air-gapped environment.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable

_SCHEMAS_DIR = Path(__file__).parent.parent.parent / "src" / "sbom_validator" / "schemas"

_REQUIRED_SCHEMA_FILES = frozenset(
    {
        "spdx-2.3.schema.json",
        "spdx-3.0.1.schema.json",
        "cyclonedx-1.3.schema.json",
        "cyclonedx-1.4.schema.json",
        "cyclonedx-1.5.schema.json",
        "cyclonedx-1.6.schema.json",
        "spdx.schema.json",
        "jsf-0.82.schema.json",
    }
)


def _load_all_schemas() -> dict[str, dict[str, Any]]:
    """Return {filename: schema_dict} for every .json file in the bundle."""
    return {
        f.name: json.loads(f.read_text(encoding="utf-8"))
        for f in sorted(_SCHEMAS_DIR.glob("*.json"))
    }


def _build_registry(schemas: dict[str, dict[str, Any]]) -> Registry:
    """Build a Registry pre-populated with every schema keyed by its $id URI."""
    resources: list[tuple[str, Resource[Any]]] = []
    for schema in schemas.values():
        schema_id: str = schema.get("$id", "")
        if schema_id:
            resources.append((schema_id, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _collect_external_refs(obj: Any) -> set[str]:
    """Recursively collect all $ref values that are not internal fragment-only refs."""
    refs: set[str] = set()
    if isinstance(obj, dict):
        ref: str = obj.get("$ref", "")
        if ref and not ref.startswith("#"):
            refs.add(ref)
        for value in obj.values():
            refs |= _collect_external_refs(value)
    elif isinstance(obj, list):
        for item in obj:
            refs |= _collect_external_refs(item)
    return refs


class TestSchemaBundleIntegrity:
    """All bundled JSON schemas must be self-contained with no external $ref targets."""

    def test_required_schema_files_present(self) -> None:
        """Every schema file required by the validator must exist in the bundle."""
        present = {f.name for f in _SCHEMAS_DIR.glob("*.json")}
        missing = _REQUIRED_SCHEMA_FILES - present
        assert not missing, (
            f"Required schema files are missing from src/sbom_validator/schemas/: {missing}"
        )

    def test_all_schema_files_parse_as_valid_json(self) -> None:
        """Every .json file in the bundle must parse without error and be a JSON object."""
        for path in sorted(_SCHEMAS_DIR.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(data, dict), (
                f"{path.name}: root must be a JSON object, got {type(data)}"
            )

    @pytest.mark.parametrize("schema_name,schema", list(_load_all_schemas().items()))
    def test_external_refs_resolve_within_local_bundle(
        self, schema_name: str, schema: dict[str, Any]
    ) -> None:
        """Every external $ref in a bundled schema must resolve within the local bundle.

        A failure here means a schema file is referenced by another bundled schema
        but is not itself present in src/sbom_validator/schemas/.  Add the missing
        auxiliary schema to that directory.
        """
        external_refs = _collect_external_refs(schema)
        if not external_refs:
            return

        all_schemas = _load_all_schemas()
        registry = _build_registry(all_schemas)
        # Resolve relative $ref URIs against this schema's own $id as the base URI.
        base_uri: str = schema.get("$id", "")
        resolver = registry.resolver(base_uri=base_uri)

        for ref_uri in sorted(external_refs):
            try:
                resolver.lookup(ref_uri)
            except Unresolvable:
                pytest.fail(
                    f"'{schema_name}' contains $ref '{ref_uri}' that cannot be resolved "
                    f"within the local schema bundle.  Add the missing schema file to "
                    f"src/sbom_validator/schemas/."
                )

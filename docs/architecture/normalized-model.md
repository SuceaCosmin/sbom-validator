# Normalized SBOM Model Specification

**Status:** Accepted  
**Date:** 2026-04-06  
**Related ADR:** ADR-002 — Parser Abstraction and Normalized Internal Model

---

## 1. Purpose

`sbom-validator` validates two structurally different SBOM formats — SPDX 2.3 JSON and CycloneDX 1.6 JSON — against a common set of NTIA minimum-element rules. Without a shared intermediate representation, every NTIA rule would need two parallel implementations: one for SPDX field paths and one for CycloneDX field paths. This approach does not scale and makes tests harder to write, since checker tests would require realistic format-specific fixtures.

The `NormalizedSBOM` model is a **format-agnostic internal representation** that sits between the parser layer and the validator layer. Its role is to absorb all format-specific differences so that:

- **NTIA checker rules** are written once, in terms of `NormalizedSBOM` fields, and work identically for both formats.
- **Parsers** are thin translation functions whose sole responsibility is converting a raw parsed JSON dict into a `NormalizedSBOM`. They do not enforce NTIA rules.
- **Tests** for the NTIA checker can construct `NormalizedSBOM` objects directly, without needing SPDX or CycloneDX knowledge.
- **Future formats** (e.g., SPDX 3.0, CycloneDX 1.7) only require a new parser, not changes to the checker.

The `NormalizedSBOM` model deliberately captures only the fields required to evaluate the seven NTIA minimum elements (FR-04 through FR-10). It is not a lossless representation of either format. Format-specific fields not relevant to NTIA compliance are discarded during parsing.

All three model types (`NormalizedSBOM`, `NormalizedComponent`, `NormalizedRelationship`) are **frozen dataclasses** (`@dataclass(frozen=True)`), making them immutable after construction. This is consistent with the approach used for the result model (ADR-004).

---

## 2. NormalizedSBOM Field Specification

`NormalizedSBOM` is the top-level container representing a single parsed SBOM document.

| Field | Python Type | Required | Description |
|---|---|---|---|
| `format` | `Literal["spdx", "cyclonedx"]` | Yes | The source format of the SBOM. Set by the parser; matches the value returned by `detect_format()`. Never `None`. |
| `author` | `str \| None` | No | The author or creator of the SBOM data (a tool name or organization name). Maps to NTIA element "Author of SBOM Data" (FR-09). `None` if the source document provides no authorship information. When multiple authors are present, parsers concatenate them as a comma-separated string (e.g., `"Tool: cargo-sbom, Organization: Acme Inc."`). |
| `timestamp` | `str \| None` | No | ISO 8601 date-time string recording when the SBOM was assembled (e.g., `"2024-01-15T10:30:00Z"`). Maps to NTIA element "Timestamp" (FR-10). `None` if the source document does not include a timestamp. Parsers do **not** validate the timestamp format; the NTIA checker performs format validation. |
| `components` | `tuple[NormalizedComponent, ...]` | Yes | All components (packages, libraries, applications) declared in the SBOM. An empty tuple is valid at the model level; the NTIA checker may raise issues if it is empty. Never `None`. |
| `relationships` | `tuple[NormalizedRelationship, ...]` | Yes | All declared dependency relationships between components. An empty tuple is valid at the model level; the NTIA checker raises an issue if no relationships exist (FR-08). Never `None`. |

**Construction example:**

```python
NormalizedSBOM(
    format="spdx",
    author="Tool: syft-0.95.0",
    timestamp="2024-03-10T12:00:00Z",
    components=(
        NormalizedComponent(
            component_id="SPDXRef-libfoo",
            name="libfoo",
            version="1.2.3",
            supplier="Acme Inc.",
            identifiers=("pkg:pypi/libfoo@1.2.3",),
        ),
    ),
    relationships=(
        NormalizedRelationship(
            from_id="SPDXRef-DOCUMENT",
            to_id="SPDXRef-libfoo",
            relationship_type="DEPENDS_ON",
        ),
    ),
)
```

---

## 3. NormalizedComponent Field Specification

`NormalizedComponent` represents a single software component declared in the SBOM. It maps to `packages[i]` in SPDX and `components[i]` in CycloneDX.

| Field | Python Type | Required | Description |
|---|---|---|---|
| `component_id` | `str` | Yes | A unique identifier for the component **within this SBOM document**. Used to correlate components with relationships. In SPDX this is the `SPDXID` field (e.g., `"SPDXRef-libfoo"`). In CycloneDX this is the `bom-ref` field (e.g., `"pkg:pypi/libfoo@1.2.3"` or a UUID). Never `None` or empty. |
| `name` | `str \| None` | No | The component's name (e.g., `"libfoo"`, `"numpy"`). Maps to NTIA element "Component Name" (FR-05). `None` if absent in the source. Parsers set this to `None` rather than empty string when the field is missing. |
| `version` | `str \| None` | No | The component's version string (e.g., `"1.2.3"`, `"2.0.0-beta.1"`). Maps to NTIA element "Component Version" (FR-06). `None` if absent or if the source value is `NOASSERTION` or an empty string. |
| `supplier` | `str \| None` | No | The name of the organization or tool that supplied the component. Maps to NTIA element "Supplier Name" (FR-04). `None` if absent. SPDX-specific prefixes (`"Organization: "`, `"Tool: "`) are stripped by the SPDX parser so this field always contains a plain name string. `NOASSERTION` values in SPDX are converted to `None`. |
| `identifiers` | `tuple[str, ...]` | No | A tuple of unique identifiers beyond name and version (PURLs and CPEs). Maps to NTIA element "Other Unique Identifiers" (FR-07). An empty tuple means no qualifying identifiers were found. Identifiers are stored as raw strings (e.g., `"pkg:pypi/libfoo@1.2.3"`, `"cpe:2.3:a:acme:libfoo:1.2.3:*:*:*:*:*:*:*"`). |

**Notes on `supplier` normalization:**

SPDX `packages[i].supplier` values follow the pattern `"Organization: Acme Inc."` or `"Tool: cargo-sbom"`. The SPDX parser strips the prefix and colon, storing only `"Acme Inc."` or `"cargo-sbom"`. The NTIA checker does not need to know about SPDX prefix conventions. If a future rule needs to distinguish between tool-supplied and organization-supplied components, this information would need to be preserved in a separate field or in `raw_extras`.

**Notes on `version` normalization:**

SPDX uses `NOASSERTION` as a sentinel for "version is explicitly unknown". CycloneDX uses an absent field for the same meaning. Both are normalized to `None` so the NTIA checker's version check (FR-06) handles them identically.

---

## 4. NormalizedRelationship Field Specification

`NormalizedRelationship` represents a single declared dependency relationship between two components. It maps to `relationships[i]` in SPDX and an entry in `dependencies[i].dependsOn[j]` in CycloneDX.

| Field | Python Type | Required | Description |
|---|---|---|---|
| `from_id` | `str` | Yes | The `component_id` of the dependent component (the component that depends on something). In SPDX terms, this is the `spdxElementId` field of the relationship. In CycloneDX terms, this is the `ref` field of the `dependencies` entry. |
| `to_id` | `str` | Yes | The `component_id` of the dependency (the component being depended upon). In SPDX terms, this is the `relatedSpdxElement` field of the relationship. In CycloneDX terms, this is one entry in the `dependsOn` array. |
| `relationship_type` | `str` | No | The type of relationship, normalized to a string. Defaults to `"DEPENDS_ON"` when the source format does not distinguish relationship types (as in CycloneDX's `dependencies` array, which always implies dependency). For SPDX, the original `relationshipType` value is preserved (e.g., `"DEPENDS_ON"`, `"DYNAMIC_LINK"`, `"STATIC_LINK"`). |

**CycloneDX relationship expansion:**

CycloneDX's `dependencies` array uses a one-to-many structure:
```json
{ "ref": "A", "dependsOn": ["B", "C"] }
```
The CycloneDX parser expands this into multiple `NormalizedRelationship` objects:
```
NormalizedRelationship(from_id="A", to_id="B", relationship_type="DEPENDS_ON")
NormalizedRelationship(from_id="A", to_id="C", relationship_type="DEPENDS_ON")
```

**SPDX relationship filtering:**

The SPDX `relationships` array contains many relationship types, not all of which represent dependencies. Only the following `relationshipType` values are included when building `NormalizedRelationship` objects, as these are the qualifying types for NTIA FR-08:

- `DEPENDS_ON`
- `DYNAMIC_LINK`
- `STATIC_LINK`
- `RUNTIME_DEPENDENCY_OF`
- `DEV_DEPENDENCY_OF`

Other SPDX relationship types (e.g., `DESCRIBES`, `GENERATED_FROM`, `CONTAINS`) are silently dropped by the parser. They are not relevant to NTIA compliance.

---

## 5. SPDX 2.3 → NormalizedSBOM Mapping

The following table defines the exact SPDX 2.3 JSON field paths and transformation rules for each `NormalizedSBOM` field.

### SPDX Top-Level → NormalizedSBOM

| NormalizedSBOM Field | SPDX 2.3 JSON Path | Transformation |
|---|---|---|
| `format` | _(none; set by parser)_ | Always `"spdx"` |
| `author` | `creationInfo.creators` | Filter entries starting with `"Tool:"` or `"Organization:"`. Join all matching entries with `", "`. If none match or the array is absent, set to `None`. |
| `timestamp` | `creationInfo.created` | Use as-is (string). `None` if absent or empty string. |
| `components` | `packages[*]` | Map each package to a `NormalizedComponent` (see table below). |
| `relationships` | `relationships[*]` | Filter to qualifying `relationshipType` values; map each to a `NormalizedRelationship` (see table below). |

### SPDX packages[i] → NormalizedComponent

| NormalizedComponent Field | SPDX packages[i] Path | Transformation |
|---|---|---|
| `component_id` | `packages[i].SPDXID` | Use as-is. |
| `name` | `packages[i].name` | Use as-is. `None` if absent or empty string. |
| `version` | `packages[i].versionInfo` | `None` if absent, empty string, or value is `"NOASSERTION"`. Otherwise use as-is. |
| `supplier` | `packages[i].supplier` | `None` if absent, empty, or value is `"NOASSERTION"`. Otherwise strip leading `"Organization: "` or `"Tool: "` prefix (prefix + one space). |
| `identifiers` | `packages[i].externalRefs[*]` | Include `locator` from entries where `referenceCategory` is `"PACKAGE-MANAGER"` (PURL) or `"SECURITY"` (CPE). Collect into a tuple. Empty tuple if no qualifying refs. |

### SPDX relationships[i] → NormalizedRelationship

| NormalizedRelationship Field | SPDX relationships[i] Path | Transformation |
|---|---|---|
| `from_id` | `relationships[i].spdxElementId` | Use as-is. |
| `to_id` | `relationships[i].relatedSpdxElement` | Use as-is. |
| `relationship_type` | `relationships[i].relationshipType` | Use as-is (already a string). Only qualifying types are included (see Section 4). |

---

## 6. CycloneDX 1.6 → NormalizedSBOM Mapping

The following table defines the exact CycloneDX 1.6 JSON field paths and transformation rules for each `NormalizedSBOM` field.

### CycloneDX Top-Level → NormalizedSBOM

| NormalizedSBOM Field | CycloneDX 1.6 JSON Path | Transformation |
|---|---|---|
| `format` | _(none; set by parser)_ | Always `"cyclonedx"` |
| `author` | `metadata.authors[*].name` and/or `metadata.manufacture.name` | If `metadata.authors` is present and non-empty, concatenate all non-empty `name` fields with `", "`. If `metadata.authors` is absent or empty, fall back to `metadata.manufacture.name`. If neither is present or non-empty, set to `None`. |
| `timestamp` | `metadata.timestamp` | Use as-is (string). `None` if absent or empty string. |
| `components` | `components[*]` | Map each component to a `NormalizedComponent` (see table below). |
| `relationships` | `dependencies[*]` | Expand each `{ "ref": X, "dependsOn": [Y, Z, ...] }` entry into one `NormalizedRelationship` per `dependsOn` entry (see Section 4). |

### CycloneDX components[i] → NormalizedComponent

| NormalizedComponent Field | CycloneDX components[i] Path | Transformation |
|---|---|---|
| `component_id` | `components[i]["bom-ref"]` | Use as-is. If `bom-ref` is absent (it is optional in CycloneDX), use `components[i].name + "@" + components[i].version` as a fallback identifier. If both are absent, generate a positional identifier `"component-{i}"`. |
| `name` | `components[i].name` | Use as-is. `None` if absent or empty string. |
| `version` | `components[i].version` | `None` if absent or empty string. CycloneDX does not use `NOASSERTION`. |
| `supplier` | `components[i].supplier.name` | `None` if `supplier` object is absent or `supplier.name` is absent or empty. Otherwise use `supplier.name` as-is (no prefix stripping needed). |
| `identifiers` | `components[i].purl` and/or `components[i].cpe` | Collect non-empty values of `purl` and `cpe` into a tuple. Empty tuple if both are absent. |

### CycloneDX dependencies[i] → NormalizedRelationship (expanded)

| NormalizedRelationship Field | CycloneDX Path | Transformation |
|---|---|---|
| `from_id` | `dependencies[i].ref` | Use as-is. |
| `to_id` | `dependencies[i].dependsOn[j]` | One `NormalizedRelationship` is created per entry in `dependsOn`. |
| `relationship_type` | _(none)_ | Always `"DEPENDS_ON"`. CycloneDX's `dependencies` array does not differentiate relationship types. |

---

## 7. Extension Points: Adding a New Format

To add support for a new SBOM format (e.g., SPDX 3.0 JSON, CycloneDX 1.7), follow these steps:

### Step 1 — Update `format_detector.py`

Add a new detection branch in `detect_format()`. Identify the unique root-level JSON key(s) that unambiguously identify the new format. Example for a hypothetical SPDX 3.0:

```python
if "spdxVersion" in document and document["spdxVersion"] == "SPDX-3.0":
    return "spdx30"
```

Update the return type annotation from `Literal["spdx", "cyclonedx"]` to `Literal["spdx", "cyclonedx", "spdx30"]`.

### Step 2 — Create a new parser module

Create `parsers/spdx30_parser.py` with a single public function:

```python
def parse_spdx30(document: dict[str, Any]) -> NormalizedSBOM: ...
```

The function must return a fully constructed `NormalizedSBOM`. It should:
- Set `format` to the new format literal (e.g., `"spdx30"`).
- Map all format-specific fields to `NormalizedSBOM`, `NormalizedComponent`, and `NormalizedRelationship` fields according to the same conventions described in Sections 5 and 6.
- Never raise exceptions for missing optional fields — use `None` or empty tuples as appropriate.

If the new format version changes how a field is structured (e.g., SPDX 3.0 introduces a different supplier representation), document the transformation in a new mapping section in this file.

### Step 3 — Register the parser in `validator.py`

Update the parser dispatch dict in the orchestrator:

```python
PARSERS: dict[str, Callable[[dict[str, Any]], NormalizedSBOM]] = {
    "spdx": parse_spdx,
    "cyclonedx": parse_cyclonedx,
    "spdx30": parse_spdx30,  # <-- add this
}
```

### Step 4 — Bundle the JSON schema

Add the new format's official JSON schema to the `schemas/` directory (e.g., `schemas/spdx-3.0.schema.json`) and update the schema lookup dict in `validators/schema_validator.py`.

### Step 5 — Add tests

- Parser tests in `tests/unit/parsers/test_spdx30_parser.py`: verify correct normalization of format-specific quirks using fixture documents.
- Integration tests in `tests/integration/`: add representative valid and invalid SBOM files in the new format to the fixtures directory and add test cases to the integration test matrix.

### What does NOT need to change

- `validators/ntia_checker.py` — the checker operates exclusively on `NormalizedSBOM` and is format-agnostic. No changes required.
- `models/result.py` — the result model is format-agnostic. No changes required.
- `output/` renderers — no changes required.

This is the key benefit of the normalized model architecture: adding a new format is a localized change confined to the detection and parser layers, with no ripple effect into the validation logic.

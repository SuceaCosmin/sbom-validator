# Agent Briefing — sbom-validator

**Start every task by reading this file.** It distills the decision-critical facts from the full spec.
Read the originals only when you need detailed rationale or full mapping tables.

---

## Architecture Decisions (5 ADRs in brief)

| ADR | Decision |
|-----|----------|
| ADR-001 | Format detected by root JSON keys: `spdxVersion=="SPDX-2.3"` → SPDX; `bomFormat=="CycloneDX" && specVersion=="1.6"` → CycloneDX. Wrong version or no match → `UnsupportedFormatError` (exit 2). |
| ADR-002 | Parsers accept a file path and return `NormalizedSBOM`. NTIA checker only receives `NormalizedSBOM` — it has no imports from the parser layer. |
| ADR-003 | Two-stage pipeline: schema validation (collect-all), then NTIA checks (collect-all, all 7 run independently). **Schema failure blocks the NTIA stage entirely.** |
| ADR-004 | Frozen dataclasses for all result types. `ValidationStatus` and `IssueSeverity` inherit from `str` for JSON serialization. |
| ADR-005 | CLI uses Click. Command: `sbom-validator validate <FILE> [--format text\|json]`. Exit codes: 0=PASS, 1=FAIL, 2=ERROR. |

---

## Module Map and Canonical Function Signatures

```python
# src/sbom_validator/format_detector.py
def detect_format(file_path: Path) -> str: ...
# Returns "spdx" or "cyclonedx". Raises UnsupportedFormatError on failure.

# src/sbom_validator/parsers/spdx_parser.py
def parse_spdx(file_path: Path) -> NormalizedSBOM: ...

# src/sbom_validator/parsers/cyclonedx_parser.py
def parse_cyclonedx(file_path: Path) -> NormalizedSBOM: ...

# src/sbom_validator/schema_validator.py
def validate_schema(raw_doc: dict[str, Any], format_name: str) -> list[ValidationIssue]: ...

# src/sbom_validator/ntia_checker.py
def check_ntia(sbom: NormalizedSBOM) -> list[ValidationIssue]: ...

# src/sbom_validator/validator.py  (orchestrator — the only module that touches the filesystem)
def validate(file_path: str | Path) -> ValidationResult: ...
# Never raises; all errors are returned as ValidationResult(status=ERROR).
```

**Before implementing any module, verify your function signatures match these exactly.**

---

## NormalizedSBOM Field Contract

All three types are `@dataclass(frozen=True)`.

**`NormalizedSBOM`**

| Field | Type | NTIA FR |
|-------|------|---------|
| `format` | `Literal["spdx", "cyclonedx"]` | — |
| `author` | `str \| None` | FR-09 |
| `timestamp` | `str \| None` | FR-10 |
| `components` | `tuple[NormalizedComponent, ...]` | — |
| `relationships` | `tuple[NormalizedRelationship, ...]` | FR-08 |

**`NormalizedComponent`**

| Field | Type | NTIA FR |
|-------|------|---------|
| `component_id` | `str` | — |
| `name` | `str \| None` | FR-05 |
| `version` | `str \| None` | FR-06 |
| `supplier` | `str \| None` | FR-04 |
| `identifiers` | `tuple[str, ...]` | FR-07 |

**`NormalizedRelationship`**: `from_id: str`, `to_id: str`, `relationship_type: str`

---

## NTIA Field Mapping (compact)

| FR | NTIA Element | SPDX 2.3 JSON field | CycloneDX 1.6 JSON field |
|----|-------------|---------------------|--------------------------|
| FR-04 | Supplier Name | `packages[*].supplier` (strip `"Organization: "`/`"Tool: "` prefix; `NOASSERTION`→`None`) | `components[*].supplier.name` |
| FR-05 | Component Name | `packages[*].name` | `components[*].name` |
| FR-06 | Component Version | `packages[*].versionInfo` (`NOASSERTION`→`None`) | `components[*].version` |
| FR-07 | Other Unique IDs | `packages[*].externalRefs` where category is `PACKAGE-MANAGER` (PURL) or `SECURITY` (CPE) | `components[*].purl` and/or `components[*].cpe` |
| FR-08 | Dependency Relationships | `relationships[*]` with `relationshipType` in: `DEPENDS_ON`, `DYNAMIC_LINK`, `STATIC_LINK`, `RUNTIME_DEPENDENCY_OF`, `DEV_DEPENDENCY_OF` | `dependencies[*].dependsOn` — at least one non-empty entry |
| FR-09 | Author of SBOM Data | `creationInfo.creators` entries starting with `"Tool:"` or `"Organization:"` | `metadata.authors[*].name` OR `metadata.manufacture.name` |
| FR-10 | Timestamp | `creationInfo.created` (ISO 8601) | `metadata.timestamp` (ISO 8601) |

---

## ⚠️ Schema-Invalid Fixture Rule

"Schema-invalid" means the document **fails JSON schema validation** but **must still contain format fingerprints** (`spdxVersion` for SPDX, `bomFormat` for CycloneDX). Fixtures missing fingerprints trigger an "unrecognized format" error — that is a different error class and a different test scenario.

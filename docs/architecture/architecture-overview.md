# Architecture Overview

## System Overview

`sbom-validator` is a layered, pipeline-oriented tool for validating SBOM (Software Bill of Materials) files against format-specific schemas (JSON Schema and XML XSD) and NTIA minimum-element requirements. The system is organized into four logical layers that execute in strict sequence:

1. **Format Detection** — identifies whether the input is SPDX 2.3 JSON, CycloneDX 1.6 JSON, or CycloneDX 1.6 XML.
2. **Schema Validation** — checks the document's structure against the official JSON schema for the detected format.
3. **Parsing** — translates the raw JSON document into a format-agnostic `NormalizedSBOM` internal model.
4. **NTIA Checking** — evaluates all seven NTIA minimum elements against the normalized model.

The CLI layer (`cli.py`) is a thin shell that accepts user input, delegates all validation logic to `validator.py`, and renders the resulting `ValidationResult` to either human-readable text or machine-readable JSON. No business logic lives in the CLI layer.

Refer to `component-diagram.drawio` for a visual overview of the component relationships.

---

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `cli.py` | CLI entry point, output rendering, exit codes (0/1/2) |
| `validator.py` | Pipeline orchestration: coordinates all four stages and converts exceptions into `ValidationResult` objects |
| `format_detector.py` | Detect SPDX/CycloneDX using JSON keys and CycloneDX XML root namespace |
| `schema_validator.py` | JSON schema conformance checking against bundled format schemas |
| `parsers/spdx_parser.py` | SPDX 2.3 JSON → `NormalizedSBOM` translation |
| `parsers/cyclonedx_parser.py` | CycloneDX 1.6 JSON/XML → `NormalizedSBOM` translation |
| `ntia_checker.py` | NTIA minimum element compliance evaluation (FR-04 through FR-10) |
| `models.py` | Shared data contracts: frozen dataclasses and enums for results and issues |
| `exceptions.py` | Domain-specific exception hierarchy (`ParseError`, `UnsupportedFormatError`) |

---

## Validation Pipeline

The orchestrator in `validator.py` implements a four-stage sequential pipeline. Stages run in order; a failure at any stage produces a `ValidationResult` immediately and stops further processing, with the exception that NTIA checks within Stage 4 are all executed independently before returning (collect-all, not fail-fast). See ADR-003 for the full rationale.

```
File on disk
    │
    ▼
[0] Format Detection (format_detector.py)
    │  ParseError / UnsupportedFormatError → ValidationResult(ERROR)
    ▼
[1] Raw JSON Read
    │  IOError / JSONDecodeError → ValidationResult(ERROR)
    ▼
[2] Schema Validation (schema_validator.py)
    │  Collect ALL schema issues
    │  Any issues found → ValidationResult(FAIL)  ◄── pipeline stops here
    ▼
[3] Parsing (parsers/spdx_parser.py or parsers/cyclonedx_parser.py)
    │  ParseError → ValidationResult(ERROR)
    ▼
[4] NTIA Checking (ntia_checker.py)
    │  Run ALL 7 checks independently; collect ALL issues
    │  Any issues found → ValidationResult(FAIL)
    │  No issues → ValidationResult(PASS)
```

**Key design decision — Stage 2 gates Stage 3 and Stage 4:** A document that fails schema validation is not reliably parseable for NTIA field extraction. Running NTIA checks on a structurally broken document would produce false positives (reporting NTIA gaps that are actually schema violations) and obscure the real problem. Schema errors must be fixed first; only a schema-valid document provides the structural guarantees that the NTIA checker depends on. (ADR-003)

**Collect-all within stages:** Within Stage 2, all schema violations are accumulated before the result is returned. Within Stage 4, all seven NTIA checks are executed unconditionally and independently before the result is returned. This gives operators a complete picture of all issues in a single invocation rather than requiring repeated fix-and-rerun cycles.

---

## Normalized Internal Model

### Why It Exists

SPDX 2.3 JSON and CycloneDX 1.6 JSON express the same conceptual NTIA information using completely different JSON structures, field names, and conventions. For example:

- A component's supplier is `packages[i].supplier` in SPDX (a string prefixed with `"Organization:"` or `"Tool:"`) versus `components[i].supplier.name` in CycloneDX (a plain string inside a nested object).
- Dependency relationships appear in a top-level `relationships` array in SPDX and a top-level `dependencies` array in CycloneDX, with different cardinality semantics.

Without a shared intermediate representation, every NTIA rule would need two parallel implementations. `NormalizedSBOM` absorbs all format-specific differences so that the NTIA checker is written once, in terms of normalized fields, and works identically for both formats. (ADR-002)

### The Contract

- **Parsers must produce `NormalizedSBOM`.** Each parser exposes a single public function (`parse_spdx` / `parse_cyclonedx`) that accepts a raw JSON dict and returns a fully constructed `NormalizedSBOM`. Parsers do not enforce NTIA requirements; they only translate field representations.
- **`ntia_checker` only consumes `NormalizedSBOM`.** The checker has no imports from the parser layer and no knowledge of SPDX or CycloneDX field paths.
- **`validator.py` wires the layers together:** detect → schema-validate → parse → check.

### Key Fields

**`NormalizedSBOM`** — top-level container

| Field | Python Type | NTIA Element | Notes |
|-------|-------------|--------------|-------|
| `format` | `Literal["spdx", "cyclonedx"]` | — | Set by the parser; matches `detect_format()` return value |
| `author` | `str \| None` | Author of SBOM Data (FR-09) | Multiple authors joined with `", "` |
| `timestamp` | `str \| None` | Timestamp (FR-10) | ISO 8601 string; parsers do not validate format |
| `components` | `tuple[NormalizedComponent, ...]` | — | Empty tuple is valid at model level |
| `relationships` | `tuple[NormalizedRelationship, ...]` | — | Empty tuple triggers FR-08 issue |

**`NormalizedComponent`** — one software component

| Field | Python Type | NTIA Element | Notes |
|-------|-------------|--------------|-------|
| `component_id` | `str` | — | SPDX `SPDXID` or CycloneDX `bom-ref`; used to correlate with relationships |
| `name` | `str \| None` | Component Name (FR-05) | `None` when absent in source |
| `version` | `str \| None` | Component Version (FR-06) | SPDX `NOASSERTION` normalized to `None` |
| `supplier` | `str \| None` | Supplier Name (FR-04) | SPDX `"Organization: "` / `"Tool: "` prefixes stripped |
| `identifiers` | `tuple[str, ...]` | *(not enforced — FR-07 removed)* | PURLs and CPEs parsed by the format parsers; empty tuple if none. Not validated against NTIA. |

**`NormalizedRelationship`** — a declared dependency edge

| Field | Python Type | Notes |
|-------|-------------|-------|
| `from_id` | `str` | `component_id` of the dependent component |
| `to_id` | `str` | `component_id` of the dependency |
| `relationship_type` | `str` | SPDX: original type preserved; CycloneDX: always `"DEPENDS_ON"` |

All three model types are frozen dataclasses (`@dataclass(frozen=True)`), making them immutable after construction. The full field specification, transformation rules, and SPDX/CycloneDX field mapping tables are in `docs/architecture/normalized-model.md`.

---

## Format Detection Strategy

Format detection is performed by inspecting the top-level keys of the parsed JSON document. File extensions are explicitly not used — files are routinely named `sbom.json`, `bom.json`, or arbitrary names in CI/CD artifact registries. (ADR-001)

The detection rules, applied in order:

1. **SPDX:** `"spdxVersion"` is present at the JSON document root → format is SPDX.
   - The value must equal `"SPDX-2.3"`; any other version string raises `UnsupportedFormatError`.
2. **CycloneDX JSON:** `"bomFormat"` is present with value `"CycloneDX"` at the JSON document root → format is CycloneDX.
3. **CycloneDX XML:** root element `bom` with namespace `http://cyclonedx.org/schema/bom/1.6` and document `version="1"` → format is CycloneDX.
   - `specVersion` must equal `"1.6"`; any other version string raises `UnsupportedFormatError`.
3. **Neither matches** → `UnsupportedFormatError` is raised. The orchestrator converts this to `ValidationResult(status=ERROR)` and the CLI exits with code `2`.

JSON parsing failures (malformed JSON, non-object root, empty file) are treated as `ERROR`-level input failures that also produce exit code `2`.

Detection is O(1) in document size — only root-level keys are inspected. Version mismatches produce specific, actionable error messages rather than confusing schema-validation failures.

---

## Result Model

The result model is defined as frozen dataclasses with `str`-enum inheritance, providing immutability and zero-dependency JSON serialization. (ADR-004)

### Type Hierarchy

**`ValidationStatus(str, Enum)`** — overall outcome of a validation run

| Value | Meaning |
|-------|---------|
| `PASS` | Document is schema-valid and satisfies all NTIA minimum elements |
| `FAIL` | Document has schema violations or NTIA compliance gaps |
| `ERROR` | Validation could not complete (unreadable file, invalid JSON, unsupported format) |

**`IssueSeverity(str, Enum)`** — severity of an individual issue

| Value | Meaning |
|-------|---------|
| `ERROR` | Must be fixed; used for all NTIA and schema violations in v0.1.0 |
| `WARNING` | Reserved for future advisory checks (recommended but not required fields) |
| `INFO` | Reserved for future informational annotations |

**`ValidationIssue`** (frozen dataclass) — a single diagnostic finding

| Field | Type | Description |
|-------|------|-------------|
| `severity` | `IssueSeverity` | How serious the issue is |
| `field_path` | `str` | JSONPath expression pointing to the violation in the **original document** (e.g., `"packages[2].supplier"`) |
| `message` | `str` | Human-readable description of the violation |
| `rule` | `str` | Functional requirement identifier (e.g., `"FR-04"`) for downstream filtering |

**`ValidationResult`** (frozen dataclass) — the complete output of one validation run

| Field | Type | Description |
|-------|------|-------------|
| `status` | `ValidationStatus` | Overall outcome |
| `file_path` | `str` | Input file path as provided to the CLI |
| `format_detected` | `str \| None` | `"spdx"`, `"cyclonedx"`, or `None` if detection failed |
| `issues` | `tuple[ValidationIssue, ...]` | All issues found; empty tuple on PASS |

### Why Frozen Dataclasses

- **Zero additional runtime dependencies** — `dataclasses` and `enum` are standard library. Pydantic was considered and rejected due to its heavyweight dependency footprint (including Rust-compiled extensions), which would increase installation friction in CI and air-gapped environments.
- **Full `mypy` strict-mode coverage** — field names, types, and mutability are statically verified.
- **Complete immutability** — `frozen=True` on the dataclass plus `tuple` (not `list`) for `issues` prevents accidental mutation as results flow through output renderers.
- **Natural JSON serialization** — `str`-enum inheritance means `ValidationStatus.PASS` serializes as `"PASS"` in `json.dumps()` without a custom encoder.

Serialization to a JSON-compatible dict is handled by a standalone `result_to_dict()` function in `output/serializer.py`, keeping the model free of output-format concerns.

---

## How to Add a New SBOM Format

Adding support for a new SBOM format (e.g., SPDX 3.0, CycloneDX 1.7) requires changes only to the detection and parser layers. The NTIA checker, result model, CLI, and exception hierarchy require no changes.

1. **Add format detection logic to `format_detector.py`.** Identify the unique root-level JSON key(s) that unambiguously fingerprint the new format and add a new detection branch in `detect_format()`. Update the return type annotation to include the new format literal.

2. **Create `parsers/<format>_parser.py`** implementing a single public function:
   ```python
   def parse_<format>(document: dict[str, Any]) -> NormalizedSBOM: ...
   ```
   Map all format-specific fields to `NormalizedSBOM`, `NormalizedComponent`, and `NormalizedRelationship`. Parsers must never raise exceptions for missing optional fields — use `None` or empty tuples as appropriate.

3. **Map format fields to `NormalizedSBOM`** according to the NTIA element mapping tables in `docs/architecture/normalized-model.md` and the field mapping conventions in `docs/requirements.md`.

4. **Register the parser in `validator.py`'s dispatch block.** Add the new format literal as a key and the new parser function as the value in the parser dispatch block.

5. **Bundle the official JSON schema** for the new format in `src/sbom_validator/schemas/`.

6. **Add a schema loading entry in `schema_validator.py`'s `_SCHEMA_FILES` dict**, mapping the new format literal to the bundled schema filename.

7. **Write fixture files** representing valid and invalid documents in the new format under `tests/fixtures/<format>/`.

8. **Write tests** following the patterns in `tests/unit/test_spdx_parser.py` (parser normalization tests) and add integration test cases using the new fixtures.

No changes are needed to: `ntia_checker.py`, `models.py`, `cli.py`, or `exceptions.py`. This is the key benefit of the normalized model architecture — adding a new format is a localized change confined to the detection and parser layers.

---

## Architecture Decision Records

| ADR | Title | Decision Summary |
|-----|-------|-----------------|
| [ADR-001](ADR-001-format-detection.md) | Format Detection Strategy | Format is detected by inspecting top-level JSON fields (`spdxVersion`, `bomFormat`), not by file extension |
| [ADR-002](ADR-002-parser-abstraction.md) | Parser Abstraction and Normalized Internal Model | `NormalizedSBOM` frozen dataclass is the single contract between format-specific parsers and the format-agnostic NTIA checker |
| [ADR-003](ADR-003-validation-pipeline.md) | Validation Pipeline Design | Two-stage pipeline; schema validation failure gates NTIA checking; all checks within each stage are collect-all (not fail-fast) |
| [ADR-004](ADR-004-result-model.md) | Validation Result Model | Frozen dataclasses with `str`-enum inheritance; zero runtime dependencies; immutable after construction |
| [ADR-005](ADR-005-cli-design.md) | CLI Design | Click (not Typer) for the CLI framework; `@click.group()` structure for future subcommands; exit codes 0 (PASS), 1 (FAIL), 2 (ERROR) |

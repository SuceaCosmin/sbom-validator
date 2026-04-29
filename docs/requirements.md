# Requirements — sbom-validator v0.1.0

**Status:** Draft  
**Date:** 2026-04-06  
**Author:** Architecture Agent

---

## 1. Introduction

`sbom-validator` is a command-line tool that validates Software Bill of Materials (SBOM) files against two independent criteria:

1. **Schema conformance** — the file must be structurally valid according to the official JSON schema for the detected format and version.
2. **NTIA minimum elements compliance** — the file must contain all seven fields required by the NTIA "Framing Software Component Transparency" guidance.

The tool is designed for integration into CI/CD pipelines. It communicates results through machine-readable exit codes and supports both human-readable text output and structured JSON output for downstream tooling.

---

## 2. Scope

### 2.1 In Scope (v0.1.0)

- Validation of **SPDX 2.3 JSON** files (schema conformance + NTIA element checks)
- Validation of **CycloneDX 1.6 JSON and XML** files (schema conformance + NTIA element checks)
- Automatic format detection from file content (no manual format flag required)
- CLI with **text** and **JSON** output modes
- Structured exit codes suitable for CI/CD gate integration
- Bundled JSON schemas (no network access at runtime)

### 2.2 Out of Scope (v0.1.0)

The following are explicitly deferred to future versions:

| Item | Rationale |
|------|-----------|
| SPDX formats: RDF, tag-value (TV), XML | Only JSON is supported in v0.1.0 |
| CycloneDX XML format | CycloneDX XML is supported only for version 1.6 |
| SPDX versions other than 2.3 | Scope control |
| CycloneDX versions other than 1.6 | Scope control |
| License compliance checking | Separate concern; requires policy input |
| Vulnerability data enrichment | Requires external data feeds |
| SBOM generation | Out of tool's domain |

---

## 3. Functional Requirements

### FR-01 — Format Auto-Detection

The tool **must** automatically determine whether an input file is SPDX 2.3 JSON, CycloneDX 1.6 JSON, or CycloneDX 1.6 XML by inspecting the file content, without requiring the user to specify the format.

- For SPDX: the presence of `"spdxVersion": "SPDX-2.3"` at the document root is the definitive indicator.
- For CycloneDX: the presence of `"bomFormat": "CycloneDX"` and `"specVersion": "1.6"` at the document root is the definitive indicator.
- For CycloneDX XML: the root `bom` element in namespace `http://cyclonedx.org/schema/bom/1.6` is the definitive indicator.
- If the file cannot be identified as either format, the tool **must** exit with code `2` and report an `ERROR`-severity issue.

### FR-02 — Schema Validation: SPDX 2.3 JSON

The tool **must** validate SPDX 2.3 JSON files against the official SPDX 2.3 JSON schema. All schema violations **must** be collected and reported. Schema failure blocks the NTIA phase (see FR-14 and Section 6).

### FR-03 — Schema Validation: CycloneDX 1.6 (JSON/XML)

The tool **must** validate CycloneDX 1.6 JSON files against the official CycloneDX 1.6 JSON schema and CycloneDX 1.6 XML files against the official CycloneDX 1.6 XML schema (XSD). All schema violations **must** be collected and reported. Schema failure blocks the NTIA phase (see FR-14 and Section 6).

### FR-04 — NTIA Element: Supplier Name

The tool **must** verify that every component in the SBOM declares a supplier name. A missing or empty supplier field on any component **must** produce an `ERROR`-severity issue identifying the specific component. See Section 5 for field mappings.

### FR-05 — NTIA Element: Component Name

The tool **must** verify that every component in the SBOM declares a non-empty component name. A missing or empty name field on any component **must** produce an `ERROR`-severity issue.

### FR-06 — NTIA Element: Component Version

The tool **must** verify that every component in the SBOM declares a version. A missing or empty version field on any component **must** produce an `ERROR`-severity issue identifying the specific component.

### FR-07 — NTIA Element: Other Unique Identifiers *(removed)*

> **Removed in v0.5.0.** The NTIA minimum elements guideline lists "Other Unique Identifiers" (PURL, CPE) as a recommended best practice, not a mandatory requirement. Enforcing this check produced false positives on otherwise-compliant SBOMs. The `identifiers` field is still parsed and stored on each component but is no longer validated.

### FR-08 — NTIA Element: Dependency Relationships

The tool **must** verify that the SBOM document declares at least one dependency relationship between components. An SBOM with no dependency relationships at all **must** produce an `ERROR`-severity issue. See Section 5 for field mappings.

### FR-09 — NTIA Element: Author of SBOM Data

The tool **must** verify that the SBOM document identifies at least one author of the SBOM data (a tool or organization responsible for producing the SBOM). Missing or empty authorship information **must** produce an `ERROR`-severity issue. See Section 5 for field mappings.

### FR-10 — NTIA Element: Timestamp

The tool **must** verify that the SBOM document contains a timestamp recording when the SBOM data was assembled. The timestamp **must** be a valid ISO 8601 date-time string. A missing, empty, or malformed timestamp **must** produce an `ERROR`-severity issue.

### FR-11 — Structured JSON Output Mode

When invoked with `--format json`, the tool **must** write a single JSON object to `stdout` conforming to the output schema defined in Section 7. The JSON output **must** be valid and parseable even when the tool exits with a non-zero code.

### FR-12 — Human-Readable Text Output Mode

When invoked with `--format text` (the default), the tool **must** write a human-readable summary to `stdout`. The summary **must** include:

- The detected format and version
- Overall pass/fail status
- A list of all issues, each showing severity, the affected field path, and a description

### FR-13 — Exit Codes

The tool **must** exit with one of the following codes:

| Code | Meaning |
|------|---------|
| `0` | Validation passed — schema valid and all NTIA elements present |
| `1` | Validation failed — one or more schema or NTIA issues found |
| `2` | Tool or input error — file not found, unparseable JSON, unrecognized format, or internal error |

### FR-14 — Full Issue Collection (Non-Fail-Fast)

The tool **must** collect and report **all** validation issues in a single run rather than stopping at the first failure, with one exception:

- If **schema validation fails** (FR-02 or FR-03), the tool **must not** proceed to NTIA element checking (FR-04 through FR-10). A schema-invalid document cannot be reliably parsed for NTIA fields, making NTIA results unreliable. The tool reports schema issues and exits.
- If schema validation passes, **all** NTIA issues **must** be collected before the tool exits.

### FR-15 — Format Support: SPDX 3.x JSON-LD

The tool **must** detect, schema-validate, parse, and NTIA-check SBOM files serialized in
SPDX 3.x JSON-LD format. Detection is based on the presence of a `"@context"` key at the
document root with the value `"https://spdx.org/rdf/3.0.1/spdx-context.jsonld"`. The
detected format string is `"spdx3-jsonld"`.

- Schema validation **must** use `jsonschema.Draft202012Validator` against the bundled
  `spdx-3.0.1.schema.json` schema file. The existing `Draft7Validator` path **must not** be
  used for SPDX 3.x documents.
- The parser **must** implement a two-pass `@graph` traversal: index all elements by
  `spdxId` in Pass 1; resolve cross-references (e.g., `suppliedBy`, `createdBy`) in Pass 2.
- A broken `spdxId` cross-reference (reference target absent from `@graph`) **must** be
  treated as `None` for the affected `NormalizedSBOM` field, not as an error at the parser
  layer. The NTIA checker will surface a compliance failure if a mandatory NTIA field is
  `None`.
- When multiple `SpdxDocument`-typed elements are present in `@graph`, the tool **must**
  use the first and emit a WARNING-severity log entry.
- The tool **must not** make any network request to the SPDX context URL or any external
  schema source (see NFR-04).

See ADR-010 for the full design rationale, interface contracts, and NTIA field mapping.

---

## 4. Non-Functional Requirements

### NFR-01 — Python Version Support

The tool **must** support Python 3.11 and Python 3.12. Compatibility with earlier versions is not required.

### NFR-02 — Test Coverage

The automated test suite **must** achieve a line coverage of **90% or higher**, measured by `pytest-cov`. The CI pipeline **must** enforce this threshold and fail if coverage drops below it.

### NFR-03 — Performance

Validation of an SBOM containing up to **100 components** (schema + NTIA phases combined) **must** complete in under **5 seconds** on a standard developer workstation. This excludes any one-time startup overhead unrelated to validation logic.

### NFR-04 — No Network Access at Validation Time

All JSON schemas required for validation **must** be bundled with the package. The tool **must not** make any network requests during a validation run. This ensures the tool is usable in air-gapped environments and does not introduce a network dependency in CI pipelines.

### NFR-05 — Type Annotations and Static Analysis

All public API functions, methods, and class definitions **must** carry complete Python type annotations. The codebase **must** pass `mypy` in strict mode with no errors. Type correctness is enforced in CI.

---

## 5. NTIA Element Mapping Table

The table below defines the precise JSON field paths used to satisfy each NTIA minimum element for each supported format. Field paths use JSONPath dot-bracket notation. `[*]` denotes iteration over all array elements.

| NTIA Element | SPDX 2.3 JSON Field | CycloneDX 1.6 JSON Field | Notes |
|---|---|---|---|
| **Supplier Name** | `packages[*].supplier` | `components[*].supplier.name` | SPDX value must match the pattern `"Organization: <name>"` or `"Tool: <name>"`. A `NOASSERTION` value is treated as absent. |
| **Component Name** | `packages[*].name` | `components[*].name` | Must be a non-empty string. |
| **Component Version** | `packages[*].versionInfo` | `components[*].version` | Must be a non-empty string. `NOASSERTION` is treated as absent. |
| **Other Unique Identifiers** *(not enforced)* | `packages[*].externalRefs` (`PACKAGE-MANAGER` / `SECURITY`) | `components[*].purl` or `components[*].cpe` | Parsed and stored but not validated — see FR-07. |
| **Dependency Relationships** | `relationships` array — at least one entry with `relationshipType` of `DEPENDS_ON`, `DYNAMIC_LINK`, `STATIC_LINK`, `RUNTIME_DEPENDENCY_OF`, or `DEV_DEPENDENCY_OF` | `dependencies` array — at least one entry where the `dependsOn` array is non-empty | This is a document-level check. At least one relationship must exist in the entire document. |
| **Author of SBOM Data** | `creationInfo.creators` — at least one entry starting with `"Tool:"` or `"Organization:"` | `metadata.authors` (at least one entry with a non-empty `name`) OR `metadata.manufacture` (non-empty `name`) | Either field satisfies the requirement for CycloneDX. |
| **Timestamp** | `creationInfo.created` | `metadata.timestamp` | Must be a valid ISO 8601 date-time string (e.g., `"2024-01-15T10:30:00Z"`). |

---

## 6. Validation Pipeline Behavior

The validator executes a two-stage pipeline for every input file.

### Stage 1 — Schema Validation

The file is validated against the bundled JSON schema for its detected format and version (FR-02 or FR-03). All schema violations are collected.

**If Stage 1 fails:** The tool immediately reports all schema issues, sets status to `FAIL`, and exits. Stage 2 is not executed.

**Rationale:** A document that does not conform to its format's schema may be missing required structural elements (e.g., `packages`, `components`, `creationInfo`). Attempting to evaluate NTIA fields against such a document would produce unreliable results — fields may appear absent due to structural corruption rather than genuine non-compliance. Blocking Stage 2 prevents false positives and misleading output.

### Stage 2 — NTIA Element Checking

Each of the six actively enforced NTIA elements is checked independently (FR-04 through FR-10, excluding FR-07 — see FR-07 for rationale). All failures are collected before the tool exits — there is no fail-fast behavior within Stage 2. This ensures the user receives a complete picture of compliance gaps in a single run.

**If Stage 2 produces no issues:** status is `PASS`, exit code is `0`.  
**If Stage 2 produces any issues:** status is `FAIL`, exit code is `1`.

### Pipeline Diagram

```
Input File
    │
    ▼
[Format Detection]──── unrecognized ──► exit 2 (ERROR)
    │
    ▼
[Stage 1: Schema Validation]
    │
    ├── FAIL ──► report schema issues ──► exit 1 (FAIL)
    │
    └── PASS
         │
         ▼
    [Stage 2: NTIA Element Checks]
    FR-04 │ FR-05 │ FR-06 │ FR-08 │ FR-09 │ FR-10
         │
         ├── issues found ──► report all issues ──► exit 1 (FAIL)
         │
         └── no issues ──► exit 0 (PASS)
```

---

## 7. CLI Interface Specification

### 7.1 Command Structure

```
sbom-validator validate <FILE> [--format text|json]
sbom-validator --version
sbom-validator --help
```

| Argument / Option | Description |
|---|---|
| `validate <FILE>` | Validate the SBOM file at the given path |
| `--format text` | Human-readable text output (default) |
| `--format json` | Structured JSON output written to `stdout` |
| `--version` | Print the tool version and exit |
| `--help` | Print usage information and exit |

### 7.2 Exit Codes

| Exit Code | Constant | Description |
|---|---|---|
| `0` | `PASS` | File passed both schema validation and all NTIA element checks |
| `1` | `FAIL` | One or more schema violations or NTIA element failures were found |
| `2` | `ERROR` | The tool encountered an input or runtime error (file not found, invalid JSON, unrecognized format, internal exception) |

### 7.3 JSON Output Schema

When `--format json` is used, the tool writes the following JSON object to `stdout`:

```json
{
  "tool_version": "0.4.0",
  "status": "PASS|FAIL|ERROR",
  "file": "<path>",
  "format_detected": "spdx|cyclonedx|null",
  "issues": [
    {
      "severity": "ERROR|WARNING|INFO",
      "field_path": "<json.path.expression>",
      "message": "<human readable description of the issue>",
      "rule": "<FR-XX>"
    }
  ]
}
```

**Field definitions:**

| Field | Type | Description |
|---|---|---|
| `tool_version` | `string` | Version of sbom-validator that produced this output (e.g., `"0.4.0"`) |
| `status` | `string` | Overall result: `"PASS"`, `"FAIL"`, or `"ERROR"` |
| `file` | `string` | The file path as provided to the CLI |
| `format_detected` | `string \| null` | `"spdx"`, `"cyclonedx"`, or `null` if detection failed |
| `issues` | `array` | List of all issues found; empty array on `PASS` |
| `issues[].severity` | `string` | `"ERROR"` for blocking failures, `"WARNING"` for advisory, `"INFO"` for informational |
| `issues[].category` | `string` | Issue classification: `"FORMAT"` (detection errors), `"SCHEMA"` (schema violations), or `"NTIA"` (NTIA element failures) |
| `issues[].field_path` | `string` | JSONPath expression identifying the field or location involved |
| `issues[].message` | `string` | Human-readable description of the issue |
| `issues[].rule` | `string` | The functional requirement identifier that this issue corresponds to (e.g., `"FR-04"`) |

**Example — NTIA failure:**

```json
{
  "tool_version": "0.4.0",
  "status": "FAIL",
  "file": "my-app.spdx.json",
  "format_detected": "spdx",
  "issues": [
    {
      "severity": "ERROR",
      "category": "NTIA",
      "field_path": "packages[2].supplier",
      "message": "Component 'libfoo' is missing a supplier name.",
      "rule": "FR-04"
    }
  ]
}
```

**Example — clean pass:**

```json
{
  "tool_version": "0.4.0",
  "status": "PASS",
  "file": "my-app.spdx.json",
  "format_detected": "spdx",
  "issues": []
}
```

---

*End of requirements document.*

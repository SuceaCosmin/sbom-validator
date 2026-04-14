# ADR-009: SPDX Multi-Format Support (Tag-Value and YAML)

## Status

Accepted

## Context

`sbom-validator` already validates SPDX 2.3 JSON (ADR-001). The SPDX specification defines three additional textual serialization formats: Tag-Value (`.spdx`), YAML (`.spdx.yaml`), and RDF. Users increasingly produce SBOMs in Tag-Value format via tools like `syft` or `spdx-sbom-generator`, and YAML is gaining adoption as a human-readable alternative to JSON.

This ADR covers the addition of SPDX Tag-Value and SPDX YAML support, addressing:

1. Format detection extension strategy
2. Sub-format constant design
3. Schema validation policy for each new format
4. Parser factoring (shared core logic vs. per-format wrappers)
5. YAML library selection

The following design questions arose:

**Q1 — Sub-format constants or unified "spdx"?**
The existing `FORMAT_SPDX = "spdx"` constant is returned by `detect_format()` and threaded through the pipeline as `format_detected` in `ValidationResult`. Callers (CI/CD consumers of `--format json` output) rely on this field to know what was parsed. Returning the coarse `"spdx"` for all three serializations would lose information. Sub-format strings (`"spdx-yaml"`, `"spdx-tv"`) provide richer signals without breaking consumers that already handle `"spdx"` — they simply see a new possible value, which is additive.

**Q2 — Schema validation for YAML**
SPDX YAML is structurally identical to SPDX JSON (same field names, same nesting). The bundled `spdx-2.3.schema.json` can validate a YAML document after it is loaded into a Python dict. No new schema file is needed.

**Q3 — Schema validation for Tag-Value**
SPDX Tag-Value has no official JSON schema or XSD. Schema validation must be explicitly skipped for this format. A silent skip would be a process violation — the skip must be logged at INFO level and reflected in the pipeline flow.

**Q4 — Shared parsing core**
The SPDX JSON parser (`spdx_parser.py`) contains well-tested helper functions (`_parse_author`, `_parse_component`, `_parse_relationship`) that operate on dict objects. YAML loads to the same dict structure, so the YAML parser can be a thin wrapper that loads YAML and delegates to a shared `_parse_spdx_document(document: dict)` helper. The Tag-Value parser is independent (line-by-line text parsing), but reuses the same `NormalizedComponent` / `NormalizedRelationship` constructors.

**Q5 — YAML library choice**
PyYAML (`pyyaml`) is the de-facto standard for Python YAML parsing. It is well-maintained, has no C-extension requirement for pure-Python usage, and is widely used in the Python ecosystem. The `ruamel.yaml` alternative offers round-trip preservation but is unnecessary here. PyYAML `yaml.safe_load` is used exclusively — `yaml.load` without an explicit Loader is deprecated and unsafe.

## Decision

### 1. Sub-format constants

Two new constants are added to `src/sbom_validator/constants.py`:

```python
FORMAT_SPDX_TV   = "spdx-tv"
FORMAT_SPDX_YAML = "spdx-yaml"
```

`FORMAT_SPDX = "spdx"` is retained unchanged for SPDX JSON (backward-compatible).

### 2. Format detection order

`detect_format()` in `format_detector.py` is extended with the following priority order:

1. Try JSON parse → if JSON object with `spdxVersion == "SPDX-2.3"` → return `"spdx"` (unchanged)
2. Try JSON parse → if JSON object with `bomFormat == "CycloneDX"` → return `"cyclonedx"` (unchanged)
3. If JSON parse fails → try CycloneDX XML detection (unchanged)
4. If JSON parse fails AND not CycloneDX XML → check if content starts with `SPDXVersion:` → return `"spdx-tv"`
5. If JSON parse fails → try `yaml.safe_load` → if result is a dict with `spdxVersion == "SPDX-2.3"` → return `"spdx-yaml"`
6. Otherwise → raise `UnsupportedFormatError`

The YAML detection check deliberately comes after Tag-Value because a Tag-Value file starting with `SPDXVersion:` is also technically valid YAML (YAML is a superset of many plain-text formats). The content-match `startswith("SPDXVersion:")` is unambiguous for Tag-Value and fast.

### 3. Schema validation policy

| Format | Schema Validation |
|--------|------------------|
| `"spdx"` (JSON) | Validated against bundled `spdx-2.3.schema.json` (unchanged) |
| `"spdx-yaml"` | YAML loaded to dict; validated against bundled `spdx-2.3.schema.json` |
| `"spdx-tv"` | Schema validation explicitly skipped; INFO log entry emitted: `"Schema validation skipped for spdx-tv: no formal schema available"` |

`validate_schema()` in `schema_validator.py` is extended to accept `"spdx-yaml"` and `"spdx-tv"` format names. The existing `ValueError` guard for unknown format names is updated to include the new constants.

### 4. Parser factoring

`spdx_parser.py` is refactored to expose a shared helper:

```python
def _parse_spdx_document(document: dict[str, Any], source_label: str) -> NormalizedSBOM: ...
```

The existing `parse_spdx(file_path)` function becomes a thin wrapper that reads JSON and calls `_parse_spdx_document`. Two new parser modules are introduced:

- `src/sbom_validator/parsers/spdx_yaml_parser.py` — loads YAML, calls `_parse_spdx_document`
- `src/sbom_validator/parsers/spdx_tv_parser.py` — parses Tag-Value lines, builds NormalizedSBOM directly

The Tag-Value parser processes these line patterns:

| TV Field | Mapping |
|----------|---------|
| `SPDXVersion:` | Version check (must be `SPDX-2.3`) |
| `Created:` | `NormalizedSBOM.timestamp` |
| `Creator: Tool: <name>` | Contributes to `NormalizedSBOM.author` |
| `Creator: Organization: <name>` | Contributes to `NormalizedSBOM.author` |
| `PackageName:` | `NormalizedComponent.name` |
| `SPDXID:` | `NormalizedComponent.component_id` |
| `PackageVersion:` | `NormalizedComponent.version` |
| `PackageSupplier:` | `NormalizedComponent.supplier` (strip `Organization: ` / `Tool: ` prefix; `NOASSERTION` → None) |
| `ExternalRef: PACKAGE-MANAGER purl <locator>` | Appended to `NormalizedComponent.identifiers` |
| `ExternalRef: SECURITY cpe23Type <locator>` | Appended to `NormalizedComponent.identifiers` |
| `Relationship: <from> <type> <to>` | `NormalizedRelationship` (qualifying types only) |

Multi-line continuation values (lines starting with whitespace after a TV field) are ignored — only single-line fields relevant to NTIA compliance are parsed.

### 5. Validator pipeline extension

`validator.py` is extended to:
- Import the two new parser functions and the two new constants
- In Stage 1 (raw doc loading), handle `"spdx-tv"` (read as text), `"spdx-yaml"` (load YAML dict)
- In Stage 2 (schema validation), pass the new format names; TV skips schema validation
- In Stage 3 (parsing), dispatch `parse_spdx_tv` and `parse_spdx_yaml` for the respective formats

### 6. Dependency

`pyyaml = ">=6.0"` is added to `[tool.poetry.dependencies]` in `pyproject.toml`.

### Interface Contracts (Python stubs)

```python
# src/sbom_validator/constants.py
FORMAT_SPDX    = "spdx"       # SPDX 2.3 JSON (unchanged)
FORMAT_SPDX_TV = "spdx-tv"    # SPDX 2.3 Tag-Value
FORMAT_SPDX_YAML = "spdx-yaml"  # SPDX 2.3 YAML

# src/sbom_validator/format_detector.py
def detect_format(file_path: Path) -> str:
    # Returns "spdx", "spdx-tv", "spdx-yaml", or "cyclonedx"
    # Raises UnsupportedFormatError on unrecognized format
    ...

# src/sbom_validator/schema_validator.py
def validate_schema(
    raw_doc: dict[str, Any] | str,
    format_name: str,
    cdx_version: str | None = None,
) -> list[ValidationIssue]:
    # format_name now also accepts "spdx-tv" (skip) and "spdx-yaml" (validate as JSON schema)
    ...

# src/sbom_validator/parsers/spdx_parser.py
def _parse_spdx_document(document: dict[str, Any], source_label: str) -> NormalizedSBOM: ...
def parse_spdx(file_path: Path) -> NormalizedSBOM: ...  # unchanged signature

# src/sbom_validator/parsers/spdx_yaml_parser.py
def parse_spdx_yaml(file_path: Path) -> NormalizedSBOM: ...

# src/sbom_validator/parsers/spdx_tv_parser.py
def parse_spdx_tv(file_path: Path) -> NormalizedSBOM: ...
```

## Consequences

**Positive:**
- Full NTIA compliance checking for Tag-Value and YAML SBOMs without structural changes to the NTIA checker (it receives `NormalizedSBOM` regardless of source format)
- Zero new schema files required — YAML reuses the existing JSON schema
- Explicit, logged schema-skip for Tag-Value provides auditability
- Backward-compatible: all existing `"spdx"` consumers continue working; new sub-format values are additive
- `format_detected` now surfaces the precise serialization format, enabling downstream tools to distinguish SPDX variants

**Negative:**
- Tag-Value parser is a custom line parser, not using the `spdx-tools` library. This is intentional: `spdx-tools` is a large dependency excluded from the binary (ADR-008), and the subset of TV fields needed for NTIA compliance is small and well-defined.
- YAML detection requires a `yaml.safe_load` call in the format detector for files that are not JSON and not XML. This is acceptable (safe, fast, and only triggered when JSON/XML detection fails).
- Tag-Value multi-line continuation values are not parsed. This is not a compliance gap for NTIA since all seven NTIA elements map to single-line TV fields.

## ADR Update to agent-briefing.md

The following entries in `docs/agent-briefing.md` must be updated after this ADR is implemented:
- ADR table: add ADR-009 row
- Module Map: update `detect_format` return type note; add `parse_spdx_yaml` and `parse_spdx_tv` signatures
- `format_detected` field description: update to include `"spdx-tv"` and `"spdx-yaml"`

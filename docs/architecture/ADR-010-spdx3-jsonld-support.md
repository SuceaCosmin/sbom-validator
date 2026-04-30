# ADR-010: SPDX 3.x JSON-LD Format Support

## Status

Accepted — **Amended** (see Amendment 1 below)

## Context

`sbom-validator` already validates SPDX 2.3 (JSON, YAML, Tag-Value) and CycloneDX 1.3–1.6
(JSON, XML). The SPDX project released SPDX 3.0 in April 2024, with SPDX 3.0.1 being the
first patch. SPDX 3.x uses JSON-LD as its canonical serialization format, replacing the flat
JSON structure of SPDX 2.3 with an RDF-based graph encoded as a JSON-LD `@graph` array.

This structural change is significant enough that the existing SPDX 2.3 parser cannot be
reused without adaptation. The following design questions arose and are resolved here:

**Q1 — Format fingerprint for detection**
SPDX 3.x JSON-LD documents include a `@context` key at the document root pointing to the
SPDX 3.x JSON-LD context URL (`"https://spdx.org/rdf/3.0.1/spdx-context.jsonld"`), and a
`@graph` array containing typed element objects. No other format uses a `@context` field
at the root, making this an unambiguous fingerprint. The `@type` or `spdxId` fields inside
`@graph` cannot serve as root-level fingerprints; `@context` at the root is the reliable
indicator.

**Q2 — JSON Schema validator version**
The SPDX 3.0.1 official JSON Schema (`spdx-3.0.1.schema.json`, already bundled) is written
against JSON Schema Draft 2020-12. The existing `validate_schema()` function uses
`jsonschema.Draft7Validator`. Draft 2020-12 requires `jsonschema.Draft202012Validator`.
Using the wrong validator silently skips keywords like `unevaluatedProperties`, producing
false passes. A new internal helper `_validate_json_schema_2020()` is required in
`schema_validator.py`.

**Q3 — Graph traversal and cross-reference resolution**
SPDX 3.x places all elements (document metadata, packages, snippets, files, relationships)
as sibling objects in the `@graph` array, each identified by an `spdxId` URI. Parsers must
perform a two-pass approach:

- Pass 1: index all elements by `spdxId` (build a `dict[str, dict]`).
- Pass 2: resolve cross-references when extracting fields. For example,
  `Package.suppliedBy` is a list of `spdxId` URI references pointing to `Organization`
  or `Tool` elements elsewhere in the graph. The parser follows these references to read
  the `name` field of the target element.

A missing cross-reference (broken `spdxId`) must not raise an exception — it is treated as
`None` for the field that depended on it, consistent with the "never raise for missing
optional fields" convention established in ADR-002.

**Q4 — Multiple SpdxDocument elements in `@graph`**
The SPDX 3.x specification allows a `@graph` to be a bundle containing elements from
multiple SPDX documents. In practice, single-document SBOMs are the common case. When
multiple `SpdxDocument`-typed elements are present, the parser takes the first one and logs
a WARNING: `"Multiple SpdxDocument elements found in @graph; using the first."` This is
consistent with the fail-gracefully policy established in ADR-002.

**Q5 — `SpdxDocument` type URI**
The JSON-LD type identifier for the document metadata element is `"SpdxDocument"` (short
form, resolved via `@context`). In the absence of a running JSON-LD processor, the parser
must treat both short-form (`"SpdxDocument"`) and fully-qualified
(`"https://spdx.org/rdf/3.0.1/terms/Core/SpdxDocument"`) values as equivalent. The short
form is used in all known tool outputs.

**Q6 — NTIA field mapping for SPDX 3.x**
SPDX 3.x restructures many fields relative to 2.3:

| NTIA Element | SPDX 2.3 JSON | SPDX 3.x JSON-LD |
|---|---|---|
| Author of SBOM Data | `creationInfo.creators` (string prefix) | `SpdxDocument.creationInfo.createdBy` → list of `spdxId` refs → resolved `name` |
| Timestamp | `creationInfo.created` | `SpdxDocument.creationInfo.created` |
| Supplier Name | `packages[*].supplier` (string prefix) | `Package.suppliedBy` → list of `spdxId` refs → resolved `name` |
| Component Name | `packages[*].name` | `Package.name` |
| Component Version | `packages[*].versionInfo` | `Package.packageVersion` |
| Dependency Relationships | `relationships[*]` (type filter) | `Relationship` elements in `@graph` with `relationshipType == "DEPENDS_ON"` |
| Component ID | `packages[*].SPDXID` | `Package.spdxId` |

The SPDX 3.x `Relationship.from` / `Relationship.to` fields are `spdxId` URI references.
These are stored as-is in `NormalizedRelationship.from_id` / `to_id`.

**Q7 — New format constant and `detect_format()` return value**
A new constant `FORMAT_SPDX3_JSONLD = "spdx3-jsonld"` is added to `constants.py`. The
`detect_format()` function already returns `str`; no signature change is needed. The new
constant is additive and backward-compatible with all existing consumers.

## Decision

### 1. Format constant

A new constant is added to `src/sbom_validator/constants.py`:

```python
FORMAT_SPDX3_JSONLD = "spdx3-jsonld"
SPDX3_CONTEXT_URL   = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
SPDX3_SCHEMA_FILE   = "spdx-3.0.1.schema.json"
RULE_SPDX3_SCHEMA   = "FR-15"
```

### 2. Format detection

`detect_format()` in `format_detector.py` is extended. The new branch is inserted
**before** the existing SPDX 2.3 JSON branch because both SPDX 2.3 JSON and SPDX 3.x
JSON-LD are valid JSON; the SPDX 3.x branch's `@context` check is unambiguous and does
not overlap with `spdxVersion` in 2.3 documents.

Detection priority order (full, with new branch):

1. Try JSON parse. If root object contains `"@context"` with value equal to
   `SPDX3_CONTEXT_URL` → return `"spdx3-jsonld"`. If `"@context"` is present but contains
   a different URL, raise `UnsupportedFormatError`.
2. If root object contains `"spdxVersion" == "SPDX-2.3"` → return `"spdx"`.
3. If root object contains `"bomFormat" == "CycloneDX"` and `"specVersion"` in
   supported versions → return `"cyclonedx"`.
4. If JSON parse fails → try CycloneDX XML namespace detection → return `"cyclonedx"`.
5. If JSON parse fails AND not CycloneDX XML → `startswith("SPDXVersion: ")` → return
   `"spdx-tv"`.
6. If JSON parse fails → `yaml.safe_load` with `spdxVersion == "SPDX-2.3"` → return
   `"spdx-yaml"`.
7. Otherwise → raise `UnsupportedFormatError`.

The `@context` check uses an equality comparison against `SPDX3_CONTEXT_URL`. If
`@context` is present but contains a different URL (e.g., a draft or future version),
`UnsupportedFormatError` is raised with a message identifying the unrecognized context URL.

### 3. Schema validation

`validate_schema()` is extended to dispatch on `"spdx3-jsonld"`. A new private helper
is introduced:

```python
def _validate_json_schema_2020(
    document: dict[str, Any],
    schema: dict[str, Any],
    rule: str,
) -> list[ValidationIssue]: ...
```

This helper instantiates `jsonschema.Draft202012Validator` (not `Draft7Validator`) and
collects all validation errors via `iter_errors`. The format name `"spdx3-jsonld"` is
handled as a new branch in the existing `if/elif` dispatch inside `validate_schema()`.

The bundled schema file `src/sbom_validator/schemas/spdx-3.0.1.schema.json` is already
present in the repository. No additional schema download is required.

### 4. New parser module

A new parser module `src/sbom_validator/parsers/spdx3_jsonld_parser.py` is created
with a single public function:

```python
def parse_spdx3_jsonld(file_path: Path) -> NormalizedSBOM: ...
```

The parser implements the two-pass graph traversal described in Q3:

- **Pass 1:** Load the JSON file and build `index: dict[str, dict[str, Any]]` keyed by
  `spdxId`.
- **Pass 2:** Locate the `SpdxDocument` element (type `"SpdxDocument"` or its
  fully-qualified equivalent). Extract `creationInfo.created` (timestamp) and
  `creationInfo.createdBy` (list of `spdxId` refs → resolved `name` fields → joined as
  `", "`). Collect all `Package` elements; for each, resolve `suppliedBy` refs and extract
  `name`, `packageVersion`, `spdxId`. Collect all `Relationship` elements with
  `relationshipType == "DEPENDS_ON"`; extract `from` and `to` `spdxId` refs.

Missing cross-references produce `None` for the affected field, never an exception.

### 5. Pipeline wiring (`validator.py`)

`validator.py` is extended to:

- Import `FORMAT_SPDX3_JSONLD` from `constants`.
- Import `parse_spdx3_jsonld` from `parsers.spdx3_jsonld_parser`.
- Add `"spdx3-jsonld"` to the set of formats that are loaded as JSON (alongside `"spdx"`,
  `"spdx-yaml"`, and `"cyclonedx"` JSON path).
- Dispatch `parse_spdx3_jsonld` for `format_name == FORMAT_SPDX3_JSONLD`.
- Pass `FORMAT_SPDX3_JSONLD` to `validate_schema()`.

### Interface Contract (Python stubs)

```python
# src/sbom_validator/constants.py
FORMAT_SPDX3_JSONLD: str = "spdx3-jsonld"
SPDX3_CONTEXT_URL: str = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
SPDX3_SCHEMA_FILE: str = "spdx-3.0.1.schema.json"
RULE_SPDX3_SCHEMA: str = "FR-15"

# src/sbom_validator/format_detector.py
def detect_format(file_path: Path) -> str:
    # Returns one of: "spdx3-jsonld", "spdx", "spdx-tv", "spdx-yaml", "cyclonedx"
    # Raises UnsupportedFormatError on unrecognized format
    ...

# src/sbom_validator/schema_validator.py
def validate_schema(
    raw_doc: dict[str, Any] | str,
    format_name: str,
    cdx_version: str | None = None,
) -> list[ValidationIssue]:
    # format_name now also accepts "spdx3-jsonld" (uses Draft202012Validator)
    ...

def _validate_json_schema_2020(
    document: dict[str, Any],
    schema: dict[str, Any],
    rule: str,
) -> list[ValidationIssue]:
    # Private. Instantiates Draft202012Validator; collects all errors via iter_errors.
    ...

# src/sbom_validator/parsers/spdx3_jsonld_parser.py
def parse_spdx3_jsonld(file_path: Path) -> NormalizedSBOM:
    # Two-pass graph traversal.
    # Missing cross-references produce None, never raise.
    # Multiple SpdxDocument elements: take first, log WARNING.
    ...
```

## Consequences

**Positive:**

- NTIA checker requires zero changes — it receives `NormalizedSBOM` regardless of source
  format, consistent with the design intent of ADR-002.
- The bundled schema is already present; no runtime network call is needed (NFR-04).
- The format constant `"spdx3-jsonld"` is additive — all existing consumers that switch on
  format strings continue to work; they will never see the new value unless they consume
  SPDX 3.x files.
- Two-pass graph indexing is O(n) in element count, well within the 5-second budget for
  100-component SBOMs (NFR-03).

**Negative:**

- The parser does not use a full JSON-LD processor (e.g., `pyld`). Compact IRI resolution
  via `@context` is not performed; type matching uses the known short-form strings. If a
  future SPDX 3.x version changes context URL or type names, the parser must be updated.
  This is an accepted trade-off — `pyld` is a large dependency with no other use in the
  project.
- Only JSON-LD serialization of SPDX 3.x is supported. SPDX 3.x Tag-Value, YAML, and XML
  serializations are deferred (see Deferral D1 in `docs/releases/TASKS-v0.6.0.md`).
- Broken `spdxId` cross-references silently produce `None` rather than an explicit schema
  error. This is consistent with the "never raise for optional fields" policy but means a
  document with a dangling `suppliedBy` reference produces an NTIA FR-04 failure rather
  than a schema failure. This is acceptable: the schema validator catches structural
  conformance; the NTIA checker catches compliance gaps.

---

## Amendment 1 — Envelope-only Schema Validation (approved 2026-04-30)

### Finding

The original decision in section 3 states that `validate_schema()` loads and validates
against the full bundled `spdx-3.0.1.schema.json`. During implementation it was discovered
that this schema is incompatible with top-level JSON-LD envelope documents.

The bundled schema has the following structure at the root:

```json
{
  "if":   { "required": ["@graph"] },
  "then": { "properties": { "@graph": { ... } } },
  "else": { "$ref": "#/$defs/AnyClass" }
}
```

The `else` branch requires the root document to be a concrete typed SPDX element when
`@graph` is absent. Since SPDX 3.x JSON-LD files always carry `@graph`, the schema rejects
validation of the document envelope itself (`{"@context": "...", "@graph": [...]}`) because
the root object is not an `AnyClass` element. Feeding the document through `iter_errors()`
on the full schema produces spurious errors for every valid SPDX 3.x document.

### Decision

The schema-validation stage for `spdx3-jsonld` validates only the document **envelope**:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["@context"],
  "properties": {
    "@context": { "const": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld" }
  }
}
```

This schema is synthesised in-memory by `_load_spdx3_schema()` and never written to disk.
The full `spdx-3.0.1.schema.json` remains bundled (and is available for future use) but is
not loaded at runtime in this release.

Element-level validation is delegated to the two-pass parser, which raises `ParseError` for
structural problems (missing `SpdxDocument`, empty `@graph`, non-list `@graph`) and returns
`None` for broken cross-references — surfacing them as NTIA failures at Stage 4.

### Consequences

- Schema-stage errors for malformed `@graph` elements surface as `ERROR` (parse stage) rather
  than `FAIL+FR-15` (schema stage). This is a user-visible behavioural deviation.
- The `SPDX3_SCHEMA_FILE` constant in `constants.py` is retained for completeness and for use
  by a future full-schema implementation; the dead `_SPDX3_SCHEMA_FILE` module-level constant
  in `schema_validator.py` has been removed (G4 M-02).
- `jsonschema.Draft202012Validator` is instantiated with `registry=Registry()` (from the
  `referencing` package) to prevent automatic remote-reference fetching. The envelope schema
  has no `$ref` entries, so the registry is a no-op for current use; it is defensive against
  future schema additions that might introduce `$ref` URIs.

### Risk acceptance

| Risk | Mitigation | Planned resolution |
|------|------------|-------------------|
| Invalid `@graph` elements produce ERROR not FAIL+FR-15 | Parser raises `ParseError` on empty/non-list `@graph`; NTIA checker surfaces missing elements | Future release: feed each `@graph` element to a subset of the full schema, or patch the full schema's `else` branch to accept the envelope form |

Recorded as Deferral D2 in `docs/releases/TASKS-v0.6.0.md`.

---

## Requirements Traceability

| Requirement | Satisfied by |
|-------------|--------------|
| FR-15 (SPDX 3.x format detection and validation) | New `@context` branch in `detect_format()`; new `_validate_json_schema_2020()` helper |
| FR-02 (schema validation) | Extended `validate_schema()` dispatching to `Draft202012Validator` for `spdx3-jsonld` |
| FR-04 to FR-10 (NTIA elements) | `parse_spdx3_jsonld()` maps SPDX 3.x fields to `NormalizedSBOM`; `check_ntia()` unchanged |
| NFR-04 (no network calls) | Schema bundled at `src/sbom_validator/schemas/spdx-3.0.1.schema.json` |
| NFR-03 (performance) | Two-pass O(n) traversal; no external process or network I/O |

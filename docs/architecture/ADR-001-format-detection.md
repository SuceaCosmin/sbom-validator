# ADR-001: Format Detection Strategy

## Status

Accepted

## Context

`sbom-validator` supports SPDX 2.3 JSON and CycloneDX 1.6 in both JSON and XML representations, and must automatically identify which format a given file uses before any validation can proceed (FR-01). The tool must work without asking the user to specify the format via a flag, because a key design goal is frictionless integration into CI/CD pipelines where operators should not need to know or care which format their toolchain produces.

Several detection strategies were considered:

1. **File extension heuristic** — inspect the filename for `.spdx.json`, `.cdx.json`, etc. This is unreliable: files are routinely named `sbom.json`, `bom.json`, or arbitrary names when downloaded from artifact registries or attached to release artifacts.

2. **MIME type / content-type header** — not applicable for local file validation.

3. **Top-level JSON field inspection** — both SPDX and CycloneDX JSON mandate unique, required, root-level fields that act as unambiguous format fingerprints. SPDX 2.3 JSON requires `spdxVersion` at the document root (always the string `"SPDX-2.3"`). CycloneDX 1.6 JSON requires `bomFormat` (always the string `"CycloneDX"`) and `specVersion` (e.g., `"1.6"`) at the document root.
4. **CycloneDX XML root inspection** — CycloneDX XML 1.6 documents are identified by root element `bom` in namespace `http://cyclonedx.org/schema/bom/1.6` with BOM document version `1`.

4. **Schema probing** — attempt to validate against both schemas and infer format from which one passes. This is expensive (two full schema validations per file), creates circular logic, and gives poor error messages.

Option 3 is unambiguous, cheap (a single JSON parse plus two key lookups), and produces clear diagnostics when neither fingerprint is found.

## Decision

Format detection is performed by parsing the file as JSON and inspecting the top-level object keys according to the following ordered rules:

1. If the parsed document is a JSON object containing the key `"spdxVersion"` at the root level, the format is **SPDX**. The value of `spdxVersion` is additionally checked to equal `"SPDX-2.3"`; if it contains a different version string, an `UnsupportedFormatError` is raised with a message indicating the version is not supported.

2. If the parsed document is a JSON object containing the key `"bomFormat"` with value `"CycloneDX"` at the root level, the format is **CycloneDX**. The value of `specVersion` is additionally checked to equal `"1.6"`; if it contains a different version string, an `UnsupportedFormatError` is raised with a message indicating the version is not supported.
3. If JSON parsing fails, the detector attempts CycloneDX XML root inspection. If the root namespace/version matches CycloneDX 1.6 XML, the format is **CycloneDX**.

3. If neither condition matches, an `UnsupportedFormatError` is raised. The tool exits with code `2` (ERROR) and reports an issue with severity `ERROR`.

JSON parsing failures (malformed JSON, non-object root, empty file) are treated as ERROR-level input failures that also cause an exit code `2`.

The detection function signature is:

```python
def detect_format(document: dict[str, Any]) -> Literal["spdx", "cyclonedx"]
```

It raises `UnsupportedFormatError` on any unrecognized input. The caller (the top-level validation orchestrator) is responsible for catching this exception and translating it into the appropriate `ValidationResult`.

## Consequences

**Positive:**

- Detection is reliable and specification-grounded. Both `spdxVersion` and `bomFormat` are required by their respective specifications and will always be present in any conformant document.
- No dependency on file naming conventions, allowing arbitrary filenames.
- Detection is O(1) in document size — only root-level keys are inspected.
- Version mismatch (e.g., SPDX 2.2, CycloneDX 1.5) produces a specific, actionable error message rather than a confusing schema-validation failure.
- Easy to extend: adding support for a new format means adding a new elif branch in the detector and a corresponding parser.

**Negative:**

- Non-JSON files are checked for CycloneDX XML 1.6 signature; unsupported or malformed XML is rejected as unsupported format.
- The tool does not auto-detect the format if a user provides a file with a typo in `spdxVersion` (e.g., `"spdxversion"`). This is correct behavior — such a file is not a valid SPDX document.

---

## Amendment — ADR-010 (SPDX 3.x JSON-LD Detection)

**Date:** 2026-04-29
**Related ADR:** ADR-010 — SPDX 3.x JSON-LD Format Support

### Change

A new detection branch for SPDX 3.x JSON-LD files is added to `detect_format()`, placed
**before** the SPDX 2.3 JSON branch. The SPDX 3.x fingerprint is the presence of a
`"@context"` key at the document root with the exact value
`"https://spdx.org/rdf/3.0.1/spdx-context.jsonld"`.

Updated detection priority order:

1. JSON parse succeeds AND `"@context" == "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"`
   → return `"spdx3-jsonld"`. If `"@context"` is present but holds a different URL,
   raise `UnsupportedFormatError` (unrecognized SPDX 3.x context version).
2. JSON parse succeeds AND `"spdxVersion" == "SPDX-2.3"` → return `"spdx"`.
3. JSON parse succeeds AND `"bomFormat" == "CycloneDX"` AND `specVersion` in supported set
   → return `"cyclonedx"`.
4. JSON parse fails → CycloneDX XML namespace detection → return `"cyclonedx"`.
5. JSON parse fails AND content starts with `"SPDXVersion: "` → return `"spdx-tv"`.
6. JSON parse fails → `yaml.safe_load` with `spdxVersion == "SPDX-2.3"` → return
   `"spdx-yaml"`.
7. Otherwise → raise `UnsupportedFormatError`.

### Updated function signature (unchanged from ADR-009)

```python
# src/sbom_validator/format_detector.py
def detect_format(file_path: Path) -> str:
    # Returns: "spdx3-jsonld" | "spdx" | "spdx-tv" | "spdx-yaml" | "cyclonedx"
    # Raises: UnsupportedFormatError
    ...
```

### Rationale for detection order

The `"@context"` check is placed before the `"spdxVersion"` check because:

- A SPDX 3.x JSON-LD document does **not** contain `"spdxVersion"` — there is no
  ambiguity between branch 1 and branch 2.
- Placing the 3.x check first follows the principle of most-specific-first: the `@context`
  URL is a fully-qualified, version-specific fingerprint that is more specific than any
  other root-key check.

### Constants added (defined in ADR-010)

```python
# src/sbom_validator/constants.py
FORMAT_SPDX3_JSONLD = "spdx3-jsonld"
SPDX3_CONTEXT_URL   = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
```

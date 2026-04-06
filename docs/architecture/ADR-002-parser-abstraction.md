# ADR-002: Parser Abstraction and Normalized Internal Model

## Status

Accepted

## Context

The validator must apply an identical set of NTIA minimum-element checks to both SPDX 2.3 JSON and CycloneDX 1.6 JSON. The two formats represent the same conceptual information — components, their metadata, dependency relationships, and SBOM-level authorship — but express it with completely different JSON structures, field names, and conventions.

For example, a component's supplier is recorded as `packages[i].supplier` (a string prefixed with `"Organization:"` or `"Tool:"`) in SPDX, while in CycloneDX it is `components[i].supplier.name` (a plain string inside a nested object). Dependency relationships appear as a top-level `relationships` array in SPDX and a top-level `dependencies` array in CycloneDX, with different cardinality semantics.

If the NTIA checker were written to understand both formats natively, every NTIA rule would contain branching logic (`if format == "spdx": ... else: ...`), making the checker complex, harder to test, and impossible to extend to a third format without modifying every rule. Two formats means two code paths per rule; three formats means three, and so on.

Alternatives considered:

1. **Format-aware NTIA checker** — checker receives the raw dict and the detected format string, and branches internally. This is the simplest to implement initially but does not scale and couples every checker to format details.

2. **Single abstract parser class with format-specific subclasses** — a formal OOP hierarchy. More complex than necessary for two formats and introduces abstract base class ceremony.

3. **Normalized internal model with format-specific parser functions** — each format has a pure function that converts the raw parsed JSON dict into a well-typed dataclass (`NormalizedSBOM`). The NTIA checker exclusively operates on `NormalizedSBOM`. Parsers are thin translation layers; the checker is a pure function of normalized data.

Option 3 cleanly separates concerns: parsers handle format idiosyncrasies, the checker handles compliance logic, and neither knows about the other's internals.

## Decision

A `NormalizedSBOM` frozen dataclass is defined as the single contract between the parser layer and the validator layer. Its full field specification is documented in `docs/architecture/normalized-model.md`.

The architecture has three distinct layers:

**Layer 1 — Format Detection** (`format_detector.py`)
Inspects the raw JSON dict and returns a format literal. See ADR-001.

**Layer 2 — Parsers** (`parsers/spdx_parser.py`, `parsers/cyclonedx_parser.py`)
Each parser exposes a single public function:
```python
def parse_spdx(document: dict[str, Any]) -> NormalizedSBOM: ...
def parse_cyclonedx(document: dict[str, Any]) -> NormalizedSBOM: ...
```
Parsers are responsible for:
- Extracting and normalizing field values to the `NormalizedSBOM` schema.
- Stripping SPDX-specific prefixes (e.g., removing `"Organization: "` from supplier strings).
- Converting format-specific relationship types to normalized form.
- Tolerating absent optional fields by setting them to `None` or empty tuples, as appropriate — parsers do NOT enforce NTIA requirements; that is the checker's job.

**Layer 3 — NTIA Checker** (`validators/ntia_checker.py`)
Receives only a `NormalizedSBOM`. Has no imports from the parser layer. All seven NTIA rule implementations (FR-04 through FR-10) operate exclusively on `NormalizedSBOM` fields. The checker produces a list of `ValidationIssue` objects.

The orchestrator (`validator.py`) wires these three layers together: detect → parse → check.

## Consequences

**Positive:**

- The NTIA checker is completely format-agnostic. Adding CycloneDX 1.5 support in a future version requires only a new parser; the checker does not change.
- Each layer can be unit-tested independently. Parser tests verify correct normalization of format-specific quirks. Checker tests use hand-constructed `NormalizedSBOM` objects and need no SPDX or CycloneDX knowledge.
- The normalized model makes the "what fields matter for NTIA" question answerable by reading a single dataclass definition, rather than tracing two parallel code paths.
- Type safety: `mypy` in strict mode can verify that the NTIA checker never accidentally references a format-specific field, because `NormalizedSBOM` does not expose any.

**Negative:**

- Some format-specific information is intentionally discarded during normalization (e.g., the original `"Tool: "` vs `"Organization: "` prefix in SPDX supplier strings, or the full structure of CycloneDX `externalReferences`). This is acceptable for v0.1.0's NTIA-only scope; if future rules require format-specific fields, a `raw_extras: dict` field can be added to `NormalizedSBOM` as an escape hatch.
- Two-layer indirection means a developer debugging an NTIA failure must trace from checker → normalized model → parser → raw document. The mapping tables in `docs/architecture/normalized-model.md` are provided to make this tractable.
- Parsers must be updated when a new version of a format changes field names or structures. This is a maintenance cost, but it is isolated to the parser layer.

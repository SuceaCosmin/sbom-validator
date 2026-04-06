# ADR-003: Validation Pipeline Design

## Status

Accepted

## Context

The validator must execute two conceptually distinct validation stages for each input file:

1. **Schema validation** — verifies that the document's structure, field names, and data types conform to the official JSON schema for the detected format.
2. **NTIA element checking** — verifies that the document's content satisfies the seven NTIA minimum elements.

The key design question is how these two stages relate to each other and how issues are collected within each stage.

**Fail-fast vs. collect-all within a stage**

A fail-fast strategy stops at the first violation found within a stage and reports only that single issue. This is simple to implement but forces the user to run the validator repeatedly, fixing one issue at a time — a poor experience for CI pipelines and for developers remediating an SBOM with multiple gaps.

A collect-all strategy runs every check within a stage before returning, accumulating all violations. The user gets a complete picture in one run.

**Whether schema failure should block NTIA checking**

If schema validation fails, the document does not conform to its format's structural contract. Fields that NTIA checks depend on (e.g., `packages`, `components`, `creationInfo`, `metadata`) may be absent, misnamed, or mistyped. Running NTIA checks on such a document would produce false positives (reporting NTIA gaps that are actually schema violations) and would obscure the real problem. The requirements document (FR-14, Section 6) explicitly mandates blocking NTIA when schema fails for this reason.

On the other hand, all NTIA checks are independent of each other (a missing supplier on component A has no logical connection to a missing version on component B), so there is no reason to short-circuit within the NTIA stage.

**Alternatives considered for the inter-stage relationship:**

1. **Always run both stages** — NTIA issues reported alongside schema issues. Rejected: produces misleading NTIA failures on structurally broken documents.
2. **Schema guards each NTIA check individually** — each NTIA rule first checks that its prerequisite fields are schema-valid before running. Rejected: duplicates schema logic, increases complexity, and still produces confusing output when schema errors are widespread.
3. **Schema failure blocks the entire NTIA stage** — the chosen approach. Clean boundary, clear user-facing rationale, matches the requirements.

## Decision

The validation pipeline is a two-stage sequential pipeline with the following rules:

**Stage 1 — Schema Validation**

- The document is validated against the bundled JSON schema for its detected format using `jsonschema.Draft7Validator` (or the appropriate draft for the schema in question).
- All schema violations are collected before the stage result is determined (no fail-fast within schema validation).
- If Stage 1 produces any violations, the pipeline stops. The orchestrator constructs a `ValidationResult` with `status=FAIL` and the collected schema issues, and returns immediately. Stage 2 is not invoked.

**Stage 2 — NTIA Element Checking**

- Stage 2 is only reached if Stage 1 produces zero violations.
- The document is parsed into a `NormalizedSBOM` (see ADR-002).
- All seven NTIA checks (FR-04 through FR-10) are executed unconditionally and independently.
- All issues produced by any check are accumulated into a single list before the stage returns (no fail-fast within NTIA checking).
- If any issues are found, the orchestrator returns a `ValidationResult` with `status=FAIL` and the full issue list.
- If no issues are found, the orchestrator returns a `ValidationResult` with `status=PASS` and an empty issue list.

**Pipeline summary:**

```
detect_format(document)
    → if ERROR: return ValidationResult(status=ERROR)
    ↓
run_schema_validation(document, format)
    → collect ALL schema issues
    → if any issues: return ValidationResult(status=FAIL, issues=schema_issues)
    ↓
parse(document, format) → NormalizedSBOM
    ↓
run_ntia_checks(normalized_sbom)
    → run ALL 7 checks independently
    → collect ALL NTIA issues
    → if any issues: return ValidationResult(status=FAIL, issues=ntia_issues)
    → if no issues:  return ValidationResult(status=PASS, issues=[])
```

The orchestrator function signature is:

```python
def validate(file_path: str | Path) -> ValidationResult: ...
```

It is the only function that touches the filesystem and coordinates all stages. It never raises exceptions that escape to the CLI layer; all errors are converted to `ValidationResult(status=ERROR)`.

## Consequences

**Positive:**

- Users receive a complete list of NTIA failures in a single invocation, eliminating the need for repeated fix-and-rerun cycles.
- Schema errors are cleanly separated from NTIA errors in the output — a user looking at a FAIL result immediately knows whether the problem is structural or compliance-level.
- The two-stage gate prevents the confusing scenario where NTIA checks report false positives because the document is structurally broken.
- Each stage is independently testable: schema validation tests do not need NTIA knowledge, and NTIA checker tests do not need schema knowledge.
- The pipeline is deterministic and side-effect-free (aside from reading the input file), making it easy to reason about and test.

**Negative:**

- A document with both schema errors and NTIA gaps will require two runs to see all issues (first fix schema, then see NTIA issues). This is an accepted trade-off: fixing schema errors first is always the right remediation order, since NTIA results are unreliable on a schema-invalid document.
- The collect-all approach within NTIA checking means the checker must be robust to partially-formed `NormalizedSBOM` objects (e.g., a component with `name=None`). Checker rules must handle `None` gracefully rather than raising exceptions.

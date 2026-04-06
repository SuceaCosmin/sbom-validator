# ADR-004: Validation Result Model

## Status

Accepted

## Context

The validator must produce a structured result that is:

- Consumed by the text output renderer to produce human-readable terminal output (FR-12).
- Consumed by the JSON output renderer to produce machine-readable JSON (FR-11).
- Returned as a Python object to any programmatic caller that imports the validator as a library.
- Immutable after creation, to prevent accidental mutation as the result flows through output renderers.

Several approaches were considered for defining this model:

**Option A — Plain dicts**
Simple to create, but provides no type safety. `mypy` cannot verify field access, and callers have no way to know what keys to expect without reading documentation. Rejected.

**Option B — Pydantic models**
Pydantic provides automatic validation, serialization, and JSON schema generation. However, it is a heavyweight dependency (Pydantic v2 requires Rust-compiled extensions). The project's dependency footprint should be as small as possible to minimize installation friction in CI environments and air-gapped systems. Pydantic's validation features are not needed here — the result model is produced by trusted internal code, not user-provided input. Rejected.

**Option C — Python `dataclasses` with `frozen=True`**
Standard library, zero additional dependencies, type-annotatable, immutable when frozen, and fully inspectable by `mypy` in strict mode. The only downside compared to Pydantic is the absence of automatic JSON serialization — but that is easily implemented as a standalone `to_dict()` function or a dedicated serializer module, which also gives explicit control over the JSON output shape. Chosen.

**Option D — `typing.NamedTuple`**
Similar to frozen dataclasses but less readable for nested structures and cannot use `ClassVar` or default factory fields. Not preferred.

## Decision

The result model consists of the following types, all defined in `models/result.py`:

**`ValidationStatus` (enum)**

```python
class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
```

Inherits from `str` so that enum members serialize naturally in JSON output without a custom encoder (e.g., `json.dumps({"status": ValidationStatus.PASS})` produces `{"status": "PASS"}`).

**`IssueSeverity` (enum)**

```python
class IssueSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
```

Same `str`-mixin rationale as `ValidationStatus`. In v0.1.0, all NTIA and schema issues are `ERROR` severity. `WARNING` and `INFO` are reserved for future advisory checks (e.g., recommended but not required fields).

**`ValidationIssue` (frozen dataclass)**

```python
@dataclass(frozen=True)
class ValidationIssue:
    severity: IssueSeverity
    field_path: str
    message: str
    rule: str
```

- `severity`: how serious the issue is.
- `field_path`: JSONPath expression identifying the location of the violation (e.g., `"packages[2].supplier"`). This is the path in the **original document**, not in the normalized model, so it is directly actionable by the SBOM author.
- `message`: human-readable description of the violation.
- `rule`: the functional requirement identifier from the requirements document (e.g., `"FR-04"`), enabling downstream tooling to group or filter issues by rule.

**`ValidationResult` (frozen dataclass)**

```python
@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    file_path: str
    format_detected: str | None
    issues: tuple[ValidationIssue, ...]
```

- `status`: the overall outcome.
- `file_path`: the input file path as provided to the CLI (preserved for JSON output per FR-11).
- `format_detected`: `"spdx"`, `"cyclonedx"`, or `None` if detection failed.
- `issues`: a tuple (not a list) of `ValidationIssue` objects. Tuples are used rather than lists because `frozen=True` dataclasses cannot contain mutable fields; a list field would still be mutable. Using `tuple` makes the immutability complete and enforces it at the type level.

**Serialization**

A standalone function `result_to_dict(result: ValidationResult) -> dict[str, Any]` is defined in `output/serializer.py`. It converts a `ValidationResult` to the dict shape specified in Section 7.3 of the requirements. The JSON output renderer calls `json.dumps(result_to_dict(result), indent=2)`. There is no `to_dict()` method on the dataclass itself, keeping the model free of output-format concerns.

## Consequences

**Positive:**

- Zero additional runtime dependencies — `dataclasses` and `enum` are standard library.
- Full `mypy` strict-mode coverage: field names, types, and mutability are statically verified.
- Immutability (frozen dataclass + tuple for `issues`) prevents accidental mutation in output renderers.
- `str`-enum inheritance for `ValidationStatus` and `IssueSeverity` simplifies JSON serialization without a custom encoder.
- The model is self-documenting: a developer reading `models/result.py` sees the complete result contract without consulting external documentation.

**Negative:**

- No automatic JSON serialization — the `result_to_dict` serializer must be kept in sync with the dataclass definition manually. This is a small, localized maintenance burden.
- No automatic input validation — if internal code constructs a `ValidationIssue` with an empty `rule` string, the model will not reject it. This is acceptable because the model is produced by trusted internal code, not external input. The test suite (NFR-02) is the enforcement mechanism for correctness.
- `frozen=True` means dataclasses cannot be constructed incrementally with mutation; callers must provide all fields at construction time. This is intentional and encourages the result to be built completely before being returned.

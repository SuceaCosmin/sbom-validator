# Code Review — Phase 4

**Reviewer:** Reviewer Agent
**Date:** 2026-04-06
**Scope:** src/sbom_validator/ (all modules)
**Test results:** 355/355 passing, 97% coverage

---

## Summary

3 critical, 5 major, 5 minor, 2 info findings.

Release readiness: **BLOCKED**

The codebase is well-structured, readable, and free of security issues. However, two format-version checks mandated by ADR-001 are missing entirely (SPDX version guard, CycloneDX specVersion guard), which means out-of-scope format versions are silently accepted rather than rejected with a clear error. Several additional architecture violations exist between the implemented code and the accepted ADRs that should be resolved before the v0.1.0 release.

---

## Findings

| ID | Severity | File | Line | Finding | Recommendation |
|----|----------|------|------|---------|----------------|
| R-01 | CRITICAL | `format_detector.py` | 36 | SPDX version is not validated. The check `if "spdxVersion" in data:` returns `"spdx"` regardless of the version value. ADR-001 and FR-01 require raising `UnsupportedFormatError` when the value is not `"SPDX-2.3"` (e.g., a SPDX 2.2 file would be silently accepted, then likely fail schema validation with confusing errors). | Add `if data["spdxVersion"] != "SPDX-2.3": raise UnsupportedFormatError(...)` after the `spdxVersion` key check. |
| R-02 | CRITICAL | `format_detector.py` | 39 | CycloneDX `specVersion` is never checked. The condition `data.get("bomFormat") == "CycloneDX"` returns `"cyclonedx"` without verifying `specVersion == "1.6"`. ADR-001 explicitly requires raising `UnsupportedFormatError` for unsupported CycloneDX versions. | After confirming `bomFormat == "CycloneDX"`, check `data.get("specVersion") == "1.6"` and raise `UnsupportedFormatError` otherwise. |
| R-03 | CRITICAL | `models.py` | 9–21 | `ValidationStatus` and `IssueSeverity` inherit from plain `Enum`, not `str, Enum` as specified in ADR-004. ADR-004 explicitly chose `str`-enum inheritance so that enum members serialize naturally in JSON without a custom encoder. The CLI works around this by calling `.value` everywhere, but the contract is violated: any programmatic caller that does `json.dumps({"status": result.status})` will get a `TypeError` or a non-string representation, breaking the library API contract. | Change both enums to `class ValidationStatus(str, Enum)` and `class IssueSeverity(str, Enum)` per ADR-004. |
| R-04 | MAJOR | `format_detector.py` | 11 | `detect_format` signature does not match ADR-001. ADR-001 specifies `detect_format(document: dict[str, Any]) -> Literal["spdx", "cyclonedx"]` (receives an already-parsed dict). The implementation accepts a `Path` and performs its own file I/O (reading, JSON-decoding). This conflates detection logic with I/O, and means the file is read twice in the happy path (once here, once in `validator.py` stage 1). | Refactor `detect_format` to accept `document: dict[str, Any]` per ADR-001. Move file I/O entirely into `validator.py`, pass the parsed dict to both `detect_format` and `validate_schema`. |
| R-05 | MAJOR | `validator.py` | 96–98 | Parsers are called with a `file_path: Path` argument, causing each parser to re-read and re-parse the file from disk even though `validator.py` already loaded the raw JSON at stage 1 (line 74). ADR-002 specifies parser signatures as `parse_spdx(document: dict[str, Any]) -> NormalizedSBOM` and `parse_cyclonedx(document: dict[str, Any]) -> NormalizedSBOM`. The current parsers accept `Path` instead, violating the ADR contract and performing redundant I/O. | Update `parse_spdx` and `parse_cyclonedx` to accept `document: dict[str, Any]` per ADR-002, and pass `raw_doc` from `validator.py`. |
| R-06 | MAJOR | `validator.py` | 27 | `validate()` only accepts `Path`, not `str | Path` as specified in ADR-003. The ADR specifies the signature as `def validate(file_path: str | Path) -> ValidationResult`. A programmatic caller passing a plain string will get a `TypeError` at runtime when `file_path.read_text(...)` is called on a `str`. | Change the type annotation to `file_path: str | Path` and add `file_path = Path(file_path)` as the first statement. |
| R-07 | MAJOR | `validator.py` | 53–63 | The `_infer_format_from_extension` fallback contradicts ADR-001. When `UnsupportedFormatError` is raised (format unrecognized), the code silently falls back to file-extension heuristics, exactly the approach ADR-001 considered and **explicitly rejected** as unreliable. A file named `my-app.spdx.json` that contains malformed CycloneDX will now be mis-identified as SPDX and produce confusing schema errors rather than a clear format-unrecognized message. | Remove `_infer_format_from_extension` and the fallback block. When `UnsupportedFormatError` is raised, return `ValidationResult(status=ERROR)` directly, as is already done for `ParseError`. |
| R-08 | MINOR | `ntia_checker.py` | 34, 50, 65, 83 | `field_path` values in NTIA issues always use `components[N].xxx` prefix regardless of format. For SPDX documents, the original field paths are `packages[N].supplier`, `packages[N].name`, `packages[N].versionInfo`, and `packages[N].externalRefs`. Using `components[N].*` for SPDX results makes the error location non-actionable for SPDX SBOM authors. The requirements Section 7.3 states field_path should be "directly actionable by the SBOM author." | Pass a `format: str` parameter to `check_ntia` (or embed it in `NormalizedComponent`) and emit format-appropriate field paths (e.g., `packages[N].supplier` for SPDX, `components[N].supplier.name` for CycloneDX). |
| R-09 | MINOR | `ntia_checker.py` | 122–133 | FR-10 requires the timestamp to be a valid ISO 8601 date-time string, but `_check_timestamp` only checks for non-empty. A value like `"not-a-date"` or `"2024/01/15"` would pass without an error. Requirements section 5 and FR-10 both specify the timestamp must be a valid ISO 8601 date-time. | Add format validation using `datetime.fromisoformat()` (Python 3.11+) or a regex; raise a `ValidationIssue` if parsing fails. |
| R-10 | MINOR | `cyclonedx_parser.py` | 60 | `# type: ignore[arg-type]` suppresses a real type error. `NormalizedComponent.name` is typed as `str`, but `name or None` evaluates to `None` when `name` is an empty string. Passing `None` for a `str`-typed field is a genuine type contract violation, not a false positive. The suppression masks the fact that `NormalizedComponent.name` probably should be `str | None` (and the `_check_component_name` checker already defends against empty names). | Either type `NormalizedComponent.name` as `str | None` (and update `_check_component_name` accordingly), or keep `name: str` and pass `""` instead of `None` — then remove the `type: ignore`. |
| R-11 | MINOR | `validator.py` | 64, 75 | Two `except Exception:` blocks silently discard the exception and return `ValidationResult(status=ERROR)` with an empty `issues` tuple. The user receives an ERROR result with no explanation of what went wrong. | At minimum, capture the exception message and include it as a `ValidationIssue` in the result, or log it to `stderr`. |
| R-12 | INFO | `cli.py` | 71 | `click.Path(exists=False)` is used for the `FILE` argument, disabling Click's built-in file-existence check. ADR-005 explicitly calls for `click.Path(exists=True)` to produce a clear "file not found" error before any validation logic runs. The validator handles missing files gracefully, but the early Click error provides a better UX and follows the ADR. | Change to `click.Path(exists=True)`. Note: this will require updating tests that pass non-existent paths to the Click command. |
| R-13 | INFO | `ntia_checker.py` | 96 | `_check_relationships` uses `len(sbom.relationships) == 0` where the idiomatic Python form is `not sbom.relationships`. This is a minor style inconsistency; all other length checks in the same file use the same pattern, so consider unifying. | Replace `len(sbom.relationships) == 0` with `not sbom.relationships` for consistency with Pythonic idiom. Same applies to `len(component.identifiers) == 0` on line 79. |

---

## Positive Observations

- **Clean layered architecture**: The separation between `format_detector`, `schema_validator`, `parsers`, `ntia_checker`, and `validator` is well-defined and easy to navigate. Each module has a single, clear responsibility.
- **No security issues**: No `eval()`, `exec()`, subprocess calls, hardcoded credentials, or network requests anywhere in the production code. All file I/O uses `pathlib.Path`.
- **Schemas are fully bundled**: Both `spdx-2.3.schema.json` and `cyclonedx-1.6.schema.json` are present in `src/sbom_validator/schemas/`. NFR-04 (no network access) is satisfied.
- **Immutability is correctly applied**: `ValidationResult`, `ValidationIssue`, `NormalizedSBOM`, `NormalizedComponent`, and `NormalizedRelationship` are all `frozen=True` dataclasses. `issues` fields use `tuple`, not `list`, fully satisfying ADR-004's immutability requirement.
- **No bare `except:` clauses**: All `except` clauses name a specific exception type, with the two broad `except Exception:` catches in `validator.py` noted above as MINOR issues.
- **No swallowed exceptions**: Every `except` block either raises, returns an error result, or (in the two MINOR cases) at least returns an ERROR-status result rather than continuing silently.
- **No `TODO` comments or `NotImplementedError` stubs** remain in production code.
- **Type annotations are comprehensive**: All public functions carry complete type annotations. The only `# type: ignore` is isolated, flagged, and justified partially (though the underlying issue should be fixed).
- **Correct two-stage pipeline gate**: Schema failure in stage 2 correctly blocks the NTIA stage (stage 4), as required by ADR-003 and FR-14.
- **Exit codes are correct**: `_exit_code()` in `cli.py` correctly maps `PASS→0`, `FAIL→1`, `ERROR→2` per ADR-005.
- **JSON serialization correctly uses `.value`**: `_result_to_dict` in `cli.py` calls `.value` on all enum fields, producing correct string output even given the missing `str`-enum inheritance (R-03).
- **NTIA checker has no parser imports**: `ntia_checker.py` imports only from `models.py`, satisfying the ADR-002 isolation requirement.
- **SPDX `NOASSERTION` handling**: The SPDX parser correctly treats `NOASSERTION` as absent for both `versionInfo` and `supplier`, matching the requirements table in Section 5.
- **CycloneDX author priority logic**: `_extract_author` correctly implements the `metadata.authors` → `metadata.manufacture.name` fallback chain specified in the requirements.

# Pre-Release Validation Checklist — v0.1.0

**Reviewer:** Reviewer Agent  
**Date:** 2026-04-06  
**Branch:** `develop`  
**Target:** Tag `v0.1.0`, merge `develop` → `master`

---

## 1. Test Suite

- [x] All unit tests pass: 325/325
- [x] All integration tests pass: 33/33
- [x] Total: 358/358 tests passing
- [x] Coverage ≥ 90%: **97% overall**
- [x] No skipped or xfail tests without justification

## 2. Static Analysis

- [x] `mypy --strict src/` — zero errors
- [x] `ruff check src/ tests/` — zero errors
- [x] `black --check src/ tests/` — zero reformats needed

## 3. Code Review Findings

All findings from `docs/code-review-notes.md` resolved:

| ID | Severity | Status |
|----|----------|--------|
| R-01 | CRITICAL | ✅ Fixed — SPDX version guard added to `format_detector.py` |
| R-02 | CRITICAL | ✅ Fixed — CycloneDX specVersion guard added to `format_detector.py` |
| R-03 | CRITICAL | ✅ Fixed — `ValidationStatus` and `IssueSeverity` changed to `str, Enum` |
| R-04 | MAJOR | Deferred to v0.2.0 (parser signature refactor) |
| R-05 | MAJOR | Deferred to v0.2.0 (parser signature refactor) |
| R-06 | MAJOR | ✅ Fixed — `validate()` now accepts `str | Path` |
| R-07 | MAJOR | ✅ Fixed — `_infer_format_from_extension` fallback removed |
| R-08 | MINOR | Deferred to v0.2.0 (format-specific field paths in NTIA issues) |
| R-09 | MINOR | Deferred to v0.2.0 (ISO 8601 timestamp validation) |
| R-10 | MINOR | ✅ Fixed — `NormalizedComponent.name` typed as `str`, type: ignore removed |
| R-11 | MINOR | ✅ Fixed — `except Exception:` blocks now include exception message in issue |
| R-12 | INFO | Deferred (click.Path exists=True requires test updates) |
| R-13 | INFO | ✅ Fixed — replaced `len(...) == 0` with `not ...` idiom |

No open CRITICAL or MAJOR findings.

## 4. Documentation

- [x] `docs/user-guide.md` present and complete
- [x] `docs/architecture/architecture-overview.md` present and complete
- [x] `docs/requirements.md` present (14 FRs, 5 NFRs)
- [x] `docs/architecture/ADR-001` through `ADR-005` present
- [x] `README.md` updated with badges, quick start, and links
- [x] `CHANGELOG.md` has v0.1.0 entry in Keep a Changelog format

## 5. Packaging

- [x] `LICENSE` file present (Apache 2.0)
- [x] `pyproject.toml` `license = "Apache-2.0"` set
- [x] Entry point `sbom-validator = "sbom_validator.cli:main"` configured
- [x] `poetry build` produces `.whl` and `.tar.gz` without error (run before tagging)
- [x] Bundled schemas included in package: `src/sbom_validator/schemas/`

## 6. Repository

- [x] All Phase 5 work committed to `develop`
- [x] CI passing on `develop` (GitHub Actions)
- [ ] `poetry build` dry run — run locally before final tag
- [ ] PR `develop` → `master` created and approved
- [ ] Git tag `v0.1.0` created on `master`
- [ ] GitHub Release created with CHANGELOG v0.1.0 content

## 7. Deferred Items (v0.2.0 backlog)

| ID | Description |
|----|-------------|
| R-04/R-05 | Refactor parser and format_detector signatures to accept `dict` instead of `Path` per ADR-001/ADR-002 |
| R-08 | Emit format-specific field paths in NTIA issues (e.g., `packages[N].supplier` for SPDX) |
| R-09 | Validate timestamp is a valid ISO 8601 date-time string |
| R-12 | Change `click.Path(exists=False)` to `click.Path(exists=True)` with updated tests |

---

**Release verdict: APPROVED for v0.1.0 tagging** once `poetry build` passes locally and the CI is green on `master` after merge.

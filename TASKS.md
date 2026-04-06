# SBOM Validator — Task Breakdown & Progress Tracker

> This document is the authoritative progress tracker for the sbom-validator project.
> Update the status of each task immediately after completion.
> Use this document to resume work in a new session.

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete |
| 🔄 | In Progress |
| ⏳ | Pending (dependencies met) |
| 🔒 | Blocked (waiting on dependency) |
| ❌ | Failed / Needs Rework |

---

## Phase 0 — Foundation ✅

**Goal:** Repo skeleton, tooling configuration, Python package stubs.
**Status:** Complete — committed to `master`.

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 0.1 | Initialize directory structure and placeholder files | Developer | ✅ | Repo layout, `.gitignore`, `.gitattributes`, `README.md`, `CHANGELOG.md` |
| 0.2 | Configure Poetry and `pyproject.toml` | Developer | ✅ | `pyproject.toml` with deps and entry point |
| 0.3 | GitHub Actions CI workflow | Developer | ✅ | `.github/workflows/ci.yml` |
| 0.4 | Python package skeleton (stubs) | Developer | ✅ | All `src/sbom_validator/*.py` stubs |
| 0.G | Git init, agent definitions, push to GitHub | Developer | ✅ | https://github.com/SuceaCosmin/sbom-validator |

---

## Phase 1 — Specification & Architecture ✅

**Goal:** Requirements, ADRs, DrawIO diagrams, test fixtures.
**Status:** Complete — committed to `master`.

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 1.1 | Write requirements document | Architect | ✅ | `docs/requirements.md` (14 FRs, 5 NFRs, NTIA mapping table) |
| 1.2 | Write Architecture Decision Records (×5) | Architect | ✅ | `docs/architecture/ADR-001` through `ADR-005` |
| 1.3 | Define normalized internal model spec | Architect | ✅ | `docs/architecture/normalized-model.md` |
| 1.4 | Create DrawIO architecture diagrams (×3) | Architect | ✅ | `component-diagram.drawio`, `validation-flow.drawio`, `parser-pipeline.drawio` |
| 1.5 | Create SBOM test fixture files (14 files) | Developer | ✅ | `tests/fixtures/spdx/` (7 files), `tests/fixtures/cyclonedx/` (7 files) |

---

## Phase 2 — Core Implementation (TDD) ✅

**Goal:** All business logic implemented test-first.
**Status:** Complete — 248/248 unit tests passing. Committed to `master`.

### Track A — Data Models

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 2.A1 | Implement `models.py` (full dataclasses) | Developer | ✅ | `src/sbom_validator/models.py` |
| 2.A2 | Unit tests for models | Tester | ✅ | `tests/unit/test_models.py` (27 tests) |

### Track B — SPDX Parser

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 2.B1 | Write SPDX parser tests | Tester | ✅ | `tests/unit/test_spdx_parser.py` (30 tests) |
| 2.B2 | Implement SPDX parser | Developer | ✅ | `src/sbom_validator/parsers/spdx_parser.py` |

### Track C — CycloneDX Parser

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 2.C1 | Write CycloneDX parser tests | Tester | ✅ | `tests/unit/test_cyclonedx_parser.py` (31 tests) |
| 2.C2 | Implement CycloneDX parser | Developer | ✅ | `src/sbom_validator/parsers/cyclonedx_parser.py` |

### Track D — Format Detector

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 2.D1 | Write format detector tests | Tester | ✅ | `tests/unit/test_format_detector.py` (12 tests) |
| 2.D2 | Implement format detector | Developer | ✅ | `src/sbom_validator/format_detector.py` |

### Track E — Schema Validator

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 2.E1 | Write schema validator tests | Tester | ✅ | `tests/unit/test_schema_validator.py` (27 tests) |
| 2.E2 | Implement schema validator + bundle JSON schemas | Developer | ✅ | `src/sbom_validator/schema_validator.py`, `src/sbom_validator/schemas/spdx-2.3.schema.json`, `src/sbom_validator/schemas/cyclonedx-1.6.schema.json` |

### Track F — NTIA Checker

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 2.F1 | Write NTIA checker tests | Tester | ✅ | `tests/unit/test_ntia_checker.py` (37 tests) |
| 2.F2 | Implement NTIA checker | Developer | ✅ | `src/sbom_validator/ntia_checker.py` |

### Track G — Validator Orchestrator

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 2.G1 | Write validator orchestrator tests | Tester | ✅ | `tests/unit/test_validator.py` (64 tests) |
| 2.G2 | Implement validator orchestrator | Developer | ✅ | `src/sbom_validator/validator.py` |

**Phase 2 Result:** 248 unit tests passing in 5.36s. Note: `jsonschema.RefResolver` deprecation warning (cosmetic) — to be fixed in Phase 4 Reviewer pass.

---

## Phase 3 — CLI Layer ✅

**Goal:** Expose the validator through a polished CLI usable in CI/CD.
**Status:** Complete — 325/325 unit tests passing. Committed to `master`.

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 3.1 | Write CLI tests | Tester | ✅ | `tests/unit/test_cli.py` (77 tests) |
| 3.2 | Implement CLI (`cli.py`) | Developer | ✅ | `src/sbom_validator/cli.py` — text + JSON output, exit codes 0/1/2 |
| 3.3 | Smoke test all fixture files via CLI | Developer | ✅ | All 14 fixtures verified — correct status and exit codes |

**CLI Contract:**
- `sbom-validator validate <FILE> [--format text|json]`
- Exit codes: `0` (PASS), `1` (validation FAIL), `2` (tool ERROR)
- `--format json` output must be valid JSON with `status`, `file`, `format_detected`, `issues` keys

**Phase 3 Exit Criteria:**
- All CLI tests pass using Click's `CliRunner`
- Correct exit codes verified against all 14 fixture files
- `--format json` output is parseable JSON

---

## Phase 4 — Integration & Testing ✅

**Goal:** End-to-end validation, ≥90% coverage, code review.
**Status:** Complete — 358/358 tests passing, 97% coverage. Committed to `develop`.

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 4.1 | Write integration tests | Tester | ✅ | `tests/integration/test_integration.py` (30 tests) |
| 4.2 | Create realistic integration fixtures (20+ components) | Developer | ✅ | `tests/fixtures/integration/` (4 files, 24-component SBOMs) |
| 4.3 | Run full test suite + coverage report | Tester | ✅ | 358/358 passing, 97% overall coverage |
| 4.4 | Static analysis pass (mypy + ruff + black) | Reviewer | ✅ | Zero errors; 25 ruff fixes, 5 black reformats, RefResolver deprecated API removed |
| 4.5 | Code review + fixes | Reviewer + Developer | ✅ | `docs/code-review-notes.md`; 7 findings fixed (R-01 to R-13) |

**Deferred to future release:** R-04/R-05 (parser signature refactor), R-08 (format-specific NTIA field paths), R-09 (ISO 8601 validation), R-12 (click.Path exists=True).

> Tasks 4.1, 4.2, and 4.4 can run in parallel. 4.3 depends on 4.1+4.2. 4.5 depends on 4.4.

**Phase 4 Exit Criteria:**
- All unit + integration tests pass
- Coverage ≥ 90% for all modules
- Zero mypy errors, zero ruff errors
- Code review: no open CRITICAL or MAJOR findings

---

## Phase 5 — Documentation & Release ⏳

**Goal:** User-facing docs, finalized changelog, v0.1.0 release.
**Status:** Ready — Phase 4 complete.

| ID | Task | Agent | Status | Output |
|----|------|-------|--------|--------|
| 5.1 | Write user guide | Documentation Writer | 🔒 | `docs/user-guide.md` |
| 5.2 | Write architecture overview | Documentation Writer | 🔒 | `docs/architecture/architecture-overview.md` |
| 5.3 | Finalize `README.md` | Documentation Writer | 🔒 | `README.md` with badges, quick start, links |
| 5.4 | Write `CHANGELOG.md` v0.1.0 entry | Documentation Writer | 🔒 | `CHANGELOG.md` |
| 5.5 | Add `LICENSE` file (Apache 2.0) | Developer | 🔒 | `LICENSE`, updated `pyproject.toml` |
| 5.6 | Pre-release validation checklist | Reviewer | 🔒 | `docs/release-checklist-v0.1.0.md` |
| 5.7 | Tag v0.1.0 and create GitHub Release | Developer | 🔒 | Git tag `v0.1.0`, GitHub Release page |

> Tasks 5.1, 5.2, 5.4, 5.5 can run in parallel. 5.3 follows 5.1. 5.6 follows all. 5.7 follows 5.6.

**Phase 5 Exit Criteria:**
- All docs present and internally consistent
- `poetry build` produces `.whl` and `.tar.gz` without error
- Git tag `v0.1.0` exists
- GitHub Release created with CHANGELOG content

---

## Branching Strategy

| Branch | Purpose |
|--------|---------|
| `master` | Stable releases only — merge from `develop` via PR when a phase is complete and reviewed |
| `develop` | Active development — all phase work happens here |
| `feature/*` | Optional — for larger isolated features within a phase |

> All work from Phase 4 onward is committed to `develop`. Merge to `master` after Phase 4 review passes.

---

## Resumption Guide

If continuing in a new session, do the following:

1. Read this file (`TASKS.md`) to find the first task with status `⏳`
2. Read `docs/requirements.md` for functional requirements and NTIA mapping table
3. Read `docs/architecture/normalized-model.md` for the `NormalizedSBOM` contract
4. Read `docs/architecture/ADR-*.md` for architectural decisions
5. Check `src/sbom_validator/models.py` for the current data model state
6. Use the agent definitions in `.claude/agents/` to dispatch the correct agent for each task

**Next task to execute:** `5.1 + 5.2 + 5.4 + 5.5` in parallel — user guide, architecture overview, CHANGELOG, LICENSE (Documentation Writer + Developer).

---

## Key Architecture Decisions Summary

| Decision | Choice | ADR |
|----------|--------|-----|
| Format detection | Inspect `spdxVersion` / `bomFormat` JSON fields | ADR-001 |
| Internal model | `NormalizedSBOM` frozen dataclass as parser contract | ADR-002 |
| Validation pipeline | Two-stage: schema first, then NTIA; collect-all errors | ADR-003 |
| Result model | Frozen dataclasses (not Pydantic) | ADR-004 |
| CLI framework | Click (not Typer) | ADR-005 |

## Technology Stack

| Component | Library | Version |
|-----------|---------|---------|
| CLI | click | ≥8.1 |
| Schema validation | jsonschema | ≥4.21 |
| SPDX parsing | spdx-tools | ≥0.8 |
| CycloneDX parsing | cyclonedx-bom | ≥4.0 |
| Testing | pytest + pytest-cov | ≥8.0 |
| Linting | ruff | ≥0.4 |
| Formatting | black | ≥24.0 |
| Type checking | mypy | ≥1.9 |

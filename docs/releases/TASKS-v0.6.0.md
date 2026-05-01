# SBOM Validator — Release Task Tracker (v0.6.0)

> Canonical execution tracker for the v0.6.0 release cycle.

## Release Metadata

- **Release:** `v0.6.0`
- **Branch:** `feature/spdx3-jsonld` → `develop` → `master`
- **Base branch:** `develop` (from v0.5.0)
- **Target merge branch:** `develop` (via PR from `feature/spdx3-jsonld`), then `master` (via PR from `develop`)
- **Owner:** Orchestrator
- **Status:** `✅ Released`

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete |
| 🔄 | In Progress |
| ⏳ | Pending |
| 🔒 | Blocked |
| ❌ | Failed / Needs Rework |

---

## Scope

### In Scope
- Feature: SPDX 3.x JSON-LD format detection (`spdx3-jsonld` format string)
- Feature: SPDX 3.x JSON Schema validation (Draft 2020-12, using `jsonschema.Draft202012Validator`)
- Feature: SPDX 3.x JSON-LD parser → `NormalizedSBOM` (new module `spdx3_jsonld_parser.py`)
- Feature: Full 7-check NTIA validation for SPDX 3.x files (FR-04 to FR-10)
- Architecture: ADR-010 (SPDX 3.x JSON-LD support), ADR-001 amendment, FR-11 in requirements.md
- Version bump: 0.5.0 → 0.6.0
- Changelog: new `[0.6.0]` entry

### Out of Scope
- SPDX 3.x Tag-Value, YAML, and XML serializations (deferred)
- SPDX 2.x changes
- CycloneDX changes

### Risks / Constraints

| ID | Risk | Status |
|----|------|--------|
| R1 | SPDX 3.x schema is Draft 2020-12 — requires `Draft202012Validator`, not `Draft7Validator` | RESOLVED — handled as new helper in schema_validator.py |
| R2 | `@context` form — confirmed as plain string URL `"https://spdx.org/rdf/3.0.1/spdx-context.jsonld"` | RESOLVED |
| R3 | `suppliedBy`/`createdBy` cross-reference resolution — two-pass graph index required; missing refs produce `None` gracefully | RESOLVED — per ADR-010 |
| R4 | SPDX 3.x field names — must be confirmed against schema and spec before parser implementation | OPEN — tester/developer must read schema before authoring fixtures |
| R5 | Multiple `SpdxDocument` elements in `@graph` — take first, log WARNING | RESOLVED — per ADR-010 |

---

## Task Breakdown

| ID | Task | Agent | Branch | Dependencies | Status | Deliverables | Acceptance Criteria |
|----|------|-------|--------|--------------|--------|--------------|---------------------|
| 0.A1 | Create feature branch `feature/spdx3-jsonld` from `develop` | Developer | `feature/spdx3-jsonld` | None | ✅ | Branch exists locally | `git branch` shows `feature/spdx3-jsonld` |
| 0.A2 | Create `docs/releases/TASKS-v0.6.0.md` | Developer | `feature/spdx3-jsonld` | 0.A1 | ✅ | This file | File exists and all task IDs are listed |
| 1.B1 | Write ADR-010, amend ADR-001, add FR-15 to requirements.md | Architect | `feature/spdx3-jsonld` | 0.A2 | ✅ | `docs/architecture/ADR-010-spdx3-jsonld-support.md`, ADR-001 amendment, `docs/requirements.md` FR-15 | ADR committed; all interface stubs, resolution contracts, and detection fingerprint documented |
| 2.C1 | Write failing tests for new SPDX 3.x constants | Tester | `feature/spdx3-jsonld` | 1.B1 | ✅ | `tests/unit/test_constants_spdx3.py` | 7/7 tests pass; ruff+mypy clean |
| 2.C2 | Implement new constants in `constants.py` | Developer | `feature/spdx3-jsonld` | 2.C1 | ✅ | `src/sbom_validator/constants.py` updated | 7/7 tests pass; ruff+mypy clean |
| 2.C3 | Bundle SPDX 3.0.1 JSON Schema | Developer | `feature/spdx3-jsonld` | 1.B1 | ✅ | `src/sbom_validator/schemas/spdx-3.0.1.schema.json` | File is valid JSON; committed in b8c9da8 |
| 3.D1 | Write failing tests for SPDX 3.x format detection | Tester | `feature/spdx3-jsonld` | 2.C2 | ✅ | New class `TestDetectFormatSPDX3JsonLD` in `tests/unit/test_format_detector.py`; `tests/fixtures/spdx/valid-minimal.spdx3.jsonld` | 2 tests correctly failing; 42 existing pass; ruff+mypy clean |
| 3.D2 | Implement SPDX 3.x detection branch in `format_detector.py` | Developer | `feature/spdx3-jsonld` | 3.D1 | ✅ | `src/sbom_validator/format_detector.py` updated | `test_format_detector.py` all pass; ruff+mypy pass |
| 3.E1 | Write failing tests for SPDX 3.x schema validation | Tester | `feature/spdx3-jsonld` | 2.C2, 2.C3 | ✅ | New class `TestValidateSchemaSPDX3JsonLD` in `tests/unit/test_schema_validator.py`; `tests/fixtures/spdx/invalid-schema.spdx3.jsonld` | 9 tests correctly failing (ValueError); 30 existing pass; ruff+mypy clean |
| 3.E2 | Extend `schema_validator.py` to handle `spdx3-jsonld` | Developer | `feature/spdx3-jsonld` | 3.E1 | ✅ | `src/sbom_validator/schema_validator.py` updated (new `_validate_json_schema_2020()` helper) | `test_schema_validator.py` all pass; ruff+mypy pass |
| 3.F1 | Write failing tests for the SPDX 3.x JSON-LD parser | Tester | `feature/spdx3-jsonld` | 2.C2 | ✅ | `tests/unit/test_spdx3_jsonld_parser.py` (44 tests, 5 classes); fixtures: `valid-full.spdx3.jsonld`, `missing-supplier.spdx3.jsonld`, `missing-relationships.spdx3.jsonld` | All 44 tests fail with ImportError; ruff+mypy clean |
| 3.F2 | Implement `parse_spdx3_jsonld()` in new parser module | Developer | `feature/spdx3-jsonld` | 3.F1 | ✅ | `src/sbom_validator/parsers/spdx3_jsonld_parser.py` | `test_spdx3_jsonld_parser.py` all pass; ruff+mypy pass |
| 3.G1 | Write failing integration tests for SPDX 3.x end-to-end pipeline | Tester | `feature/spdx3-jsonld` | 3.D2, 3.E2, 3.F2 | ✅ | New class in `tests/unit/test_validator.py`; `tests/integration/test_cli_spdx3.py` | Tests fail; ruff+mypy pass |
| 3.G2 | Wire SPDX 3.x into `validator.py` pipeline | Developer | `feature/spdx3-jsonld` | 3.G1 | ✅ | `src/sbom_validator/validator.py` updated (`_SPDX_FORMATS`, dispatch branch) | All pipeline tests pass; ruff+mypy pass |
| 3.H1 | Run full test suite; verify coverage >= 90% | Developer | `feature/spdx3-jsonld` | 3.G2 | ✅ | Clean pytest run output | 0 failures; coverage >= 90%; ruff+mypy clean |
| 4.I1 | Independent code review | Reviewer | `feature/spdx3-jsonld` | 3.H1 | ✅ | Review findings and verdict | No open CRITICAL/MAJOR (or approved deferrals recorded) |
| 4.J1 | Security/compliance review | Security Reviewer | `feature/spdx3-jsonld` | 3.H1 | ✅ | Security findings and verdict | Verdict APPROVED/CONDITIONAL; no runtime network calls; graceful malformed input handling confirmed |
| 4.K1 | CI stabilization | CI Ops | `feature/spdx3-jsonld` | 4.I1, 4.J1 | ✅ | CI stabilization report | All required CI checks green |
| 5.L1 | Update README, CHANGELOG, agent-briefing.md | Documentation Writer | `feature/spdx3-jsonld` | 4.K1 | ✅ | Updated `README.md`, `CHANGELOG.md`, `docs/agent-briefing.md` | SPDX 3.x listed in supported formats table; `[0.6.0]` changelog entry present; briefing updated with new format constant and function |
| 6.M1 | Version bump to 0.6.0 and release brief | Release Manager | `feature/spdx3-jsonld` | 5.L1 | ✅ | `pyproject.toml` at `0.6.0`; release brief in tracker | Version consistent; all gate evidence sections populated |
| 7.N1 | Generate `docs/releases/token-report-v0.6.0.html` | Token Analyst | `feature/spdx3-jsonld` | 6.M1 | ✅ | `docs/releases/token-report-v0.6.0.html` | Report generated with per-agent token breakdown |
| 7.N2 | Generate `docs/releases/token-delta-v0.5.0_to_v0.6.0.html` | Token Analyst | `feature/spdx3-jsonld` | 7.N1 | ✅ | `docs/releases/token-delta-v0.5.0_to_v0.6.0.html` | Delta vs v0.5.0 generated |
| 7.O1 | Generate `docs/releases/workflow-report-v0.6.0.html` | Workflow Analyst | `feature/spdx3-jsonld` | 7.N1 | ✅ | `docs/releases/workflow-report-v0.6.0.html` | Per-agent efficiency and gate compliance benchmarked against v0.5.0 |
| 8.P1 | Push branch and open PR to `develop` | Developer | `feature/spdx3-jsonld` → `develop` | 7.N2, 7.O1 | 🔄 | PR open on GitHub | CI green on PR; all gate evidence linked in PR description |

---

## Gate Evidence

### G0 Intake
- Evidence:
- Status: ⏳ PENDING

### G1 Planning
- Evidence: Planner and Architect agents evaluated the feature (2026-04-29). Full task breakdown produced. All pre-implementation decisions settled (schema source, context URL, cross-reference contract, ADR vehicle). See feature evaluation session.
- Status: ✅ PASS

### G2 Architecture
- Evidence: ADR-010 written (`docs/architecture/ADR-010-spdx3-jsonld-support.md`). ADR-001 amended with new detection priority order. FR-15 added to `docs/requirements.md`. All interface stubs, resolution contracts, detection fingerprint, and NTIA field mapping documented. FR-11 collision resolved (FR-11 is Structured JSON Output Mode; SPDX 3.x requirement is FR-15).
- Status: ✅ PASS

### G3 TDD Build
- Evidence: All three parallel tracks complete. Constants (2.C1/2.C2): 7/7 passing. Schema bundle (2.C3): committed. Detection (3.D1/3.D2): 50/50 passing. Schema validator (3.E1/3.E2): 39/39 passing. Parser (3.F1/3.F2): 44/44 passing. Pipeline wiring (3.G1/3.G2): 15 unit + 3 integration tests passing. 3.H1: 701/701 total, 96.11% coverage, ruff+mypy clean.
- Status: ✅ PASS

### G4 Quality Review
- Evidence: Reviewer agent dispatched post-3.H1. Verdict: **CONDITIONAL** — 0 critical, 2 major, 3 minor, 3 info. M-01: envelope schema deviates from ADR-010 (Architect must formally amend ADR-010); M-02: dead `_SPDX3_SCHEMA_FILE` constant in `schema_validator.py`. All mandatory findings addressed: M-02 constant removed; `detect_format()` docstring updated to list `spdx3-jsonld`; ADR-010 amendment dispatched (see Deferrals D2).
- Status: ✅ PASS (mandatory fixes applied)

### G5 Security
- Evidence: Security Reviewer agent dispatched post-3.H1. Verdict: **CONDITIONAL** — mandatory pre-merge: S-M-01 (formal deferral for envelope schema; see Deferrals D2), S-M-02 (`registry=Registry()` added to `Draft202012Validator`), S-m-02/03 (`isinstance` guards added in parser for `@graph` non-list and non-dict elements), S-m-04 (class docstring mismatch fixed in `test_spdx3_jsonld_parser.py`). All mandatory items addressed.
- Status: ✅ PASS (mandatory fixes applied)

### G6 CI Stability
- Evidence: 20 DeprecationWarnings from CycloneDX schema remote-ref fetching eliminated. Root cause: `spdx.schema.json` and `jsf-0.82.schema.json` referenced by CycloneDX schemas but not bundled. Fix: both files downloaded and committed to `src/sbom_validator/schemas/`; `_build_cdx_registry()` added to `schema_validator.py` to pre-register them in a `referencing.Registry` passed to `Draft7Validator`. 0 warnings remain.
- Status: ✅ PASS

### G7 Docs Sync
- Evidence: README.md Supported Formats table updated with SPDX 3.0.1 JSON-LD row. CHANGELOG.md `[0.6.0]` entry added. `docs/agent-briefing.md` updated with ADR-010, `parse_spdx3_jsonld()` signature, updated detect_format() return values, updated NTIA field mapping table, updated NormalizedSBOM.format values.
- Status: ✅ PASS

### G8 Release Readiness
- Evidence: `pyproject.toml` version 0.5.0 → 0.6.0. `src/sbom_validator/__init__.py` `__version__` updated. CHANGELOG `[0.6.0]` entry present. All gate evidence populated in this tracker.
- Status: ✅ PASS

### G9 Token Analytics
- Evidence: `docs/releases/token-report-v0.6.0.html` generated. Total estimated: ~600,000 tokens (2.0× v0.5.0, proportionate to scope: new format stack, 19 agent dispatches, 107 new tests). Top optimization: add jsonschema API checklist and schema-deviation documentation requirement to ADR template.
- Status: ✅ PASS

### G10 Workflow Evaluation
- Evidence: `docs/releases/workflow-report-v0.6.0.html` generated. Verdict: NEEDS ATTENTION. All 11 gates executed. Key gap: developer deviated from ADR-010 (envelope schema) without pre-commit Architect consultation — generated avoidable G4 M-01 retroactive amendment. Notable improvement vs v0.5.0: zero documentation gaps at G4 (v0.5.0 F-02/F-03/F-04 pattern did not recur).
- Status: ✅ PASS

---

## Deferrals (if any)

| ID | Description | Severity | Deferral Reason | Planned Release |
|----|-------------|----------|-----------------|-----------------|
| D1 | SPDX 3.x Tag-Value, YAML, and XML serializations | LOW | Out of scope for this release; SPDX 3.x JSON-LD is the primary use case | v0.7.0 or later |
| D2 | Full SPDX 3.0.1 JSON Schema validation (envelope-only approach in use) | MEDIUM | The bundled `spdx-3.0.1.schema.json` (Draft 2020-12, shacl2code-generated) uses an `else: $ref AnyClass` branch that rejects minimal `{"@context": ...}` root documents — a valid SPDX 3.x JSON-LD pattern. The schema-validation stage validates only the document envelope (`@context` presence and value); element-level validation is deferred to the parser (two-pass graph traversal). **Risk acceptance:** schema-stage errors for invalid SPDX 3.x elements will surface as parse-stage `ERROR` rather than `FAIL+FR-15`. **Planned resolution:** either patch the bundled schema or implement a pre-processor that feeds the `@graph` elements individually to the full schema validator. Approved by G4 (M-01) and G5 (S-M-01); Architect must formally amend ADR-010 to document this deviation. |

---

## Final Verdict

- **Recommendation:** ✅ SHIP
- **Approved by (Human):** PR #20 reviewed with no findings; approved and merged to develop → master
- **Date:** 2026-04-30
- **Notes:** Tag v0.6.0 pushed. GitHub Release workflow triggered (run 25178451805). Standalone binaries (Linux + Windows amd64) will be produced by the CI release pipeline.

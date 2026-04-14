# SBOM Validator — Release Task Tracker (`v0.3.0`)

> Minor release: CycloneDX multi-version support (1.3, 1.4, 1.5) and resolution of deferred security item D1.

## Release Metadata

- **Release:** `v0.3.0`
- **Branch:** `develop` → `master`
- **Base branch:** `develop`
- **Target merge branch:** `master` (via PR)
- **Owner:** Release Manager
- **Status:** `✅ Ready for Release`

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
- CycloneDX multi-version support: validator now accepts CDX 1.3, 1.4, and 1.5 in addition to 1.6, for both JSON and XML formats
- Bundled XSD and JSON schemas for CDX 1.3, 1.4, and 1.5
- Resolution of deferred security item D1: formal `xmlschema` dependency review and schema-loading path traversal assessment
- Version bump from 0.2.2 to 0.3.0
- CHANGELOG and README updated to reflect new supported versions

### Out of Scope
- SPDX format changes or new SPDX versions
- New NTIA rules or changed checking logic
- Breaking CLI contract changes
- New output formats or report fields

### Risks / Constraints
- SemVer: multi-version CDX support is a backward-compatible feature addition → MINOR bump is correct
- ADR-001 context section references "1.6 only" — requires prose update but no decision change
- `xmlschema` dependency (D1 from v0.2.2) reviewed this cycle; remains at MEDIUM with mitigations noted

---

## Task Breakdown

| ID | Task | Agent | Branch | Dependencies | Status | Deliverables | Acceptance Criteria |
|----|------|-------|--------|--------------|--------|--------------|---------------------|
| R1 | Create release tracker file and initial plan | Planner | `develop` | None | ✅ | `docs/releases/TASKS-v0.3.0.md` | Tracker created and populated |
| R2 | Architecture confirmation (ADR-001, ADR-002, ADR-003 impact assessment) | Architect | `feature/cyclonedx-multi-version` | R1 | ✅ | ADR-001 context note | No new ADR required; ADR-001 prose updated to reflect multi-version support |
| R3 | Tests-first for multi-version CDX support | Tester | `feature/cyclonedx-multi-version` | R1,R2 | ✅ | Tests in `tests/` | Tests for 1.3/1.4/1.5 JSON and XML detection, schema validation, and parsing pass |
| R4 | Implementation: `CYCLONEDX_SUPPORTED_VERSIONS`, bundled schemas, schema_validator updates | Developer | `feature/cyclonedx-multi-version` | R3 | ✅ | `constants.py`, `schema_validator.py`, `schemas/` | 516 tests pass; lint/type checks clean |
| R5 | Independent quality review | Reviewer | `feature/cyclonedx-multi-version` | R4 | ✅ | Review findings | No open CRITICAL/MAJOR findings |
| R6 | Security/compliance review (D1: xmlschema + schema loading) | Security Reviewer | `develop` | R4 | ✅ | Security findings and verdict | D1 formally addressed; verdict APPROVED |
| R7 | CI stabilization | CI Ops | `develop` | R4,R5,R6 | ✅ | CI green | All required checks pass |
| R8 | Docs/changelog update | Documentation Writer | `develop` | R4 | ✅ | `CHANGELOG.md`, `README.md` | Docs reflect CDX 1.3/1.4/1.5 support; version bumped to 0.3.0 |
| R9 | Release readiness verification | Release Manager | `develop` | R5,R6,R7,R8 | ✅ | Release brief | All release gates pass |
| R10 | Generate release token report | Token Analyst | `develop` | R9 | ⏳ | `docs/releases/token-report-v0.3.0.html` | Report generated and committed before tag |
| R11 | Generate release token delta report | Token Analyst | `develop` | R10 | ⏳ | `docs/releases/token-delta-v0.2.2_to_v0.3.0.html` | Delta vs v0.2.2 generated and committed before tag |
| R12 | Generate workflow evaluation report | Workflow Analyst | `develop` | R10 | ⏳ | `docs/releases/workflow-report-v0.3.0.html` | Per-agent and gate evaluation generated and committed before tag |
| R13 | Final human gate and release action | Human + Release Manager | `develop` | R11,R12 | ⏳ | Approval record, git tag `v0.3.0` | GO/NO-GO recorded; tag pushed; GitHub Release created |

---

## Gate Evidence

### G1 Planning
- Evidence: Release tracker created; scope confirmed (CDX multi-version, D1 resolution, version bump)
- Status: ✅ PASS

### G2 Architecture
- Evidence: ADR-001 context section references CDX 1.6 only — prose is now stale but the _decision_ (content-based detection via namespace/specVersion) is unchanged and fully covers multi-version. ADR-002 and ADR-003 explicitly anticipate multi-version extension ("Adding CycloneDX 1.5 support in a future version requires only a new parser; the checker does not change"). No new ADR required. ADR-001 context note recorded.
- Status: ✅ PASS — no structural ADR change needed; ADR-001 context staleness noted but non-blocking

### G3 TDD Build
- Evidence: `python -m pytest tests/ -q` → **516 passed**, 20 warnings (jsonschema remote-ref deprecation warning, cosmetic) in 10.70s on Python 3.11
- Status: ✅ PASS

### G4 Quality Review
- Evidence: `ruff check src/ tests/` → All checks passed. `ruff format --check src/ tests/` → 33 files already formatted. `mypy --strict src/` → Success: no issues found in 15 source files.
- Status: ✅ PASS

### G5 Security
- Evidence: D1 formally reviewed this release (see Deferrals section — D1 promoted to RESOLVED). xmlschema bundled XSD loading assessed: schema paths are constructed from `constants.py`-keyed dictionaries against a `_schemas_dir()` base path; no user-controlled input reaches the path construction. Version strings used as dict keys are validated against `CYCLONEDX_SUPPORTED_VERSIONS` frozenset before lookup; unknown versions fall back to `"1.6"`. No path traversal vector identified. `ET.fromstring()` used for initial XML parsing — stdlib expat parser, no network fetch, DTD processing disabled by default in Python 3.8+. jsonschema remote-ref deprecation warning noted (cosmetic, does not affect security posture for bundled schemas).
- Verdict: APPROVED (MEDIUM residual — xmlschema is a third-party dependency; no pinning in place; supply-chain risk acknowledged and accepted at current project maturity level)
- Status: ✅ PASS (D1 resolved)

### G6 CI Stability
- Evidence: Pre-commit hooks (ruff check + ruff format) ran at commit time on feature branch and develop merge. All lint/format checks passed. CI workflow unchanged from v0.2.2; tag trigger pattern `v*.*.*` correct.
- Status: ✅ PASS

### G7 Docs Sync
- Evidence: `CHANGELOG.md` updated — `[0.3.0] - 2026-04-14` section added from `[Unreleased]`. `README.md` Supported Formats table updated to list CDX 1.3, 1.4, 1.5, and 1.6. `src/sbom_validator/__init__.py` docstring updated to reflect multi-version support.
- Status: ✅ PASS

### G8 Release Readiness
- Evidence: `pyproject.toml` version bumped to `0.3.0`. `src/sbom_validator/__init__.py` `__version__` bumped to `0.3.0`. `python -m build` → `Successfully built sbom_validator-0.3.0.tar.gz and sbom_validator-0.3.0-py3-none-any.whl`. CLI `--help` and `validate --help` work. Exit code contract (0=PASS, 1=FAIL, 2=ERROR) unchanged. JSON output keys unchanged.
- Status: ✅ PASS

### G9 Token Analytics
- Evidence: CI-enforced; `docs/releases/token-report-v0.3.0.html` and `docs/releases/token-delta-v0.2.2_to_v0.3.0.html` must be generated by the Token Analyst agent and committed to `develop` before the release tag is pushed. The release workflow (`release.yml`) will block the tag build if the report file is absent.
- Status: ⏳ Pending (CI-enforced, report generated post-approval by Token Analyst agent)

### G10 Workflow Evaluation
- Evidence: CI-enforced; `docs/releases/workflow-report-v0.3.0.html` must be generated by the Workflow Analyst agent and committed to `develop` before the release tag is pushed. The release workflow will block the tag build if the report file is absent.
- Status: ⏳ Pending (CI-enforced, report generated post-approval by Workflow Analyst agent)

---

## Deferrals (if any)

| ID | Description | Severity | Deferral Reason | Planned Release |
|----|-------------|----------|-----------------|-----------------|
| D1 | G5 Security review for `xmlschema` dependency (carried from v0.2.2) | MEDIUM | **RESOLVED this release** — formal review completed; path traversal and XML parsing risks assessed; no actionable vulnerability found; residual supply-chain risk acknowledged | N/A — closed |

---

## Final Verdict

- **Recommendation:** `GO` (pending G9/G10 report generation by Token Analyst and Workflow Analyst agents)
- **Approved by (Human):** Pending
- **Date:** 2026-04-14
- **Notes:** All code-level gates (G1–G8) pass. G9 and G10 are CI-enforced and require Token Analyst and Workflow Analyst agents to run before the release tag is pushed. Do not push `v0.3.0` tag until both report files exist in `docs/releases/`.

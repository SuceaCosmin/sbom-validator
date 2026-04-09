# SBOM Validator — Release Task Tracker (`v0.2.1`)

> Canonical execution tracker for CycloneDX XML support.

## Release Metadata

- **Release:** `v0.2.1`
- **Branch:** `feature/cdx-xml-support`
- **Base branch:** `develop`
- **Target merge branch:** `develop` (then `master` per release flow)
- **Owner:** Release Manager / Orchestrator
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
- Add CycloneDX 1.6 XML detection support.
- Add strict CycloneDX XML schema validation in Stage 1.
- Add CycloneDX XML parsing to `NormalizedSBOM`.
- Add XML fixture/test parity for validator, CLI, and integration flows.
- Update docs and architecture notes for CycloneDX XML support.

### Out of Scope
- SPDX XML support.
- CycloneDX versions other than 1.6.
- Relaxing existing exit code and output contracts.

### Risks / Constraints
- XML schema validation must remain strict and deterministic.
- Existing JSON behavior must not regress.
- Runtime contract for `format_detected` remains stable (`cyclonedx`).

---

## Task Breakdown

| ID | Task | Agent | Branch | Dependencies | Status | Deliverables | Acceptance Criteria |
|----|------|-------|--------|--------------|--------|--------------|---------------------|
| R1 | Create release tracker and initial plan | Planner | `feature/cdx-xml-support` | None | ✅ | `docs/releases/TASKS-v0.2.1.md` | Tracker exists and is populated |
| R2 | XML detection + tests | Developer + Tester | `feature/cdx-xml-support` | R1 | ✅ | `format_detector.py`, `test_format_detector.py` | CDX XML 1.6 detected, unsupported versions rejected |
| R3 | XML schema validation + tests | Developer + Tester | `feature/cdx-xml-support` | R2 | ✅ | `schema_validator.py`, schema assets, schema tests | Stage 1 strict XML schema checks enforced |
| R4 | XML parser path + tests | Developer + Tester | `feature/cdx-xml-support` | R3 | ✅ | CycloneDX parser/tests | XML normalized to existing model correctly |
| R5 | Validator/CLI/integration parity | Developer + Tester | `feature/cdx-xml-support` | R4 | ✅ | validator/cli/integration tests + fixtures | PASS/FAIL/ERROR parity with JSON behavior |
| R6 | Docs + ADR updates | Documentation Writer + Architect | `feature/cdx-xml-support` | R5 | ✅ | README/requirements/ADR/architecture docs | User-facing and architecture docs aligned |
| R7 | Quality gates and release prep | Reviewer + Release Manager | `feature/cdx-xml-support` | R6 | ✅ | test/lint/type evidence + release brief | All gates pass; release readiness verified |

---

## Gate Evidence

### G1 Planning
- Evidence: this tracker + approved implementation plan
- Status: ✅

### G2 Architecture
- Evidence: ADR and architecture overview updated for CycloneDX 1.6 XML detection/parsing flow.
- Status: ✅

### G3 TDD Build
- Evidence: unit tests updated for detector/schema/parser/validator with `.cdx.xml` parity.
- Status: ✅

### G4 Quality Review
- Evidence: `ruff check .` and `black --check .` passed.
- Status: ✅

### G5 Security
- Evidence: No formal security review executed. `xmlschema` dependency added without security gate. Formally deferred — see Deferrals table.
- Status: ⚠️ Deferred to v0.3.x

### G6 CI Stability
- Evidence: full local `pytest` run passed (501 tests); 3 CI failure cycles resolved (ruff import sort + black formatting).
- Status: ✅

### G7 Docs Sync
- Evidence: `README.md`, `docs/requirements.md`, ADR-001, architecture overview updated.
- Status: ✅

### G8 Release Readiness
- Evidence: all workpackage todos complete; schema assets bundled for runtime.
- Status: ✅

### G9 Token Analytics
- Evidence: `docs/releases/token-report-v0.2.1.html` and `docs/releases/token-delta-v0.2.0_to_v0.2.1.html` generated post-release. All metrics are estimates (no direct telemetry). See reports for optimization recommendations.
- Status: ✅ (post-release — process gap noted; see workflow fix)

---

## Deferrals (if any)

| ID | Description | Severity | Deferral Reason | Planned Release |
|----|-------------|----------|-----------------|-----------------|
| D1 | G5 Security review for `xmlschema` dependency | MEDIUM | Gate was skipped in this release cycle; no security issues found in manual spot-check but formal review not performed | v0.3.x |
| D2 | G9 Token Analytics executed pre-release (not post) | LOW | Tooling/process not yet established to run token analyst before tag; reported retrospectively | v0.3.x |
| D3 | Pre-commit hooks (black + ruff) | MEDIUM | Would eliminate recurring CI lint/format failures; not yet added to repo | v0.3.x |

---

## Final Verdict

- **Recommendation:** `GO` ✅
- **Approved by (Human):** SuceaCosmin
- **Date:** 2026-04-09
- **Notes:** Released as v0.2.1. Three deferred items (D1–D3) to be addressed at start of v0.3.x. Tag pushed, GitHub Release artifacts published (Linux + Windows binaries with SHA256 checksums).

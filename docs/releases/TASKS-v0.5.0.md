# SBOM Validator — Release Task Tracker (v0.5.0)

> Canonical execution tracker for the v0.5.0 release cycle.

## Release Metadata

- **Release:** `v0.5.0`
- **Branch:** `develop` (all work already merged; releasing existing commits)
- **Base branch:** `master` (v0.4.0)
- **Target merge branch:** `master` (via PR from `develop`)
- **Owner:** Release Manager / Orchestrator
- **Status:** `🔄 In Progress`

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
- Bug fix: Remove PURL/CPE false-positive NTIA check (FR-07 removed); `DEPENDENCY_OF` relationships now recognized (issues #11, #12)
- Feature: Validation issues classified by category — schema / NTIA / format (issue #13)
- Feature: Report improvements — stable filenames (no timestamp suffix), `tool_version` field in JSON output, version in startup log (issues #14, #15)
- Chore/process: Agent model updates, SBOM generation in CI pipeline
- Version bump: 0.4.0 -> 0.5.0
- Changelog: `[Unreleased]` section promoted to `[0.5.0]`

### Out of Scope
- New format support
- New NTIA checks
- Architecture changes (no new modules, no signature changes beyond what's already merged)

### Risks / Constraints
- FR-07 removal is a behavioral change (less strict): needs backward compat verification
- Issue category classification adds a new field to ValidationIssue — must verify JSON output keys are stable
- All code already merged to `develop`; gate pipeline is verification-only

---

## Task Breakdown

| ID | Task | Agent | Branch | Dependencies | Status | Deliverables | Acceptance Criteria |
|----|------|-------|--------|--------------|--------|--------------|---------------------|
| R1 | Create release tracker file and initial plan | Orchestrator | `develop` | None | ✅ | `docs/releases/TASKS-v0.5.0.md` | Tracker created and populated |
| R2 | Architecture confirmation (ADR impact/no-impact) | Architect | `develop` | R1 | ✅ | ADR note | Architecture decision recorded |
| R3 | Quality build — full test suite + static analysis | Tester | `develop` | R1,R2 | ✅ | Test output, lint/type results | All tests pass, coverage >= 90%, zero mypy/ruff errors |
| R4 | Independent quality review | Reviewer | `develop` | R3 | ⏳ | Review findings and verdict | No open CRITICAL/MAJOR (or approved deferrals) |
| R5 | Security/compliance review | Security Reviewer | `develop` | R3 | ⏳ | Security findings and verdict | Verdict APPROVED/CONDITIONAL with rationale |
| R6 | CI stabilization | CI Ops | `develop` | R3,R4,R5 | ⏳ | CI report | Required checks green |
| R7 | Docs/changelog update + version bump | Documentation Writer | `develop` | R3 | ⏳ | `README.md`, `CHANGELOG.md`, `pyproject.toml`, `__init__.py` | Version 0.5.0 everywhere, changelog promoted |
| R8 | Release readiness verification | Release Manager | `develop` | R4,R5,R6,R7 | ⏳ | Release brief | All release gates pass |
| R9 | Generate release token report | Token Analyst | `develop` | R8 | ⏳ | `docs/releases/token-report-v0.5.0.html` | Report generated |
| R10 | Generate release token delta report | Token Analyst | `develop` | R9 | ⏳ | `docs/releases/token-delta-v0.4.0_to_v0.5.0.html` | Delta vs v0.4.0 generated |
| R11 | Generate workflow evaluation report | Workflow Analyst | `develop` | R9 | ⏳ | `docs/releases/workflow-report-v0.5.0.html` | Per-agent and gate evaluation generated |
| R12 | Final human gate and release action | Human + Release Manager | `develop`->`master` | R10,R11 | ⏳ | Approval record, git tag v0.5.0 | Human GO recorded; tag pushed |

---

## Gate Evidence

### G0 Intake
- Evidence: Scope defined in orchestrator prompt — 14 commits on `develop` ahead of `master` (v0.4.0). Bugs #11/#12 fixed, feature #13 (issue categories), features #14/#15 (report/logging improvements).
- Status: ✅ PASS (scope pre-defined, no clarification needed)

### G1 Planning
- Evidence: Task breakdown above. No new feature branch needed — work already merged. Gates G0/G1/G2 collapsed into tracker creation per orchestration instructions.
- Status: ✅ PASS

### G2 Architecture
- Evidence: No new modules introduced. No public function signatures changed (beyond what was already released). FR-07 removal was an intentional behavioral decision already applied in merged code. `category` field added to `ValidationIssue` — constitutes a data model change. Architect pass: ADR note — `category` field added to frozen dataclass `ValidationIssue` as additive non-breaking change; no new ADR required since it extends an existing model without altering any existing field contract. Agent briefing unchanged.
- Status: ✅ PASS (no ADR change required — additive model extension only)

### G3 TDD Build
- Evidence: ruff check PASS (0 errors, 37 files formatted), ruff format PASS, mypy PASS (0 issues in 17 source files), pytest 613/613 PASS, coverage 95.93% (threshold 90%). 20 deprecation warnings (jsonschema remote-ref, cosmetic only).
- Status: ✅ PASS

### G4 Quality Review
- Evidence:
- Status: ⏳

### G5 Security
- Evidence:
- Status: ⏳

### G6 CI Stability
- Evidence:
- Status: ⏳

### G7 Docs Sync
- Evidence:
- Status: ⏳

### G8 Release Readiness
- Evidence:
- Status: ⏳

### G9 Token Analytics
- Evidence:
- Status: ⏳

### G10 Workflow Evaluation
- Evidence:
- Status: ⏳

---

## Deferrals (if any)

| ID | Description | Severity | Deferral Reason | Planned Release |
|----|-------------|----------|-----------------|-----------------|

---

## Final Verdict

- **Recommendation:** (pending)
- **Approved by (Human):**
- **Date:**
- **Notes:**

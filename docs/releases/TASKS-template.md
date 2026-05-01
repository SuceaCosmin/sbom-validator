# SBOM Validator — Release Task Tracker (`vX.Y.Z`)

> Copy this file to `docs/releases/TASKS-vX.Y.Z.md` when planning a new release.
> This is the canonical execution tracker for that release.

## Release Metadata

- **Release:** `vX.Y.Z`
- **Branch:** `feature/<release-scope>` (or release branch policy in effect)
- **Base branch:** `develop`
- **Target merge branch:** `develop` (then `master` per release flow)
- **Owner:** Release Manager / Orchestrator
- **Status:** `⏳ Planning` / `🔄 In Progress` / `✅ Ready for Release` / `❌ Blocked`

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
- 

### Out of Scope
- 

### Risks / Constraints
- 

---

## Task Breakdown

| ID | Task | Agent | Branch | Dependencies | Status | Deliverables | Acceptance Criteria |
|----|------|-------|--------|--------------|--------|--------------|---------------------|
| R1 | Create release tracker file and initial plan | Planner | `feature/<name>` | None | ✅ | `docs/releases/TASKS-vX.Y.Z.md` | Tracker created and populated |
| R2 | Architecture confirmation (ADR impact/no-impact) | Architect | `feature/<name>` | R1 | ⏳ | ADR update or note | Architecture decision recorded |
| R3 | Tests-first updates for release scope | Tester | `feature/<name>` | R1,R2 | ⏳ | Tests in `tests/` | Failing tests capture intended behavior |
| R4 | Implementation changes | Developer | `feature/<name>` | R3 | ⏳ | Code changes in `src/` | Tests pass; lint/type checks pass |
| R5 | Independent quality review | Reviewer | `feature/<name>` | R4 | ⏳ | Review findings and verdict | No open CRITICAL/MAJOR (or approved deferrals) |
| R6 | Security/compliance review | Security Reviewer | `feature/<name>` | R4 | ⏳ | Security findings and verdict | Verdict APPROVED/CONDITIONAL with rationale |
| R7 | CI stabilization | CI Ops | `feature/<name>` | R4,R5,R6 | ⏳ | CI report | Required checks green |
| R8 | Docs/changelog update | Documentation Writer | `feature/<name>` | R4 | ⏳ | `README.md`, `CHANGELOG.md`, docs | Docs align with behavior/version |
| R9 | Release readiness verification | Release Manager | `feature/<name>` | R5,R6,R7,R8 | ⏳ | Release brief | All release gates pass |
| R10 | Generate release token report | Token Analyst | `feature/<name>` | R9 | ⏳ | `docs/releases/token-report-vX.Y.Z.html` | Report generated and linked in release brief |
| R11 | Generate release token delta report | Token Analyst | `feature/<name>` | R10 | ⏳ | `docs/releases/token-delta-vA.B.C_to_vX.Y.Z.html` | Delta generated (or N/A rationale documented) |
| R12 | Generate workflow evaluation report | Workflow Analyst | `feature/<name>` | R10 | ⏳ | `docs/releases/workflow-report-vX.Y.Z.html` | Per-agent and gate evaluation generated and linked |
| R13 | Release closeout — update meta-documents | Documentation Writer | `feature/<name>` | R9 | ⏳ | Updated CLAUDE.md, agent-briefing.md Quick-Start, requirements.md header, models.py docstrings | All drift-prone reference documents reflect the released version |
| R14 | Final human gate and release action | Human + Release Manager | `feature/<name>` | R11,R12,R13 | ⏳ | Approval record | GO/NO-GO recorded |

---

## Gate Evidence

### G1 Planning
- Evidence:
- Status:

### G2 Architecture
- Evidence:
- Status:

### G3 TDD Build
- Evidence:
- Status:

### G4 Quality Review
- Evidence:
- Status:

### G5 Security
- Evidence:
- Status:

### G6 CI Stability
- Evidence:
- Status:

### G7 Docs Sync
- Evidence:
- Status:

### G8 Release Readiness
- Evidence:
- Status:

### G9 Token Analytics
- Evidence:
- Status:

### G10 Workflow Evaluation
- Evidence:
- Status:

---

## Deferrals (if any)

| ID | Description | Severity | Deferral Reason | Planned Release |
|----|-------------|----------|-----------------|-----------------|

---

## Final Verdict

- **Recommendation:** `GO` / `NO-GO`
- **Approved by (Human):**
- **Date:**
- **Notes:**

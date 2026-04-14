# Agent Operating Model — sbom-validator

This document defines how the agent team executes work from idea to release in a human-in-the-loop model.

Goal: maximize automation while preserving quality, backward compatibility, and release safety.

---

## 1) Operating Principles

- Human provides intent, priorities, and final approval.
- Agents execute planning, implementation, testing, review, stabilization, and release prep.
- Work proceeds through explicit quality gates in fixed order.
- Backward compatibility for CLI and machine-consumed outputs is a hard requirement unless explicitly approved otherwise.
- Escalations should be rare, concise, and decision-oriented.
- Every release in flight must have a dedicated release tracker file at `docs/releases/TASKS-vX.Y.Z.md`.

---

## 2) Agent Roles and When They Are Invoked

| Agent | Primary Responsibility | Invoke When |
|------|--------------------------|-------------|
| `orchestrator` | End-to-end coordination and gate enforcement | Always, as the top-level driver |
| `planner` | Task decomposition, dependencies, branch plan, risk map | At start of each feature/phase |
| `architect` | ADR decisions, interface contracts, design trade-offs | Public behavior/interface/data model changes, or architectural uncertainty |
| `tester` | Tests-first authoring, integration and regression coverage | Before implementation and during regression expansion |
| `developer` | Implementation and bug fixes | After tests are defined and accepted |
| `reviewer` | Correctness, architecture adherence, code quality verdict | After implementation reaches green locally |
| `security-reviewer` | Security/compliance/supply-chain gate | Before CI-final stabilization and release recommendation |
| `ci-ops` | CI failure triage, safe auto-fixes, rerun loops | On any failing CI check |
| `documentation-writer` | User-facing docs/changelog updates | Any feature affecting behavior, usage, or release notes |
| `token-analyst` | Token usage evaluation and release-to-release delta reporting | After release readiness evidence is available, before final release approval |
| `workflow-analyst` | Per-agent efficiency evaluation, gate compliance analysis, and release-over-release workflow benchmarking | After token analytics, before final release approval |
| `release-manager` | Release gates, versioning, artifact/release readiness | Once code/test/review/security gates pass |

---

## 3) Lifecycle Flow (Idea -> Release)

Use this sequence for every feature:

1. **Intake** (`orchestrator`)
   - Convert human idea into a feature brief with acceptance criteria.

2. **Planning** (`planner`)
   - Produce task graph, dependencies, branch strategy, and risks.
   - Create release tracker file: `docs/releases/TASKS-vX.Y.Z.md`.

3. **Architecture decision** (`architect`, conditional)
   - Confirm ADR impact or record "no ADR change needed."

4. **TDD execution** (`tester` -> `developer`)
   - Tester writes/updates tests first.
   - Developer implements until targeted tests pass.

5. **Independent quality review** (`reviewer`)
   - Validate requirements and architecture adherence.

6. **Security/compliance review** (`security-reviewer`)
   - Validate secure implementation and release-path integrity.

7. **CI stabilization** (`ci-ops`)
   - Triage and auto-fix safe failures; rerun until stable or escalation.

8. **Documentation sync** (`documentation-writer`)
   - Update docs/changelog for delivered behavior.

9. **Release readiness** (`release-manager`)
   - Validate version/changelog/packaging and compatibility gates.

10. **Token analytics reporting** (`token-analyst`)
   - Generate release token report and previous-release delta report.

11. **Workflow evaluation** (`workflow-analyst`)
   - Evaluate per-agent efficiency and gate compliance for the completed release cycle.
   - Generate `docs/releases/workflow-report-vX.Y.Z.html` benchmarked against previous release.

12. **Human final approval**
   - Approve or block release.

---

## 4) Human Approval Checkpoints

The human should only be required at these checkpoints:

| Checkpoint | Trigger | Decision Required |
|-----------|---------|-------------------|
| A. Scope/Trade-off approval | Planner or Architect identifies major trade-off or ambiguity | Choose direction and constraints |
| B. Escalation approval | A gate fails after retry budget or immediate-risk condition is hit | Approve recommended mitigation path |
| C. Final release approval | All automated gates pass and release brief is ready | GO / NO-GO for publish |

Everything else should be automated by agents.

---

## 5) Gate Ownership and Exit Criteria

| Gate | Owner | Exit Criteria |
|------|-------|---------------|
| G0 Intake | `orchestrator` | Feature brief and acceptance criteria are explicit |
| G1 Planning | `planner` | Task graph complete, dependencies clear, risks listed |
| G2 Architecture | `architect` | ADR updated or "no ADR change" justified |
| G3 TDD Build | `tester` + `developer` | Tests-first evidence and local green on targeted scope |
| G4 Quality Review | `reviewer` | No open CRITICAL/MAJOR (or approved deferrals) |
| G5 Security | `security-reviewer` | Security verdict APPROVED or justified CONDITIONAL |
| G6 CI Stability | `ci-ops` | Required checks green and stable |
| G7 Docs Sync | `documentation-writer` | Behavior docs/changelog/version references aligned |
| G8 Release Readiness | `release-manager` | Version consistency, packaging, compatibility gates pass |
| G9 Token Analytics | `token-analyst` | `token-report-vX.Y.Z.html` and delta report generated |
| G10 Workflow Evaluation | `workflow-analyst` | `workflow-report-vX.Y.Z.html` generated and benchmarked against previous release |

No gate skipping is allowed. Gates G5 (Security), G9 (Token Analytics), and G10 (Workflow Evaluation) must be completed **before** the release tag is pushed. If any cannot be completed, it must be formally recorded as a deferral in the release tracker with an explicit justification — silent omission is not acceptable.

---

## 6) Retry and Escalation Policy

- Default retry budget per failed gate: **2** attempts.
- If still failing, `orchestrator` escalates with:
  - concise failure summary
  - probable root cause
  - attempted fixes
  - 2-3 options with recommendation

Immediate escalation (no retries):
- suspected backward-compatibility break
- security-critical finding
- conflicting requirements/ADR contract

---

## 7) Backward Compatibility Policy (CLI Contracts)

Unless explicitly approved otherwise, preserve:

- command and option names/semantics
- exit code mapping (`0` PASS, `1` FAIL, `2` ERROR)
- JSON output keys and parseability
- stderr-only logging behavior for log output

Any intended breaking change must include:
- explicit justification
- migration notes
- versioning impact assessment (SemVer)

---

## 8) Branching and Merge Policy

- All feature work on `feature/<kebab-case-name>`
- Integrate to `develop` via PR after passing gates
- Release from `master` through approved release flow

No direct ad-hoc merges that bypass gate evidence.

---

## 9) Minimum Evidence Artifacts Per Feature

Each completed feature should produce:

- Planner task graph and risk list
- Test evidence (targeted + full where applicable)
- Reviewer findings summary and verdict
- Security findings summary and verdict
- CI stabilization report
- Docs/changelog update evidence
- Release brief with GO/NO-GO recommendation
- Release-specific task tracker (`docs/releases/TASKS-vX.Y.Z.md`) with final statuses

This evidence enables fast human quality gates without deep manual digging.

---

## 10) Suggested Day-to-Day Command Pattern

- Human supplies idea and constraints.
- `orchestrator` runs the lifecycle and reports gate outcomes.
- Human only responds at checkpoints A/B/C.

This keeps the workflow high-automation while retaining strong human control at meaningful risk boundaries.

# SBOM Validator — Release Task Tracker (v0.4.0)

> This is the canonical execution tracker for the v0.4.0 release.

## Release Metadata

- **Release:** `v0.4.0`
- **Branch:** `feature/spdx-tv-yaml` → `develop`
- **Base branch:** `develop`
- **Target merge branch:** `develop` (then `master` per release flow)
- **Owner:** Orchestrator
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
- SPDX Tag-Value (`.spdx`) format detection, schema-skip, and parsing to NormalizedSBOM
- SPDX YAML (`.spdx.yaml`) format detection, schema validation (via existing spdx-2.3.schema.json), and parsing
- New format constants: FORMAT_SPDX_TV = "spdx-tv", FORMAT_SPDX_YAML = "spdx-yaml"
- format_detected field surfaces sub-format string in ValidationResult
- pyyaml >= 6.0 runtime dependency
- Unit tests for both new parsers and extended format detector tests
- Updated README.md, CHANGELOG.md, and user-guide.md

### Out of Scope
- SPDX 2.2 or older TV/YAML support
- SPDX RDF format
- Multi-line Tag-Value continuation values
- PyInstaller spec update for pyyaml (deferred — pyyaml has no hidden imports)

### Risks / Constraints
- R1: yaml.safe_load must be used exclusively — security gate will verify
- R2: validate_schema() ValueError guard must be updated before TV/YAML branches added
- R3: NormalizedSBOM.format typed as str (not Literal) — new values "spdx-tv"/"spdx-yaml" are safe
- R4: Tag-Value multi-line values (continuation lines) — only single-line fields parsed; others ignored

---

## Task Breakdown

| ID | Task | Agent | Branch | Dependencies | Status | Deliverables | Acceptance Criteria |
|----|------|-------|--------|--------------|--------|--------------|---------------------|
| R1 | Create release tracker and branch | Planner/Orchestrator | `feature/spdx-tv-yaml` | None | ✅ | `docs/releases/TASKS-v0.4.0.md` | Tracker created; branch exists |
| R2 | Architecture — ADR-009 for SPDX multi-format | Architect | `feature/spdx-tv-yaml` | R1 | ✅ | `docs/architecture/ADR-009-spdx-multi-format.md` | ADR accepted; briefing updated |
| R3 | Write tests for TV parser, YAML parser, format detector extensions | Tester | `feature/spdx-tv-yaml` | R2 | ✅ | test_spdx_tv_parser.py, test_spdx_yaml_parser.py, extended test_format_detector.py | Failing tests capture intended behavior |
| R4 | Create TV and YAML fixture files | Developer | `feature/spdx-tv-yaml` | R2 | ✅ | spdx_valid.spdx, spdx_valid.spdx.yaml, spdx_ntia_fail.spdx, spdx_ntia_fail.spdx.yaml | Fixtures present and structurally correct |
| R5 | Implement constants, format_detector, schema_validator, refactored spdx_parser, spdx_yaml_parser, spdx_tv_parser, validator | Developer | `feature/spdx-tv-yaml` | R3, R4 | ✅ | constants.py, format_detector.py, schema_validator.py, spdx_parser.py, spdx_yaml_parser.py, spdx_tv_parser.py, validator.py, pyproject.toml | All new + existing tests pass; mypy + ruff clean |
| R6 | Independent quality review | Reviewer | `feature/spdx-tv-yaml` | R5 | ✅ | Review findings and verdict | No open CRITICAL/MAJOR |
| R7 | Security review | Security Reviewer | `feature/spdx-tv-yaml` | R5 | ✅ | Security findings and verdict | APPROVED/CONDITIONAL |
| R8 | CI stabilization | CI Ops | `feature/spdx-tv-yaml` | R5,R6,R7 | ✅ | CI report | All checks green |
| R9 | Documentation update | Documentation Writer | `feature/spdx-tv-yaml` | R5 | ✅ | README.md, CHANGELOG.md, user-guide.md | Docs align with new behavior |
| R10 | Release readiness verification | Release Manager | `feature/spdx-tv-yaml` | R6,R7,R8,R9 | ✅ | Release brief | Version consistency; all gates pass |
| R11 | Generate release token report | Token Analyst | `feature/spdx-tv-yaml` | R10 | ✅ | `docs/releases/token-report-v0.4.0.html` | Report generated |
| R12 | Generate release token delta report | Token Analyst | `feature/spdx-tv-yaml` | R11 | ✅ | `docs/releases/token-delta-v0.3.0_to_v0.4.0.html` | Delta report generated |
| R13 | Generate workflow evaluation report | Workflow Analyst | `feature/spdx-tv-yaml` | R11 | ✅ | `docs/releases/workflow-report-v0.4.0.html` | Workflow report generated |
| R14 | Final human gate and release action | Human + Release Manager | `develop` / `master` | R12,R13 | ⏳ | GO/NO-GO record | Human approves release |

---

## Parallelization Map

**Sequential (critical path):** R1 → R2 → R3 → R5 → R6+R7+R9 (parallel) → R8 → R10 → R11+R13 (parallel) → R12 → R14

**Parallel pairs:**
- R3 and R4 can run in parallel (tests and fixtures are independent files)
- R6, R7, R9 can all run in parallel after R5
- R11 and R13 can run in parallel after R10

---

## Gate Evidence

### G0 Intake
- Evidence: Feature brief with 11 acceptance criteria defined
- Status: ✅ PASS

### G1 Planning
- Evidence: TASKS-v0.4.0.md created; task graph with dependencies, parallelization map, and risk map
- Status: ✅ PASS

### G2 Architecture
- Evidence: ADR-009 authored
- Status: ✅ PASS

### G3 TDD Build
- Evidence: `python -m pytest tests/ -q` → **594 passed** (78 new tests); `ruff check src/ tests/` clean; `mypy --strict src/` clean. Committed in `3dc032d` ("feat: add SPDX Tag-Value and YAML format support (v0.4.0)").
- Status: ✅ PASS

### G4 Quality Review
- Evidence: No CRITICAL/MAJOR findings. 2 minor lint/mypy cycles resolved during implementation. ruff and mypy --strict both pass on final state.
- Status: ✅ PASS

### G5 Security
- Evidence: `yaml.safe_load` audited at all 3 call sites in `spdx_yaml_parser.py` and `format_detector.py`; no bare `yaml.load` present. No new network or file-write exposure introduced. Path construction for schema loading unchanged.
- Verdict: APPROVED
- Status: ✅ PASS

### G6 CI Stability
- Evidence: All pre-commit hooks (ruff check + ruff format) pass. Zero CI failure cycles. Committed in `3dc032d`.
- Status: ✅ PASS

### G7 Docs Sync
- Evidence: `README.md`, `CHANGELOG.md`, and `user-guide.md` updated to describe SPDX Tag-Value and YAML support. `__init__.py` docstring updated. Version bumped to `0.4.0`. Committed in `21d47b5` ("docs: update docs, changelog, and version for v0.4.0").
- Status: ✅ PASS

### G8 Release Readiness
- Evidence: `pyproject.toml` and `src/sbom_validator/__init__.py` both set to `0.4.0`. Exit code contract (0/1/2) and JSON output keys unchanged. PR #9 opened (`feature/spdx-tv-yaml` → `develop`).
- Status: ✅ PASS

### G9 Token Analytics
- Evidence: `docs/releases/token-report-v0.4.0.html` and `docs/releases/token-delta-v0.3.0_to_v0.4.0.html` generated by Token Analyst agent and committed in `d5c9233` ("docs: add v0.4.0 token analytics and workflow evaluation reports (G9, G10)").
- Status: ✅ PASS

### G10 Workflow Evaluation
- Evidence: `docs/releases/workflow-report-v0.4.0.html` generated by Workflow Analyst agent; verdict HEALTHY / IMPROVING. Committed in `d5c9233` ("docs: add v0.4.0 token analytics and workflow evaluation reports (G9, G10)").
- Status: ✅ PASS

---

## Deferrals (if any)

| ID | Description | Severity | Deferral Reason | Planned Release |
|----|-------------|----------|-----------------|-----------------|
| D1 | PyInstaller spec pyyaml entry | LOW | pyyaml has no hidden imports requiring explicit collect_submodules; pure Python wheel | v0.5.0 if binary issues observed |

---

## Final Verdict

- **Recommendation:** `GO` (pending human approval — R14)
- **Approved by (Human):** Pending
- **Date:**
- **Notes:** All agent gates (G0–G10) pass. 594/594 tests green. No backward-compatibility breaks. No security findings. Awaiting human merge approval and tag push.

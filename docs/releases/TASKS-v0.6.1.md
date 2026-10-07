# SBOM Validator — Release Task Tracker (v0.6.1)

> Canonical execution tracker for the v0.6.1 release cycle (patch: closes deferral R-12).

## Release Metadata

- **Release:** `v0.6.1` (SemVer PATCH — no Compatibility Contract change; **confirm at H1**)
- **Branch:** `feature/click-path-exists`
- **Base branch:** `develop`
- **Target merge branch:** `develop` (via PR), then `master` per `.agent-kb/runbooks/release.md`
- **Owner:** Orchestrator
- **Status:** `⏳ Planning` (H1 approved 2026-10-07; ready for G2)

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
- Close R-12: the `FILE` argument of `validate` (`src/sbom_validator/cli.py:94`) moves from `click.Path(exists=False)` to an `exists=True`-based path type.
- Human decision 1: keep structured ERROR behaviour. Missing file: exit 2, ERROR result as text or valid JSON on stdout, `--report-dir` reports still written. Plain `exists=True` would make Click abort before the command body (usage error on stderr, no JSON), so the design intercepts that failure and routes it into the existing ERROR path.
- Human decision 2: align docs: ADR-005 (Amendment + corrected text), CHANGELOG `[0.6.1]`, `docs/user-guide.md` troubleshooting, R-12 mentions in `docs/release-checklist-v0.1.0.md` and `TASKS.md`.
- Tests: JSON/text/`--report-dir` with a missing file, directory passed as FILE, preserve existing tests, smoke test 5; FR IDs referenced.
- Version bump 0.6.0 -> 0.6.1 (`pyproject.toml`, `src/sbom_validator/__init__.py`) and drift-prone docs closeout; analytics (G9/G10).

### Out of Scope
- Any change to option names, exit codes, JSON keys, stdout/stderr split, `--report-dir` file names.
- Other deferrals (R-04/R-05, R-08, R-09).
- Editing historical `docs/repo-review-report.html`, `docs/code-review-notes.md` (snapshots).

### Risks / Constraints

| ID | Risk | Mitigation | Status |
|----|------|------------|--------|
| K1 | Plain `exists=True` loses JSON/--report-dir on missing file (exit code 2 coincidentally preserved, stdout contract broken) | Intercepting path type/class designed at 1.B1; contract tests at 2.C1 | OPEN |
| K2 | Intercepting makes `exists=True` effectively behavior-neutral; value is semantic/documentation + single code path. Human should know. | Surfaced at H1 | OPEN |
| K3 | Directory as FILE: current behaviour of `validate()` on a directory unverified; `dir_okay=False` would otherwise yield a usage error | Decide at 1.B1: same interception, result ERROR exit 2; verify at 2.C1 | OPEN |
| K4 | Click version differences in `BadParameter` / `Path.convert` signature; mypy strict on subclass | Developer verifies against locked click in poetry.lock | OPEN |
| K5 | Binary (PyInstaller) smoke behaviour must not change | Smoke test 5 kept, JSON assertion added (2.D1) | OPEN |
| K6 | Architecture trigger: new design pattern (ParamType subclass) in cli.py, no new module | Architect task + ADR-005 Amendment 1 | OPEN |

---

## Task Breakdown

| ID | Task | Agent | Branch | Dependencies | Status | Deliverables | Acceptance Criteria |
|----|------|-------|--------|--------------|--------|--------------|---------------------|
| 0.A1 | Create branch `feature/click-path-exists` from `develop` (`git checkout develop && git pull && git checkout -b ...`) | Developer | `feature/click-path-exists` | None | ⏳ | Local branch | Branch exists, based on up-to-date develop (done: branched from `6d72d63`, which adds the hil-team migration commit on top of develop, per human decision) |
| 0.A2 | Create `docs/releases/TASKS-v0.6.1.md` (committed with branch) | Planner | `feature/click-path-exists` | 0.A1 | ✅ | This file | Mirrors every task |
| 1.B1 | Design: interception of `click.Path(exists=True)` failure; decide directory behaviour (`dir_okay`); write ADR-005 Amendment 1 and correct ADR-005 text; update ADR summary row in `.agent-kb/architecture.md` if needed | Architect | `feature/click-path-exists` | 0.A2 | ✅ | `docs/architecture/ADR-005-cli-design.md`; interface stub for the path type; note if locked surface would change (then HX escalation) | ADR matches intended code; contract unchanged; no locked-surface change |
| 2.C1 | Write failing tests: missing file JSON (valid JSON, status ERROR, keys status/file/format_detected/issues, nothing on stdout other than JSON), missing file text, exit 2, `--report-dir` + missing file writes `sbom-report-<basename>.html/.json`, directory as FILE, existing file still PASS/FAIL; unit tests of the path type; fix stale comment at `test_cli_json_output.py:423`; FR-11/12/13 (+ report-dir FR, tester to confirm ID in requirements.md) referenced | Tester | `feature/click-path-exists` | 1.B1 | ✅ | New `tests/unit/test_cli_missing_file.py`; touch `tests/unit/test_cli_json_output.py`, `tests/unit/test_cli_text_output.py` as needed | New tests fail for the right reason; existing tests unchanged in intent; ruff clean |
| 2.C2 | Implement path type/interception in `cli.py`; update `validate_cmd` docs/help | Developer | `feature/click-path-exists` | 2.C1 | ✅ | `src/sbom_validator/cli.py` | All CLI tests pass; `quality_gate` clean; `cli.py` coverage >= 85% |
| 2.D1 | Extend binary smoke: keep test 5 (exit 2), add JSON-on-stdout assertion for missing file | Tester | `feature/click-path-exists` | 2.C2 | ✅ | `tests/smoke/test_binary_smoke.sh` | Script passes against a built binary (or CI) |
| 2.D2 | Verify `tests/integration/test_integration.py::TestErrorPipeline::test_nonexistent_file_exits_two` and unit tests (`tests/unit/test_cli_*.py`) pass; full suite + coverage >= 90 | Tester | `feature/click-path-exists` | 2.C2 | ✅ | Test run evidence | `test`, `coverage` commands green |
| 3.E1 | Docs sync: CHANGELOG `[0.6.1]`; `docs/user-guide.md` troubleshooting (missing file / directory); mark R-12 resolved in `docs/release-checklist-v0.1.0.md` (lines 41, 79) and `TASKS.md:143`; ADR-005 consistency check | Documentation Writer | `feature/click-path-exists` | 2.C2 | ✅ | `CHANGELOG.md`, `docs/user-guide.md`, `docs/release-checklist-v0.1.0.md`, `TASKS.md` | Docs match behaviour; keep-a-changelog format |
| 3.F1 | Independent quality review (G4) | Reviewer | `feature/click-path-exists` | 2.D2, 3.E1 | ⏳ | Findings + verdict | No open CRITICAL/MAJOR |
| 3.F2 | Security review (G5) — parallel with 3.F1 | Security Reviewer | `feature/click-path-exists` | 2.D2 | ⏳ | Findings + verdict | APPROVED/CONDITIONAL |
| 4.G1 | CI stabilization (G6) | CI Ops | `feature/click-path-exists` | 3.F1, 3.F2 | ⏳ | CI report | `test (3.11)`, `test (3.12)` green |
| 5.H1 | Version bump to 0.6.1 | Developer | `feature/click-path-exists` | 4.G1 | ⏳ | `pyproject.toml`, `src/sbom_validator/__init__.py` | Versions consistent |
| 5.H2 | Push branch and open PR `feature/click-path-exists` -> `develop` | Developer | `feature/click-path-exists` | 5.H1, 6.J1 | ⏳ | PR URL | PR open; human reviews (H2) |
| 6.I1 | Release readiness (G8) | Release Manager | `feature/click-path-exists` | 5.H1 | ⏳ | Release brief | All gates pass |
| 6.I2 | Collect telemetry; token report | Token Analyst | `feature/click-path-exists` | 6.I1 | ⏳ | `docs/releases/token-report-v0.6.1.html` | Generated |
| 6.I3 | Token delta report | Token Analyst | `feature/click-path-exists` | 6.I2 | ⏳ | `docs/releases/token-delta-v0.6.0_to_v0.6.1.html` | Generated |
| 6.I4 | Workflow evaluation report | Workflow Analyst | `feature/click-path-exists` | 6.I2 | ⏳ | `docs/releases/workflow-report-v0.6.1.html` | Generated |
| 6.J1 | Release closeout: update `drift_prone_docs` (CLAUDE.md version, `.agent-kb/architecture.md`, `docs/requirements.md` header + JSON example versions, `models.py` docstring) | Documentation Writer | `feature/click-path-exists` | 6.I1 | ⏳ | Listed files | No stale version numbers |
| 7.K1 | Final human gate (H3) and release action | Human + Release Manager | `feature/click-path-exists` | 5.H2, 6.I3, 6.I4, 6.J1 | ⏳ | Approval record | GO/NO-GO recorded |

---

## Scope-Lock

| Task | Files created/modified | External resources | Assumptions | Unverified |
|------|------------------------|--------------------|-------------|------------|
| 1.B1 | ADR-005, `.agent-kb/architecture.md` (maybe) | None | Interception can be done inside `cli.py` | Click version in poetry.lock supports subclassing `click.Path.convert` — verify |
| 2.C1 | `tests/unit/test_cli_missing_file.py` (new), edits to `test_cli_json_output.py`, `test_cli_text_output.py` | None | CliRunner separates stdout/stderr per project fixtures | Behaviour of `validate()` on a directory not verified; `--report-dir` FR ID not verified |
| 2.C2 | `src/sbom_validator/cli.py` | None | No change to `validator.py`/models | `file` echoed in result equals the raw argument string — verify identical to today |
| 2.D1 | `tests/smoke/test_binary_smoke.sh` | Built binary | Script has JSON parsing tool available on Linux/Windows runners | jq/python availability in smoke environment |
| 3.E1 | CHANGELOG, user-guide, release-checklist-v0.1.0, TASKS.md | None | Troubleshooting section exists in user-guide | Section heading not verified |
| 5.H1 | pyproject.toml, `__init__.py` | None | Only two version files | poetry.lock unaffected |
| 6.J1 | See `drift_prone_docs` | None | — | — |

---

## Gate Evidence

### G1 Planning
- Evidence: tracker created by planner agent (separate invocation); plan and scope-lock presented to human
- Status: ✅

### H1 Plan Approval
- Decision: APPROVED (2026-10-07) — plan and scope-lock as written. Confirmed: directory as FILE → structured ERROR exit 2; PATCH release; PR opened after closeout and before H3; historical review docs untouched. K2 (behaviour-neutral change) acknowledged.

### G2 Architecture
- Evidence: Architect agent dispatched (separate invocation). ADR-005 Amendment 1 written (private `click.Path` subclass `_LenientExistingPath`, `exists=True, dir_okay=True`, `convert()` catches `click.BadParameter` and returns raw string); rejected `click.Command` subclass (would swallow real usage errors). Verified against click 8.3.2. Directory → structured ERROR (FR-01), missing file → ERROR; no Compatibility Contract change. Files: `docs/architecture/ADR-005-cli-design.md`, `.agent-kb/architecture.md` (ADR row). mypy not yet run (verify at 2.C2).
- Status: ✅

### G3 TDD Build
- Evidence (2.C1, tester agent, separate invocation): new `tests/unit/test_cli_missing_file.py` (21 tests). 6 `_LenientExistingPath` unit tests fail for the right reason (AttributeError: no attribute `_LenientExistingPath`); 15 behavioural regression guards pass. `test_cli_json_output.py` stale comment fixed. ruff check/format on tests clean. No FR ID exists for `--report-dir`; tests tagged FR-01/11/12/13. Report file names use the file stem (e.g. `sbom-report-no-such-file.spdx.html`), tests assert that.
- Evidence (2.C2, developer agent, separate invocation): `_LenientExistingPath` added to `cli.py`; targeted 70 passed; full suite 732 passed, coverage 96.15% (`cli.py` 99%); ruff check + format clean. mypy: 3 `yaml` import-untyped errors (format_detector.py, spdx_yaml_parser.py, validator.py) — orchestrator verified they are identical on the stashed baseline (pre-existing; `types-pyyaml` is declared in pyproject but not installed in this local env), none in `cli.py`. CI must confirm mypy green at G6.
- Evidence (2.D1/2.D2, tester agent, separate invocation): smoke Test 5b added (missing file + `--format json` → exit 2, valid JSON, status ERROR); `bash -n` OK; NOT executed (no built binary) — deferred to CI. Full suite 732 passed, coverage 96.15% (lowest module validator.py 90%).
- Status: ✅

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
- Evidence (3.E1, documentation-writer agent, separate invocation): CHANGELOG (entry under `[Unreleased]`; closeout must rename to 0.6.1 + date), `docs/user-guide.md` troubleshooting (extended row + new "Cannot read file" row), R-12 resolved notes in `docs/release-checklist-v0.1.0.md` and `TASKS.md`; ADR-005 consistent with code. KB write-back: `.agent-kb/gotchas.md` (lenient Click path contract). ADR/architecture row written at G2.
- Status: ✅

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
| R-12 | Closed by this release (was deferred in v0.1.0) | INFO | Resolved here | v0.6.1 |
| R-04/R-05, R-08, R-09 | Remain deferred (parser signature refactor, format-specific NTIA paths, ISO 8601 validation) | INFO | Out of scope | TBD |

---

## Final Verdict

- **Recommendation:**
- **Approved by (Human):**
- **Date:**
- **Notes:**

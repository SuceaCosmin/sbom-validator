# CLAUDE.md — sbom-validator
<!-- hil-team contract_version: 1 -->

> Auto-loaded at every session start. Keep this concise and decision-critical.
> This repository is worked on by the **hil-team** plugin (`/hil-team:deliver`, `/hil-team:plan`, …).
> Agent roles, gates and human approvals live in the plugin; project facts live here and in `.agent-kb/`.

## Overview

`sbom-validator` is a Python CLI tool that validates SBOM files against format schemas and NTIA minimum element requirements. It is intended for CI/CD pipelines. Published as a pip/pipx package AND standalone binaries (Linux + Windows amd64) via GitHub Releases.

- **Current version:** `0.6.1` (source of truth: `pyproject.toml`; mirrored in `src/sbom_validator/__init__.py`)

### Supported Formats

| Format | Versions | File types |
|--------|----------|------------|
| SPDX 2.3 | 2.3 only | JSON, YAML, Tag-Value |
| SPDX 3.x | 3.0.1 | JSON-LD |
| CycloneDX | 1.3, 1.4, 1.5, 1.6 | JSON, XML |

## Stack

- Python 3.11+ (3.11 and 3.12 tested in CI); Poetry (src layout)
- Runtime: click, jsonschema, xmlschema, pyyaml, spdx-tools, cyclonedx-bom
- Tests: pytest + pytest-cov · Lint/format: ruff (line length 100) · Types: mypy strict
- Binary: PyInstaller ≥ 6.0 (`sbom_validator.spec`) · pre-commit runs `ruff check --fix` and `ruff format`

## Commands

```yaml
install: poetry install --with dev
build: poetry build
test: poetry run pytest
test_targeted: poetry run pytest tests/unit/test_<module>.py -v
coverage: poetry run pytest --cov=sbom_validator --cov-fail-under=90 --cov-report=term
lint: poetry run ruff check src/ tests/
format_check: poetry run ruff format --check src/ tests/
typecheck: poetry run mypy src/
quality_gate: poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/ && poetry run mypy src/
lint_tests: poetry run ruff check tests/ && poetry run ruff format --check tests/
run: poetry run sbom-validator validate <FILE> [--format text|json]
package: poetry build
smoke_test: bash scripts/smoke-test-binary.sh ./dist/sbom-validator   # .exe on Windows; see runbook
```

Run targeted tests during development; the full suite with coverage at phase end. CI rejects anything failing `quality_gate`.

## Conventions

- **Import ordering (ruff I001) — the #1 CI failure cause.** Four groups separated by blank lines, written correctly from the start (don't rely on `ruff --fix`):
  1. `from __future__ import annotations`
  2. Standard library
  3. Third-party (`pytest`, `click`, …)
  4. First-party (`from sbom_validator… import …`) — never mixed with third-party
- Line length 100; mypy strict; type annotations on all public functions and classes.
- `pathlib.Path` for all file operations (never `os.path` strings).
- No magic strings: format names, rule codes and version strings come from `src/sbom_validator/constants.py`.
- All data models are frozen dataclasses — never mutate.
- Test files: `test_<module>_<concern>.py`, split at ~400 lines; shared fixtures in `tests/unit/conftest.py`.
- Every test that covers a requirement references its FR-XX ID (`docs/requirements.md`).

## Branching & PR rules

| Branch | Purpose |
|--------|---------|
| `master` | Stable releases only — never commit directly |
| `develop` | Integration branch — receives completed feature branches |
| `feature/<kebab-case>` | All new work — branched from `develop`, merged back via PR |

- Start: `git checkout develop && git pull && git checkout -b feature/<name>`
- Finish: `git push -u origin feature/<name>`, open PR `feature/<name>` → `develop`. The human reviews and merges.
- Releases: `develop` → `master` via PR per `.agent-kb/runbooks/release.md`.
- Post-merge cleanup: GitHub deletes the remote head branch automatically; delete the local branch (`git checkout develop && git pull origin develop && git branch -d feature/<name>`). Never leave merged branches.

## Compatibility Contract

Backward-compatibility locked — any change needs an ADR + Architect + human approval, changelog and migration notes:

```
sbom-validator validate <FILE> [--format text|json] [--log-level DEBUG|INFO|WARNING|ERROR] [--report-dir PATH]
sbom-validator --version
```

| Exit code | Meaning |
|-----------|---------|
| 0 | PASS |
| 1 | FAIL (validation issues found) |
| 2 | ERROR (tool could not process the file) |

- JSON output keys are stable: `status`, `file`, `format_detected`, `issues`.
- `--format json` output goes to **stdout**; all log output goes to **stderr only** (never mix).
- `--report-dir` writes `sbom-report-<basename>.html/.json` (fixed names, no timestamp).
- Command and option names/semantics are stable.

## Agent Team Settings

```yaml
contract_version: 1
project_name: sbom-validator
repo_url: https://github.com/SuceaCosmin/sbom-validator
integration_branch: develop
protected_branches: [master, develop]
release_flow: same-branch
adr_dir: docs/architecture
requirements_source: docs/requirements.md      # FR-01..FR-15, NFR-01..NFR-05, NTIA mapping
release_tracker_dir: docs/releases
global_task_file: TASKS.md
analytics: enabled                              # CI (release.yml) enforces token + workflow reports before tagging
analytics_reports_dir: docs/releases
architecture_triggers:
  - A new module or file is introduced in src/sbom_validator/
  - A public function signature is added or changed
  - A new runtime dependency is added to pyproject.toml
  - The NormalizedSBOM data model or any frozen dataclass is modified
  - A new design pattern not already established in the codebase is adopted
interface_stub_language: python
interface_source_of_truth:
  - src/sbom_validator/cli.py                   # _render_text() is the source of truth for text output
docs_map:
  - README.md                                   # description, badges, install (pip/pipx/Poetry), 3-command quick start, links
  - docs/user-guide.md                          # install, quick start, formats, NTIA elements, CLI reference, output examples, CI examples (GitHub Actions, GitLab CI, shell), troubleshooting
  - docs/architecture/architecture-overview.md  # system overview, pipeline, how to add a new SBOM format
  - CHANGELOG.md
docs_audience: Developers and DevOps engineers integrating SBOM validation into CI/CD pipelines
drift_prone_docs:
  - CLAUDE.md                                   # version, Supported Formats table
  - .agent-kb/architecture.md                   # Quick-Start Context, module map, ADR count
  - docs/requirements.md                        # header version/status/date, JSON output example version strings
  - src/sbom_validator/models.py                # NormalizedSBOM.format docstring
version_files:
  - pyproject.toml
  - src/sbom_validator/__init__.py
changelog_format: keep-a-changelog
dependency_manifest: [pyproject.toml, poetry.lock]
ci_provider: github-actions
ci_files:
  - .github/workflows/ci.yml
  - .github/workflows/release.yml
  - .github/workflows/sbom-dry-run.yml
required_checks:
  - "test (3.11)"                               # ci.yml job: ruff check, ruff format --check, mypy, pytest --cov-fail-under=90
  - "test (3.12)"
security_posture: >
  Python CLI used as a gate in CI/CD pipelines. Security impact: integrity of validation
  outcomes used in gates, trustworthiness of distributed artifacts (wheels, binaries, SBOMs),
  and reliable behaviour in automated pipelines. No network calls at runtime.
retry_budget: 2
max_parallel_tracks: 4
```

## Knowledge Base

| File | Purpose |
|------|---------|
| `.agent-kb/architecture.md` | Canonical signatures, module map, invariants, NormalizedSBOM + NTIA mapping, coverage, test scenarios — **read before implementing anything** |
| `.agent-kb/domain-glossary.md` | SBOM / SPDX / CycloneDX / NTIA vocabulary |
| `.agent-kb/decisions/README.md` | Pointer + index for ADRs in `docs/architecture/` |
| `.agent-kb/gotchas.md` | Known traps (import ordering, jsonschema registry, fixtures, rebase) |
| `.agent-kb/runbooks/release.md` | Artifacts, release gates, smoke test, tag flow |
| `docs/requirements.md` | FR-01..FR-15, NFR-01..NFR-05 |

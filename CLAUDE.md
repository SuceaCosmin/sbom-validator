# CLAUDE.md — sbom-validator

> Auto-loaded at every session start. Keep this concise and decision-critical.
> For full details, read the linked reference files.

## If You Are an AI Agent

During activities in the project be sure to consider the following:
- Challenge ambiguous or wrong prompts.
- Before implementing any non-trivial feature or refactor suggested by the user, raise at least one concrete question about the value or scope it adds.
- Say it if anything is unclear so that we can further clarify it.
- When evaluating an issue, perform a root cause analysis. Identify multiple hypotheses before settling on one; surface alternatives when the root cause is ambiguous. Ask which to pursue only when you cannot determine the most likely cause yourself — otherwise proceed.

### OUTPUT RULES:
- Feedback, confirmations, status: max 5 lines, no elaboration
- Code: full verbosity always — comments, docstrings, descriptive names
- Explanations when user asks to understand something: full verbosity
- Never explain what you are about to do before doing it
- Never summarize what you just did after doing it
- No filler phrases: "Certainly!", "Great question", "Of course", "I'll now..."

## Project Identity

`sbom-validator` is a Python CLI tool that validates SBOM files against format schemas and NTIA minimum element requirements. Published as a pip/pipx package AND standalone binaries (Linux + Windows amd64) via GitHub Releases.

- **GitHub:** https://github.com/SuceaCosmin/sbom-validator
- **Current version:** `0.5.0` (source of truth: `pyproject.toml`)
- **Python:** 3.11+ (3.11 and 3.12 tested in CI)
- **Package manager:** Poetry (src layout)

### Supported Formats

| Format | Versions | File types |
|--------|----------|------------|
| SPDX 2.3 | 2.3 only | JSON, YAML, Tag-Value |
| CycloneDX | 1.3, 1.4, 1.5, 1.6 | JSON, XML |

## CLI Contract (backward-compatibility locked)

```
sbom-validator validate <FILE> [--format text|json] [--log-level DEBUG|INFO|WARNING|ERROR] [--report-dir PATH]
sbom-validator --version
```

| Exit code | Meaning |
|-----------|---------|
| 0 | PASS |
| 1 | FAIL (validation issues found) |
| 2 | ERROR (tool could not process the file) |

- `--format json` output goes to **stdout**; all log output goes to **stderr only** (never mix)
- Breaking changes to exit codes, JSON output keys, or CLI options require explicit Architect + human approval

## Branching Strategy

| Branch | Purpose |
|--------|---------|
| `master` | Stable releases only — never commit directly |
| `develop` | Integration branch — receives completed feature branches |
| `feature/<kebab-case>` | All new work — branched from `develop`, merged back via PR |

All work goes through feature branches and PRs.

## Mandatory Quality Gate

**Every task must pass these before completion — no exceptions:**

```bash
poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/ && poetry run mypy src/
```

CI will reject anything that doesn't pass. Run targeted tests during development, full suite at phase end:

```bash
# Targeted (during development):
poetry run pytest tests/unit/test_<module>.py -v

# Full suite (phase end):
poetry run pytest --cov=sbom_validator --cov-fail-under=90
```

## Import Ordering (ruff I001)

This is the #1 CI failure cause. Always write imports in this exact order with blank lines between groups:

1. `from __future__ import annotations`
2. Standard library (`import json`, `from pathlib import Path`)
3. Third-party packages (`import pytest`, `from click.testing import CliRunner`)
4. First-party / project imports (`from sbom_validator.models import ...`)

Never mix third-party and first-party imports in the same block.

## Architecture Constraints

- **Four-stage pipeline:** format detection → schema validation → parsing → NTIA checking
- **Schema failure blocks NTIA stage entirely** (ADR-003)
- **NTIA checker only operates on `NormalizedSBOM`** — never imports from parsers
- **All data models are frozen dataclasses** — do not mutate (ADR-004)
- **No magic strings** — use constants from `src/sbom_validator/constants.py`
- **JSON schemas are bundled** at `src/sbom_validator/schemas/` — no network calls at runtime
- **`validator.py` never raises** — all errors return as `ValidationResult(status=ERROR)`

## Agent Operating Model

This project uses a 12-agent, 11-gate delivery pipeline. Key rules:

- **Gate order is strict** — no skipping. See `docs/agent-operating-model.md` for full model.
- **Gates G4 (Review) and G5 (Security)** require independent agent dispatch — never inline.
- **Gates G9 (Token Analytics) and G10 (Workflow Evaluation)** must complete before release tag push.
- **Retry budget:** 2 attempts per failed gate, then escalate to human.
- **Immediate escalation** (no retries): backward-compatibility breaks, security-critical findings, ADR conflicts.
- Every release must have a tracker at `docs/releases/TASKS-vX.Y.Z.md`.

### Agent Dispatch Quick Reference

| Agent | When to invoke |
|-------|---------------|
| `orchestrator` | End-to-end delivery coordination |
| `planner` | Task decomposition at feature start |
| `architect` | New module, signature change, new dependency, data model change |
| `tester` | Write tests BEFORE implementation (TDD) |
| `developer` | Implementation after tests exist |
| `reviewer` | Independent code review (G4 — always separate agent) |
| `security-reviewer` | Security/compliance gate (G5 — always separate agent) |
| `ci-ops` | CI failure triage |
| `documentation-writer` | User-facing docs, README, CHANGELOG |
| `release-manager` | Version/changelog/artifact validation |
| `token-analyst` | Token usage reports (G9) |
| `workflow-analyst` | Workflow evaluation reports (G10) |

## Key Reference Files

**Read `docs/agent-briefing.md` before implementing anything** — it contains canonical function signatures and an ADR summary.

| File | Purpose |
|------|---------|
| `docs/agent-briefing.md` | Canonical function signatures and ADR summary |
| `docs/agent-operating-model.md` | Full gate model, retry policy, approval checkpoints |
| `docs/requirements.md` | FR-01 to FR-14, NFR-01 to NFR-05, NTIA mapping |
| `docs/architecture/ADR-*.md` | Full architectural decisions (9 ADRs) |
| `docs/releases/README.md` | Release tracker naming and lifecycle |
| `.claude/agents/*.md` | Per-agent role definitions and checklists |
| `src/sbom_validator/constants.py` | All format names, rule codes, version strings |

## Module Map

```
src/sbom_validator/
  cli.py               # Click entry point
  validator.py          # Pipeline orchestrator (only module touching filesystem)
  format_detector.py    # Returns "spdx", "spdx-tv", "spdx-yaml", or "cyclonedx"
  schema_validator.py   # JSON schema + XSD validation
  ntia_checker.py       # 7 NTIA minimum element checks (FR-04 to FR-10)
  models.py             # Frozen dataclasses: ValidationResult, NormalizedSBOM, etc.
  constants.py          # Central format/rule code definitions
  exceptions.py         # ParseError, UnsupportedFormatError
  presentation.py       # Humanize field paths and messages for text output
  report_writer.py      # HTML + JSON report generation (string.Template)
  logging_config.py     # stdlib logging, stderr only
  parsers/
    spdx_parser.py      # SPDX JSON (shared _parse_spdx_document helper)
    spdx_yaml_parser.py # SPDX YAML
    spdx_tv_parser.py   # SPDX Tag-Value
    cyclonedx_parser.py  # CycloneDX JSON + XML (multi-version)
```

## Test Structure

```
tests/
  unit/          # Per-module tests, split by concern at ~400 lines
  integration/   # End-to-end CLI tests via CliRunner
  fixtures/      # SPDX + CycloneDX valid/invalid SBOM files
```

- Coverage target: >= 90% (run `poetry run pytest --cov=sbom_validator --cov-report=term` to see current numbers)
- TDD discipline: tests written before implementation
- Test file naming: `test_<module>_<concern>.py`
- Shared fixtures in `tests/unit/conftest.py`




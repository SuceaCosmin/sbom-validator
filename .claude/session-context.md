# sbom-validator — Session Context (for AI assistant onboarding)

> Read this file at the start of every new session to get up to speed instantly.
> Last updated: 2026-04-15

---

## What This Project Is

`sbom-validator` is a Python CLI tool that validates Software Bill of Materials (SBOM) files against format schemas and NTIA minimum element requirements. It is published as a pip/pipx package AND as standalone binaries (Linux + Windows amd64) via GitHub Releases.

- **GitHub:** https://github.com/SuceaCosmin/sbom-validator
- **Current version:** `0.4.0` (released 2026-04-14)
- **Python:** 3.11+ (3.11 and 3.12 tested in CI)

---

## Supported Formats

| Format | Version | Detection key |
|--------|---------|---------------|
| SPDX JSON | 2.3 only | `spdxVersion == "SPDX-2.3"` |
| SPDX YAML | 2.3 only | YAML `safe_load` + `spdxVersion == "SPDX-2.3"` |
| SPDX Tag-Value | 2.3 only | Line starts with `SPDXVersion: SPDX-2.3` |
| CycloneDX JSON | 1.3–1.6 | `bomFormat == "CycloneDX"` + `specVersion in {"1.3","1.4","1.5","1.6"}` |
| CycloneDX XML | 1.3–1.6 | root `<bom>` namespace `http://cyclonedx.org/schema/bom/<version>` |

Wrong version or unrecognized format → `UnsupportedFormatError` → exit code 2.

---

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
- `--report-dir` writes a paired `sbom-report-<basename>.html/.json` (fixed names, no timestamp)

---

## Validation Pipeline (two-stage, sequential)

```
Format Detection → Schema Validation (collect-all) → [if pass] Parse → NTIA Check (collect-all)
```

- Schema failure **blocks** NTIA stage entirely (by design, ADR-003)
- All issues within each stage are collected in a single pass
- `validator.py` is the orchestrator — it is the **only** module that touches the filesystem directly
- `validate()` **never raises** — all errors are returned as `ValidationResult(status=ERROR)`

---

## Module Map & Canonical Signatures

```python
# format_detector.py
def detect_format(file_path: Path) -> str: ...
# Returns "spdx" or "cyclonedx". Raises UnsupportedFormatError on failure.

# parsers/spdx_parser.py
def parse_spdx(file_path: Path) -> NormalizedSBOM: ...

# parsers/cyclonedx_parser.py
def parse_cyclonedx(file_path: Path) -> NormalizedSBOM: ...

# schema_validator.py
def validate_schema(raw_doc: dict[str, Any] | str, format_name: str) -> list[ValidationIssue]: ...
# _schemas_dir() uses PyInstaller-compatible path shim (sys._MEIPASS)

# ntia_checker.py
def check_ntia(sbom: NormalizedSBOM) -> list[ValidationIssue]: ...

# validator.py  ← orchestrator
def validate(file_path: str | Path) -> ValidationResult: ...

# logging_config.py
def configure_logging(level: str) -> None: ...
# Call ONCE at CLI startup. Output to stderr only.

# report_writer.py
def write_reports(result: ValidationResult, report_dir: Path) -> tuple[Path, Path]: ...
# Returns (html_path, json_path). Uses string.Template, no Jinja2.

# presentation.py
def humanize_field_path(field_path: str) -> str: ...
def humanize_message(message: str) -> str: ...
# Strips XML namespace prefixes; removes NTIA rule IDs from human-facing output.
```

---

## Internal Data Model (all frozen dataclasses)

```python
# models.py
class ValidationStatus(StrEnum):   PASS | FAIL | ERROR
class IssueSeverity(StrEnum):       ERROR | WARNING | INFO

@dataclass(frozen=True)
class ValidationIssue:
    severity: IssueSeverity
    field_path: str
    message: str
    rule: str = ""

@dataclass(frozen=True)
class NormalizedComponent:
    component_id: str
    name: str
    version: str | None = None
    supplier: str | None = None
    identifiers: tuple[str, ...] = ()

@dataclass(frozen=True)
class NormalizedRelationship:
    from_id: str
    to_id: str
    relationship_type: str = "DEPENDS_ON"

@dataclass(frozen=True)
class NormalizedSBOM:
    format: str          # "spdx" or "cyclonedx"
    author: str | None = None
    timestamp: str | None = None
    components: tuple[NormalizedComponent, ...] = ()
    relationships: tuple[NormalizedRelationship, ...] = ()

@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    file_path: str
    issues: tuple[ValidationIssue, ...] = ()
    format_detected: str | None = None
```

---

## NTIA Minimum Elements Checked

| FR | Element | SPDX 2.3 JSON | CycloneDX 1.6 |
|----|---------|---------------|---------------|
| FR-04 | Supplier Name | `packages[*].supplier` (strip "Organization:"/"Tool:" prefix; NOASSERTION→None) | `components[*].supplier.name` |
| FR-05 | Component Name | `packages[*].name` | `components[*].name` |
| FR-06 | Component Version | `packages[*].versionInfo` (NOASSERTION→None) | `components[*].version` |
| FR-07 | Unique Identifiers | `packages[*].externalRefs` (PACKAGE-MANAGER=PURL, SECURITY=CPE) | `components[*].purl` and/or `components[*].cpe` |
| FR-08 | Dependency Relationships | `relationships[*]` with type DEPENDS_ON/DYNAMIC_LINK/STATIC_LINK/RUNTIME_DEPENDENCY_OF/DEV_DEPENDENCY_OF | `dependencies[*].dependsOn` (≥1 non-empty) |
| FR-09 | Author | `creationInfo.creators` (entries starting "Tool:" or "Organization:") | `metadata.authors[*].name` OR `metadata.manufacture.name` |
| FR-10 | Timestamp | `creationInfo.created` (ISO 8601, strictly validated) | `metadata.timestamp` (ISO 8601) |

---

## Tech Stack

| Component | Library | Version constraint |
|-----------|---------|--------------------|
| CLI | click | >=8.1 |
| Schema validation | jsonschema | >=4.21 |
| SPDX parsing | spdx-tools | >=0.8 |
| CycloneDX parsing | cyclonedx-bom | >=4.0 |
| XML schema validation | xmlschema | >=3.3 |
| Binary | PyInstaller | >=6.0 |
| Testing | pytest + pytest-cov | >=8.0 |
| Linting | ruff | >=0.4 |
| Formatting | ruff format | >=0.4 (pre-commit hook) |
| Type checking | mypy (strict) | >=1.9 |
| Package manager | Poetry | — |

---

## Repository Layout

```
src/sbom_validator/
  __init__.py          # __version__
  cli.py               # Click entry point
  validator.py         # Orchestrator
  format_detector.py
  schema_validator.py
  ntia_checker.py
  models.py
  presentation.py      # humanize_field_path / humanize_message
  logging_config.py
  report_writer.py
  constants.py
  exceptions.py
  parsers/
    spdx_parser.py
    spdx_yaml_parser.py
    spdx_tv_parser.py
    cyclonedx_parser.py
  schemas/
    spdx-2.3.schema.json
    cyclonedx-{1.3,1.4,1.5,1.6}.schema.json
    cyclonedx-{1.3,1.4,1.5,1.6}.schema.xsd  (and dependencies)

tests/
  unit/                # 27+30+31+12+27+37+64+77+... tests
  integration/         # test_integration.py, test_report_integration.py
  fixtures/
    spdx/              # 7 SPDX fixtures
    cyclonedx/         # 7 CycloneDX fixtures
    integration/       # 4 realistic 24-component SBOMs

docs/
  requirements.md
  agent-briefing.md        ← technical contracts reference
  agent-operating-model.md ← lifecycle flow and gates
  architecture/            ← ADR-001 through ADR-009, drawio diagrams
  releases/                ← TASKS-vX.Y.Z.md per-release trackers
  user-guide.md
  architecture-overview.md

scripts/
  smoke-test-binary.sh     # 14-scenario binary smoke test

sandbox/user-demo/         # Manual test SBOMs for all 3 formats
sbom_validator.spec        # PyInstaller spec
.github/workflows/
  ci.yml
  release.yml              # Triggered by v*.*.* tags → Linux + Windows binaries
```

---

## ADR Summary

| ADR | Decision |
|-----|----------|
| ADR-001 | Format detected from root JSON keys / XML namespace. Wrong version → UnsupportedFormatError. |
| ADR-002 | Parsers return NormalizedSBOM. NTIA checker never imports from parser layer. |
| ADR-003 | Two-stage pipeline: schema (collect-all) then NTIA (collect-all). Schema failure blocks NTIA. |
| ADR-004 | Frozen dataclasses (not Pydantic). StrEnum for JSON serialization. |
| ADR-005 | Click CLI. Commands: `validate`. Exit codes: 0/1/2. |
| ADR-006 | stdlib logging. `--log-level` option. All log output → stderr only. |
| ADR-007 | `--report-dir` writes HTML+JSON pair. string.Template (no Jinja2). No new runtime deps. |
| ADR-008 | PyInstaller `--onefile`. Linux+Windows amd64. Release triggered by `v*.*.*` tags. |
| ADR-009 | SPDX TV and YAML sub-formats. Detection priority: JSON → CycloneDX XML → TV → YAML. TV skips schema validation. YAML validates against existing JSON schema. Shared `_parse_spdx_document` helper. `pyyaml>=6.0` runtime dep. |

---

## Test Count & Quality Bar

- **594+ unit + integration tests** passing on Python 3.11 and 3.12
- **≥96% code coverage**
- Zero mypy errors (strict mode), zero ruff errors
- Pre-commit hooks: ruff check + ruff format (prevent lint/format failures at commit)

---

## Branching Strategy

| Branch | Purpose |
|--------|---------|
| `master` | Stable releases only |
| `develop` | Active development |
| `feature/<name>` | Isolated features within a release |

---

## Development Process (Agent Operating Model)

Key files to read before starting any feature:
1. `TASKS.md` — main progress tracker (authoritative)
2. `docs/agent-briefing.md` — technical contracts and signatures
3. `docs/agent-operating-model.md` — lifecycle flow, gates G0–G10
4. `docs/releases/README.md` — per-release tracker naming
5. `docs/releases/TASKS-vX.Y.Z.md` — the active release tracker

Gates that must be completed before a release tag is pushed: G5 (Security), G9 (Token Analytics), G10 (Workflow Evaluation). No silent omissions — deferrals must be recorded.

---

## Outstanding Deferrals

| ID | Description | Target |
|----|-------------|--------|
| D1 | Formal security review of `xmlschema` dependency | v0.3.x |
| — | R-04/R-05: parser signature refactor | future |
| — | R-08: format-specific NTIA field paths | future |
| — | R-09: full ISO 8601 strict validation (FR-10 already enforced) | future |
| — | R-12: `click.Path(exists=True)` for FILE argument | future |

# Architecture — sbom-validator

> Read by every hil-team agent before acting. Supersedes `docs/agent-briefing.md`.
> Updated by the documentation-writer at G7 and at release closeout; by the architect with every ADR.

## Quick-Start Context

| Property | Value |
|----------|-------|
| **Current version** | `0.6.0` (source of truth: `pyproject.toml`) |
| **Supported formats** | 5: `spdx`, `spdx-tv`, `spdx-yaml`, `spdx3-jsonld`, `cyclonedx` |
| **Source modules** | 17: 12 in `src/sbom_validator/` + 5 parsers in `parsers/` |
| **Test count** | 711 collected (run `poetry run pytest --co -q` for the current count) |
| **Coverage target** | ≥ 90% (`poetry run pytest --cov=sbom_validator --cov-fail-under=90`) |
| **ADR count** | 10 (ADR-001 through ADR-010) in `docs/architecture/` |
| **Python** | 3.11+ (3.11 and 3.12 tested in CI) |

## Module Map

```text
src/sbom_validator/
  cli.py                 # Click entry point
  validator.py           # Pipeline orchestrator (only module touching the filesystem)
  format_detector.py     # Returns "spdx3-jsonld", "spdx", "spdx-tv", "spdx-yaml", or "cyclonedx"
  schema_validator.py    # JSON schema + XSD validation
  ntia_checker.py        # 7 NTIA minimum element checks (FR-04 to FR-10)
  models.py              # Frozen dataclasses: ValidationResult, NormalizedSBOM, etc.
  constants.py           # Central format/rule code definitions
  exceptions.py          # ParseError, UnsupportedFormatError
  presentation.py        # Humanize field paths and messages for text output
  report_writer.py       # HTML + JSON report generation (string.Template)
  logging_config.py      # stdlib logging, stderr only
  schemas/               # Bundled JSON schemas / XSDs (no network at runtime)
  parsers/
    spdx_parser.py         # SPDX JSON (shared _parse_spdx_document helper)
    spdx_yaml_parser.py    # SPDX YAML
    spdx_tv_parser.py      # SPDX Tag-Value
    spdx3_jsonld_parser.py # SPDX 3.x JSON-LD (two-pass @graph traversal)
    cyclonedx_parser.py    # CycloneDX JSON + XML (multi-version)
```

Detailed design: `docs/architecture/architecture-overview.md`, `docs/architecture/normalized-model.md`, DrawIO diagrams in `docs/architecture/*.drawio`.

## Canonical Interfaces

**Verify planned signatures match these exactly before implementing.**

```python
# src/sbom_validator/format_detector.py
def detect_format(file_path: Path) -> str: ...
# Returns "spdx3-jsonld", "spdx", "spdx-tv", "spdx-yaml", or "cyclonedx". Raises UnsupportedFormatError on failure.

# src/sbom_validator/parsers/spdx_parser.py
def parse_spdx(file_path: Path) -> NormalizedSBOM: ...
def _parse_spdx_document(document: dict[str, Any], source_label: str) -> NormalizedSBOM: ...
# _parse_spdx_document is the shared core used by spdx_yaml_parser.py

# src/sbom_validator/parsers/spdx_yaml_parser.py
def parse_spdx_yaml(file_path: Path) -> NormalizedSBOM: ...          # format="spdx-yaml"

# src/sbom_validator/parsers/spdx_tv_parser.py
def parse_spdx_tv(file_path: Path) -> NormalizedSBOM: ...            # format="spdx-tv"

# src/sbom_validator/parsers/spdx3_jsonld_parser.py
def parse_spdx3_jsonld(file_path: Path) -> NormalizedSBOM: ...
# Two-pass @graph traversal; format="spdx3-jsonld".
# Missing spdxId cross-references produce None for the affected field, never raise.
# Multiple SpdxDocument elements: takes first, logs WARNING.
# Raises ParseError on: empty/missing @graph, non-list @graph, no SpdxDocument element.

# src/sbom_validator/parsers/cyclonedx_parser.py
def parse_cyclonedx(file_path: Path) -> NormalizedSBOM: ...

# src/sbom_validator/schema_validator.py
def validate_schema(raw_doc: dict[str, Any], format_name: str) -> list[ValidationIssue]: ...
# format_name accepts: "spdx", "spdx-yaml", "spdx-tv", "cyclonedx", "spdx3-jsonld".
# "spdx3-jsonld" uses Draft202012Validator with an inline envelope schema (ADR-010 Amendment 1).
# NOTE (ADR-008): _schemas_dir() must stay PyInstaller frozen-mode compatible (sys._MEIPASS).

# src/sbom_validator/ntia_checker.py
def check_ntia(sbom: NormalizedSBOM) -> list[ValidationIssue]: ...

# src/sbom_validator/validator.py  (orchestrator — the only module that touches the filesystem)
def validate(file_path: str | Path) -> ValidationResult: ...
# Never raises; all errors are returned as ValidationResult(status=ERROR).

# src/sbom_validator/logging_config.py  (ADR-006)
def configure_logging(level: str) -> None: ...
# Call ONCE at CLI startup, before any pipeline module runs.
# level: "DEBUG" | "INFO" | "WARNING" | "ERROR" (case-insensitive). Default: WARNING.
# All log output goes to stderr. Logger hierarchy: sbom_validator.<module_name>.

# src/sbom_validator/report_writer.py  (ADR-007)
def write_reports(result: ValidationResult, report_dir: Path) -> tuple[Path, Path]: ...
# Returns (html_path, json_path). Creates report_dir if absent.
# Called from cli.py only when --report-dir is supplied; OSError is caught there (non-fatal).
# Filenames fixed: sbom-report-<stem>.html / .json (no timestamp). Does NOT modify models.py.
```

## Invariants

- **Four-stage pipeline:** format detection → schema validation → parsing → NTIA checking.
- **Schema failure blocks the NTIA stage entirely** (ADR-003); issues within each stage are collected in one pass (collect-all).
- **NTIA checker operates only on `NormalizedSBOM`** — it never imports from `parsers/` (ADR-002).
- **All data models are frozen dataclasses** — never mutate (ADR-004). `models.py` changes need Architect approval.
- **No magic strings** — constants from `src/sbom_validator/constants.py`.
- **No network calls at runtime** — JSON schemas bundled at `src/sbom_validator/schemas/`; every jsonschema validator gets an explicit `registry=` (see gotchas).
- **`validator.py` never raises** — all errors return as `ValidationResult(status=ERROR)`; it is the only module touching the filesystem.
- **Logs to stderr only**; JSON data to stdout only.

## Data Contracts

All three types are `@dataclass(frozen=True)`. `ValidationStatus` and `IssueSeverity` inherit from `str` for JSON serialization.

**`NormalizedSBOM`**

| Field | Type | NTIA FR |
|-------|------|---------|
| `format` | `str` — one of `"spdx"`, `"spdx-tv"`, `"spdx-yaml"`, `"spdx3-jsonld"`, `"cyclonedx"` | — |
| `author` | `str \| None` | FR-09 |
| `timestamp` | `str \| None` | FR-10 |
| `components` | `tuple[NormalizedComponent, ...]` | — |
| `relationships` | `tuple[NormalizedRelationship, ...]` | FR-08 |

**`NormalizedComponent`**

| Field | Type | NTIA FR |
|-------|------|---------|
| `component_id` | `str` | — |
| `name` | `str \| None` | FR-05 |
| `version` | `str \| None` | FR-06 |
| `supplier` | `str \| None` | FR-04 |
| `identifiers` | `tuple[str, ...]` | *(not enforced — FR-07 removed)* |

**`NormalizedRelationship`**: `from_id: str`, `to_id: str`, `relationship_type: str`

### NTIA Field Mapping

| FR | NTIA Element | SPDX 2.3 JSON | SPDX 3.x JSON-LD | CycloneDX 1.6 JSON |
|----|-------------|---------------|------------------|--------------------|
| FR-04 | Supplier Name | `packages[*].supplier` (strip `"Organization: "`/`"Tool: "`; `NOASSERTION`→`None`) | `Package.suppliedBy[0]` → spdxId → `element.name` | `components[*].supplier.name` |
| FR-05 | Component Name | `packages[*].name` | `Package.name` | `components[*].name` |
| FR-06 | Component Version | `packages[*].versionInfo` (`NOASSERTION`→`None`) | `Package.packageVersion` | `components[*].version` |
| FR-07 | Other Unique IDs *(removed)* | — | — | — (parsed, not validated; issue #12) |
| FR-08 | Dependency Relationships | `relationships[*]` with type in `DEPENDS_ON`, `DYNAMIC_LINK`, `STATIC_LINK`, `RUNTIME_DEPENDENCY_OF`, `DEV_DEPENDENCY_OF` | `Relationship` with `relationshipType == "DEPENDS_ON"` | `dependencies[*].dependsOn` — ≥ 1 non-empty |
| FR-09 | Author of SBOM Data | `creationInfo.creators` starting `"Tool:"`/`"Organization:"` | `SpdxDocument.creationInfo.createdBy[*]` → spdxId → `name`, joined `", "` | `metadata.authors[*].name` OR `metadata.manufacture.name` |
| FR-10 | Timestamp | `creationInfo.created` (ISO 8601) | `SpdxDocument.creationInfo.created` | `metadata.timestamp` (ISO 8601) |

## ADR Summary

ADRs live in `docs/architecture/ADR-*.md`.

| ADR | Decision |
|-----|----------|
| ADR-001 | Format detected by root keys: `@context == SPDX3_CONTEXT_URL` → SPDX3 JSON-LD (checked first); `spdxVersion=="SPDX-2.3"` → SPDX; `bomFormat=="CycloneDX" && specVersion in {"1.3".."1.6"}` → CycloneDX. Wrong version / no match → `UnsupportedFormatError` (exit 2). Amended v0.6.0 for SPDX 3.x priority. |
| ADR-002 | Parsers accept a file path and return `NormalizedSBOM`. NTIA checker only receives `NormalizedSBOM`; no imports from the parser layer. |
| ADR-003 | Two-stage pipeline: schema validation (collect-all), then NTIA (collect-all, 7 independent checks). Schema failure blocks NTIA. |
| ADR-004 | Frozen dataclasses for all result types; `ValidationStatus`/`IssueSeverity` inherit from `str`. |
| ADR-005 | Click CLI: `sbom-validator validate <FILE> [--format text\|json]`; exit codes 0/1/2. Amendment 1 (v0.6.1): `FILE` uses a private `click.Path(exists=True)` subclass in `cli.py` that swallows `click.BadParameter` and passes the raw string through, so missing files/directories still yield structured ERROR (exit 2). |
| ADR-006 | stdlib `logging`; `--log-level` (default WARNING); stderr only; hierarchy `sbom_validator.<module>`; `configure_logging(level)` once at startup; at INFO/DEBUG the first line is `sbom-validator <version>`. |
| ADR-007 | `--report-dir PATH` writes paired HTML + JSON reports (`sbom-report-<basename>.{html,json}`); `string.Template`; `OSError` non-fatal in `cli.py`. |
| ADR-008 | PyInstaller ≥ 6.0 `--onefile`; Linux + Windows amd64; schemas bundled via `datas` in `sbom_validator.spec`; `spdx-tools` and `cyclonedx-bom` excluded from binary; release on `v*.*.*` tags. |
| ADR-009 | SPDX TV/YAML sub-formats (`spdx-tv`, `spdx-yaml`); detection priority JSON → CycloneDX XML → TV → YAML; TV skips schema validation (INFO log); YAML uses the SPDX 2.3 JSON schema; shared `_parse_spdx_document`; `pyyaml>=6.0`. |
| ADR-010 | SPDX 3.x JSON-LD (`spdx3-jsonld`): detection by `@context`; `Draft202012Validator` with inline envelope schema (full schema deferred — Amendment 1); two-pass `@graph` traversal; missing cross-refs → `None`; `RULE_SPDX3_SCHEMA="FR-15"`. |

## Test Layout and Coverage Targets

```text
tests/
  unit/          # Per-module tests, split by concern at ~400 lines; shared fixtures in conftest.py
  integration/   # End-to-end CLI tests via CliRunner
  fixtures/      # spdx/, cyclonedx/, integration/ — valid/invalid SBOM files
```

Global: ≥ 90% (`--cov-fail-under=90`, enforced in CI).

| Module | Required coverage |
|--------|-------------------|
| `models.py` | 100% |
| `exceptions.py` | 100% |
| `format_detector.py` | 95% |
| `ntia_checker.py` | 95% |
| `schema_validator.py` | 90% |
| `validator.py` | 90% |
| `parsers/spdx_parser.py` | 90% |
| `parsers/spdx_yaml_parser.py` | 90% |
| `parsers/spdx_tv_parser.py` | 90% |
| `parsers/cyclonedx_parser.py` | 90% |
| `cli.py` | 85% |
| other modules | 90% (global) |

## Required Test Scenarios

For each SBOM format and each NTIA element:
- Valid document → no issues reported
- Document missing that element → `ValidationIssue` with the correct `rule` (FR-XX), `field_path` and `severity`

For the pipeline:
- Schema-invalid document → NTIA check is NOT run (test for every format)
- Schema-valid, NTIA-failing document → all NTIA failures reported in one pass

Edge cases for every module:
- Empty string vs `None` for optional fields
- `NOASSERTION` sentinel values (SPDX only)
- Unicode in component names and supplier strings
- CycloneDX components with no `bom-ref` (fallback identifier)
- Empty `components` array; empty `dependencies`/`relationships`
- Correct format fingerprint but wrong version (e.g. `SPDX-2.2`)

## Review Checklist Additions

- [ ] NTIA checker imports only from `models.py`, never from `parsers/`
- [ ] Parsers return `NormalizedSBOM` matching `docs/architecture/normalized-model.md`
- [ ] Parser signatures match the Canonical Interfaces exactly
- [ ] Schema failure stops the pipeline; NTIA runs only on schema-valid docs
- [ ] No `requests`/`urllib`/remote `$ref` resolution in production code; every jsonschema validator has `registry=`
- [ ] Exit codes match ADR-005 (0 PASS, 1 FAIL, 2 ERROR)
- [ ] Each NTIA element has a missing-field test; schema-failure scenario tested for every format

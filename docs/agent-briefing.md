# Agent Briefing — sbom-validator

**Start every task by reading this file.** It distills the decision-critical facts from the full spec.
Read the originals only when you need detailed rationale or full mapping tables.

---

## Quick-Start Context

> Keep this section current at every release (G7 Documentation Writer deliverable + G8 Release Manager checklist item).

| Property | Value |
|----------|-------|
| **Current version** | `0.6.0` (source of truth: `pyproject.toml`) |
| **Supported formats** | 5: `spdx`, `spdx-tv`, `spdx-yaml`, `spdx3-jsonld`, `cyclonedx` |
| **Source modules** | 17: 12 in `src/sbom_validator/` + 5 parsers in `parsers/` |
| **Test count** | 711 collected (run `poetry run pytest --co -q` for current count) |
| **Coverage target** | ≥ 90% (`poetry run pytest --cov=sbom_validator --cov-fail-under=90`) |
| **ADR count** | 10 (ADR-001 through ADR-010) |
| **Python** | 3.11+ (3.11 and 3.12 tested in CI) |

---

## Workflow Entry Point

For end-to-end execution order, gate ownership, escalation policy, and human approval checkpoints, read:

- `docs/agent-operating-model.md`
- `docs/releases/README.md` (for release-specific task tracker naming and lifecycle usage)
- `.claude/agents/token-analyst.md` (for release token usage and delta reporting)

Use this briefing for technical contracts/signatures, and the operating model for orchestration rules.

---

## Architecture Decisions (10 ADRs in brief)

| ADR | Decision |
|-----|----------|
| ADR-001 | Format detected by root JSON keys: `@context == SPDX3_CONTEXT_URL` → SPDX3 JSON-LD (checked first); `spdxVersion=="SPDX-2.3"` → SPDX; `bomFormat=="CycloneDX" && specVersion in {"1.3","1.4","1.5","1.6"}` → CycloneDX. Wrong version or no match → `UnsupportedFormatError` (exit 2). Amended in v0.6.0 to add SPDX 3.x `@context` priority step. |
| ADR-002 | Parsers accept a file path and return `NormalizedSBOM`. NTIA checker only receives `NormalizedSBOM` — it has no imports from the parser layer. |
| ADR-003 | Two-stage pipeline: schema validation (collect-all), then NTIA checks (collect-all, all 7 run independently). **Schema failure blocks the NTIA stage entirely.** |
| ADR-004 | Frozen dataclasses for all result types. `ValidationStatus` and `IssueSeverity` inherit from `str` for JSON serialization. |
| ADR-005 | CLI uses Click. Command: `sbom-validator validate <FILE> [--format text\|json]`. Exit codes: 0=PASS, 1=FAIL, 2=ERROR. |
| ADR-006 | Logging uses Python stdlib `logging`. New `--log-level` CLI option (default: WARNING). All log output goes to stderr only. Logger hierarchy: `sbom_validator.<module>`. `configure_logging(level)` called once at CLI startup. When INFO or DEBUG is active, the first log line is always `sbom-validator <version>` from `sbom_validator.cli`. |
| ADR-007 | New `--report-dir PATH` CLI option writes paired HTML + JSON reports when supplied. Both reports always written together. Filenames: `sbom-report-<basename>.{html,json}` (fixed, no timestamp). HTML uses `string.Template` (no Jinja2). `report_writer.py` does not modify `models.py`. `OSError` on write is caught non-fatally in `cli.py` (warns to stderr, exit code unchanged). |
| ADR-008 | Standalone binary via PyInstaller >= 6.0, `--onefile` mode. Targets: Linux amd64 and Windows amd64. Schema files bundled via `datas` in `sbom_validator.spec`. `spdx-tools` and `cyclonedx-bom` excluded from binary. Release triggered by `v*.*.*` tags via `.github/workflows/release.yml`. |
| ADR-009 | SPDX TV and YAML sub-formats: `FORMAT_SPDX_TV="spdx-tv"`, `FORMAT_SPDX_YAML="spdx-yaml"`. Detection priority: JSON → CycloneDX XML → TV (`startswith("SPDXVersion: ")`) → YAML (`safe_load`+`spdxVersion`). TV skips schema validation with logged INFO. YAML validates against existing `spdx-2.3.schema.json`. Shared `_parse_spdx_document` helper in `spdx_parser.py`. `pyyaml>=6.0` runtime dep. |
| ADR-010 | SPDX 3.x JSON-LD: `FORMAT_SPDX3_JSONLD="spdx3-jsonld"`. Detection by `@context == SPDX3_CONTEXT_URL`. Schema validation uses `Draft202012Validator` with an inline envelope schema (full `spdx-3.0.1.schema.json` deferred — see Amendment 1 in ADR-010). Parser performs two-pass `@graph` traversal: Pass 1 builds `{spdxId: element}` index; Pass 2 resolves cross-references. Missing cross-refs produce `None`, never raise. `RULE_SPDX3_SCHEMA="FR-15"`. |

---

## Module Map and Canonical Function Signatures

```python
# src/sbom_validator/format_detector.py
def detect_format(file_path: Path) -> str: ...
# Returns "spdx3-jsonld", "spdx", "spdx-tv", "spdx-yaml", or "cyclonedx". Raises UnsupportedFormatError on failure.

# src/sbom_validator/parsers/spdx_parser.py
def parse_spdx(file_path: Path) -> NormalizedSBOM: ...
def _parse_spdx_document(document: dict[str, Any], source_label: str) -> NormalizedSBOM: ...
# _parse_spdx_document is the shared core used by spdx_yaml_parser.py

# src/sbom_validator/parsers/spdx_yaml_parser.py
def parse_spdx_yaml(file_path: Path) -> NormalizedSBOM: ...
# Returns NormalizedSBOM with format="spdx-yaml"

# src/sbom_validator/parsers/spdx_tv_parser.py
def parse_spdx_tv(file_path: Path) -> NormalizedSBOM: ...
# Returns NormalizedSBOM with format="spdx-tv"

# src/sbom_validator/parsers/spdx3_jsonld_parser.py
def parse_spdx3_jsonld(file_path: Path) -> NormalizedSBOM: ...
# Two-pass @graph traversal. Returns NormalizedSBOM with format="spdx3-jsonld".
# Missing spdxId cross-references produce None for the affected field, never raise.
# Multiple SpdxDocument elements: takes first, logs WARNING.
# Raises ParseError on: empty/missing @graph, non-list @graph, no SpdxDocument element.

# src/sbom_validator/parsers/cyclonedx_parser.py
def parse_cyclonedx(file_path: Path) -> NormalizedSBOM: ...

# src/sbom_validator/schema_validator.py
def validate_schema(raw_doc: dict[str, Any], format_name: str) -> list[ValidationIssue]: ...
# format_name accepts: "spdx", "spdx-yaml", "spdx-tv", "cyclonedx", "spdx3-jsonld".
# "spdx3-jsonld" uses Draft202012Validator with an inline envelope schema (ADR-010 Amendment 1).
# NOTE (ADR-008): _schemas_dir() helper must be updated for PyInstaller frozen-mode compatibility.

# src/sbom_validator/ntia_checker.py
def check_ntia(sbom: NormalizedSBOM) -> list[ValidationIssue]: ...

# src/sbom_validator/validator.py  (orchestrator — the only module that touches the filesystem)
def validate(file_path: str | Path) -> ValidationResult: ...
# Never raises; all errors are returned as ValidationResult(status=ERROR).

# src/sbom_validator/logging_config.py  (ADR-006)
def configure_logging(level: str) -> None: ...
# Call ONCE at CLI startup, before any pipeline module runs.
# level: "DEBUG" | "INFO" | "WARNING" | "ERROR" (case-insensitive). Default behavior: WARNING.
# All log output goes to stderr. Logger name hierarchy: sbom_validator.<module_name>.

# src/sbom_validator/report_writer.py  (ADR-007)
def write_reports(result: ValidationResult, report_dir: Path) -> tuple[Path, Path]: ...
# Returns (html_path, json_path). Creates report_dir if absent.
# Called from cli.py only when --report-dir is supplied; OSError is caught there (non-fatal).
# Filenames are fixed: sbom-report-<stem>.html / sbom-report-<stem>.json (no timestamp).
# Does NOT modify ValidationResult or models.py.
```

**Before implementing any module, verify your function signatures match these exactly.**

---

## NormalizedSBOM Field Contract

All three types are `@dataclass(frozen=True)`.

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

---

## NTIA Field Mapping (compact)

| FR | NTIA Element | SPDX 2.3 JSON field | SPDX 3.x JSON-LD field | CycloneDX 1.6 JSON field |
|----|-------------|---------------------|------------------------|--------------------------|
| FR-04 | Supplier Name | `packages[*].supplier` (strip `"Organization: "`/`"Tool: "` prefix; `NOASSERTION`→`None`) | `Package.suppliedBy[0]` → spdxId cross-ref → `element.name` | `components[*].supplier.name` |
| FR-05 | Component Name | `packages[*].name` | `Package.name` | `components[*].name` |
| FR-06 | Component Version | `packages[*].versionInfo` (`NOASSERTION`→`None`) | `Package.packageVersion` | `components[*].version` |
| FR-07 | Other Unique IDs *(removed)* | — | — | — | Parsed but not validated; see issue #12 |
| FR-08 | Dependency Relationships | `relationships[*]` with `relationshipType` in: `DEPENDS_ON`, `DYNAMIC_LINK`, `STATIC_LINK`, `RUNTIME_DEPENDENCY_OF`, `DEV_DEPENDENCY_OF` | `Relationship` elements with `relationshipType == "DEPENDS_ON"` | `dependencies[*].dependsOn` — at least one non-empty entry |
| FR-09 | Author of SBOM Data | `creationInfo.creators` entries starting with `"Tool:"` or `"Organization:"` | `SpdxDocument.creationInfo.createdBy[*]` → spdxId cross-ref → `element.name`, joined `", "` | `metadata.authors[*].name` OR `metadata.manufacture.name` |
| FR-10 | Timestamp | `creationInfo.created` (ISO 8601) | `SpdxDocument.creationInfo.created` | `metadata.timestamp` (ISO 8601) |

---

## ⚠️ Schema-Invalid Fixture Rule

"Schema-invalid" means the document **fails JSON schema validation** but **must still contain format fingerprints** (`spdxVersion` for SPDX, `bomFormat` for CycloneDX). Fixtures missing fingerprints trigger an "unrecognized format" error — that is a different error class and a different test scenario.

# sbom-validator User Guide

## Overview

`sbom-validator` is a command-line tool that validates Software Bill of Materials (SBOM) files against two independent criteria: structural conformance to the official JSON schema for the detected format, and compliance with the seven NTIA minimum elements defined in "Framing Software Component Transparency." It exists to give development and DevOps teams a fast, dependency-free gate they can drop into any CI/CD pipeline — the tool requires no network access at runtime (all schemas are bundled), communicates results through standard exit codes, and supports both human-readable text output and structured JSON output for downstream tooling or artifact storage.

---

## Installation

### Using pip

```bash
pip install sbom-validator
```

### Using pipx (recommended for CLI tools)

[pipx](https://pipx.pypa.io/) installs the tool into an isolated environment so it does not interfere with your project's dependencies.

```bash
pipx install sbom-validator
```

### From source with Poetry

```bash
git clone https://github.com/SuceaCosmin/sbom-validator.git
cd sbom-validator
poetry install
poetry run sbom-validator --help
```

---

## Quick Start

**1. Validate a valid SPDX 2.3 file (expected: PASS)**

```bash
sbom-validator validate sbom.spdx.json
```

```
Status:  PASS
File:    sbom.spdx.json
Format:  spdx
Issues:  none
```

**2. Validate a file with NTIA compliance gaps (expected: FAIL)**

```bash
sbom-validator validate incomplete.spdx.json
```

```
Status:  FAIL
File:    incomplete.spdx.json
Format:  spdx
Issues:  1
  [ERROR] packages[2].supplier: Component 'libfoo' is missing a supplier name (NTIA FR-04) (FR-04)
```

**3. Validate with JSON output for CI parsing**

```bash
sbom-validator validate --format json sbom.cdx.json
```

```json
{
  "status": "PASS",
  "file": "sbom.cdx.json",
  "format_detected": "cyclonedx",
  "issues": []
}
```

---

## Supported Formats

| Format | Version | Serialization | `format_detected` value | Schema Validation |
|--------|---------|---------------|------------------------|-------------------|
| SPDX | 2.3 | JSON (`.spdx.json`) | `"spdx"` | Validated against bundled `spdx-2.3.schema.json` |
| SPDX | 2.3 | YAML (`.spdx.yaml`) | `"spdx-yaml"` | Validated against bundled `spdx-2.3.schema.json` |
| SPDX | 2.3 | Tag-Value (`.spdx`) | `"spdx-tv"` | No formal schema — schema stage explicitly skipped |
| CycloneDX | 1.3–1.6 | JSON (`.cdx.json`) | `"cyclonedx"` | Validated against bundled version-specific JSON schema |
| CycloneDX | 1.3–1.6 | XML (`.cdx.xml`) | `"cyclonedx"` | Validated against bundled version-specific XSD |

> **Note:** Format is detected from file content, not the file extension. Detection priority: JSON (SPDX or CycloneDX) → CycloneDX XML → SPDX Tag-Value (file begins with `SPDXVersion: `) → SPDX YAML (YAML dict containing `spdxVersion: SPDX-2.3`). If no format is recognized, or if an unsupported version is detected, the tool exits with code `2` and reports an error.

### SPDX Tag-Value note

SPDX Tag-Value (`.spdx`) files have no official JSON schema or XSD. Schema validation (Stage 1) is explicitly skipped for this format and a log entry is emitted at INFO level. NTIA compliance checking (Stage 2) still runs as normal against all seven elements.

---

## NTIA Minimum Elements

The [NTIA "Framing Software Component Transparency"](https://www.ntia.gov/files/ntia/publications/framingsbom_20191112.pdf) guidance defines seven data fields that every SBOM must contain to be considered minimally compliant. These fields ensure that anyone receiving an SBOM can identify what software is present, who supplied it, and how components relate to each other — without needing to contact the SBOM author for clarification.

`sbom-validator` checks all seven elements in a single pass (Stage 2 of the validation pipeline). Every component in the SBOM is checked individually, so a single missing supplier field on one package produces a targeted error pointing to that specific package rather than a generic document-level failure.

| NTIA Element | Rule | SPDX 2.3 Field | CycloneDX 1.6 Field |
|---|---|---|---|
| Supplier Name | FR-04 | `packages[*].supplier` | `components[*].supplier.name` |
| Component Name | FR-05 | `packages[*].name` | `components[*].name` |
| Component Version | FR-06 | `packages[*].versionInfo` | `components[*].version` |
| Unique Identifiers | *(FR-07 — removed)* | — | — |
| Dependency Relationships | FR-08 | `relationships[]` (at least one `DEPENDS_ON` etc.) | `dependencies[]` (at least one non-empty `dependsOn`) |
| Author of SBOM Data | FR-09 | `creationInfo.creators` | `metadata.authors` or `metadata.manufacture` |
| Timestamp | FR-10 | `creationInfo.created` | `metadata.timestamp` |

> **Note on SPDX supplier values:** The `supplier` field must follow the pattern `"Organization: <name>"` or `"Tool: <name>"`. A value of `NOASSERTION` is treated as absent and triggers an FR-04 error.

---

## CLI Reference

### `sbom-validator validate`

```
sbom-validator validate [OPTIONS] FILE
```

| Argument / Option | Description | Default |
|---|---|---|
| `FILE` | Path to the SBOM JSON file to validate | required |
| `--format [text\|json]` | Output format: human-readable text or machine-readable JSON | `text` |
| `--log-level [DEBUG\|INFO\|WARNING\|ERROR]` | Minimum severity of log messages written to stderr | `WARNING` |
| `--report-dir PATH` | Directory where HTML and JSON reports are written; created if absent | omitted (no reports) |
| `--help` | Show command help and exit | |

### Exit Codes

| Code | Meaning | When |
|------|---------|------|
| `0` | PASS | File passes both schema validation and all NTIA element checks |
| `1` | FAIL | One or more schema violations or NTIA element failures were found |
| `2` | ERROR | Tool or input error: file not found, unparseable JSON, unrecognized format, or internal exception |

Exit codes are designed for use as CI gate conditions. A non-zero exit from `sbom-validator validate` will cause a pipeline step to fail when `set -e` is active or when the CI runner checks exit codes.

### `sbom-validator --version`

Prints the installed version and exits.

```bash
sbom-validator --version
```

```
sbom-validator, version 0.2.0
```

---

## Output Formats

### Text output (default)

Text output is intended for human review in terminal sessions and CI logs. It lists the overall status, the detected format, and each issue with its severity, field path, message, and rule reference.

**PASS example:**

```
Status:  PASS
File:    sbom.spdx.json
Format:  spdx
Issues:  none
```

**FAIL example with multiple issues:**

```
Status:  FAIL
File:    my-app.spdx.json
Format:  spdx
Issues:  2
  [ERROR] packages[2].supplier: Component 'libfoo' is missing a supplier name (NTIA FR-04) (FR-04)
  [ERROR] packages[3].versionInfo: Component 'libbar' is missing a version (FR-06)
```

**ERROR example (unrecognized format):**

```
Status:  ERROR
File:    legacy.spdx.json
Issues:  1
  [ERROR] $: Unrecognized or unsupported SBOM format. Expected SPDX 2.3 or CycloneDX 1.6. (FR-01)
```

### JSON output (`--format json`)

JSON output is intended for downstream tooling: parsing in shell scripts, storing as a CI artifact, feeding into dashboards, or processing with `jq`. The output is a single JSON object written to `stdout`.

**Full schema:**

```json
{
  "tool_version": "0.4.0",
  "status": "PASS|FAIL|ERROR",
  "file": "path/to/file.json",
  "format_detected": "spdx|cyclonedx|null",
  "issues": [
    {
      "severity": "ERROR|WARNING|INFO",
      "field_path": "components[0].supplier",
      "message": "Component 'requests' is missing a supplier name (NTIA FR-04)",
      "rule": "FR-04"
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `tool_version` | string | Version of sbom-validator that produced this output (e.g., `"0.4.0"`) |
| `status` | string | Overall result: `"PASS"`, `"FAIL"`, or `"ERROR"` |
| `file` | string | The file path as provided to the CLI |
| `format_detected` | string or null | `"spdx"`, `"cyclonedx"`, or `null` if detection failed |
| `issues` | array | List of all issues found; empty array on PASS |
| `issues[].severity` | string | `"ERROR"` for blocking failures, `"WARNING"` for advisory, `"INFO"` for informational |
| `issues[].field_path` | string | JSONPath expression identifying the field or location involved |
| `issues[].message` | string | Human-readable description of the issue |
| `issues[].rule` | string | The functional requirement identifier (e.g., `"FR-04"`) |

**PASS example:**

```json
{
  "tool_version": "0.4.0",
  "status": "PASS",
  "file": "sbom.spdx.json",
  "format_detected": "spdx",
  "issues": []
}
```

**FAIL example:**

```json
{
  "tool_version": "0.4.0",
  "status": "FAIL",
  "file": "my-app.spdx.json",
  "format_detected": "spdx",
  "issues": [
    {
      "severity": "ERROR",
      "field_path": "packages[2].supplier",
      "message": "Component 'libfoo' is missing a supplier name (NTIA FR-04)",
      "rule": "FR-04"
    }
  ]
}
```

---

## CI/CD Integration

### GitHub Actions

Minimal step to block a pull request if the SBOM fails validation:

```yaml
- name: Validate SBOM
  run: |
    pip install sbom-validator
    sbom-validator validate sbom.spdx.json
```

Full job with JSON output captured as an artifact for audit purposes:

```yaml
jobs:
  sbom-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install sbom-validator
        run: pip install sbom-validator

      - name: Validate SPDX SBOM
        run: sbom-validator validate --format json sbom.spdx.json | tee sbom-validation.json

      - name: Upload validation report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: sbom-validation-report
          path: sbom-validation.json
```

The `if: always()` condition on the upload step ensures the report artifact is stored even when validation fails, which is essential for diagnosing failures in the CI log.

### GitLab CI

```yaml
validate-sbom:
  stage: test
  script:
    - pip install sbom-validator
    - sbom-validator validate --format json sbom.cdx.json | tee sbom-validation-report.json
  artifacts:
    when: always
    paths:
      - sbom-validation-report.json
```

GitLab treats a non-zero script exit code as a job failure, so the pipeline gate is enforced automatically.

### Generic Shell Script

The following script wraps `sbom-validator` for use in any shell-based pipeline. Pass the SBOM file path as the first argument.

```bash
#!/bin/bash
set -euo pipefail

SBOM_FILE="${1:?Usage: validate-sbom.sh <path-to-sbom>}"

sbom-validator validate --format json "$SBOM_FILE" | tee sbom-validation.json
EXIT_CODE=${PIPESTATUS[0]}

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "SBOM validation passed."
elif [ "$EXIT_CODE" -eq 1 ]; then
  echo "SBOM validation failed — see issues above or in sbom-validation.json"
  exit 1
else
  echo "SBOM validation error — check the file path and format."
  exit 2
fi
```

> **Note:** `${PIPESTATUS[0]}` captures the exit code of `sbom-validator` before it is overwritten by `tee`. Plain `$?` after a pipeline captures the exit code of the last command (`tee`), which is always `0` if the file write succeeds.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Status: ERROR` — Unrecognized or unsupported SBOM format | File is SPDX 2.2, CycloneDX 1.2, or another format/version not supported | Regenerate the SBOM targeting SPDX 2.3 (JSON, YAML, or Tag-Value) or CycloneDX 1.3–1.6 (JSON or XML) |
| `Status: ERROR` — file not found | The path passed to `validate` does not exist or is misspelled | Verify the path with `ls` or `dir`; use an absolute path if in doubt |
| `Status: ERROR` — invalid JSON | The file is not valid JSON (truncated, BOM prefix, encoding issue) | Validate the JSON separately with `python -m json.tool <file>` |
| `Status: FAIL` — FR-02 or FR-03 schema errors | The SBOM does not conform to the SPDX 2.3 or CycloneDX 1.6 JSON schema | Read the reported field paths and fix the structural errors in the SBOM; NTIA checks are skipped until schema passes |
| `Status: FAIL` — FR-04 missing supplier | One or more packages lack a `supplier` field, or the value is `NOASSERTION` | Add a `supplier` field in the form `"Organization: <name>"` or `"Tool: <name>"` to every package |
| `Status: FAIL` — FR-06 missing version | One or more components lack a `versionInfo` (SPDX) or `version` (CycloneDX) field | Add a non-empty version string to every component |
| `Status: FAIL` — FR-08 no dependency relationships | The SBOM contains no qualifying relationship entries | Add at least one `DEPENDS_ON` relationship (SPDX) or one `dependencies` entry with a non-empty `dependsOn` list (CycloneDX) |
| `Status: FAIL` — FR-09 no SBOM author | `creationInfo.creators` (SPDX) or `metadata.authors` / `metadata.manufacture` (CycloneDX) is missing or empty | Add at least one creator entry beginning with `"Tool:"` or `"Organization:"` (SPDX), or at least one author with a non-empty `name` (CycloneDX) |

---

## Structured Logging

By default, `sbom-validator` is quiet: it emits validation output to stdout and suppresses all internal log messages except genuine warnings. When you need to diagnose an unexpected result, or when you want full pipeline visibility in a verbose CI run, use the `--log-level` option.

### `--log-level` option

```
sbom-validator validate <FILE> [--log-level DEBUG|INFO|WARNING|ERROR]
```

| Value | What is emitted to stderr |
|---|---|
| `ERROR` | Only unexpected internal errors |
| `WARNING` | Genuine warnings from parsing and detection (e.g., deprecated fields encountered) |
| `INFO` | Pipeline stage transitions: format detected, schema result, NTIA result, validation complete |
| `DEBUG` | Full internal trace: every parse step, component count, schema run, stage transition |

The default is `WARNING`. Log output is always written to **stderr**, never stdout, so `--format json` output piped to `jq` or `tee` is never contaminated by log lines.

### Log line format

```
2026-04-08T14:22:01Z INFO     sbom_validator.validator — Validation started for: bom.json
```

The format is: `<UTC timestamp> <level padded to 8 chars> <logger name> — <message>`.

### Example invocations

**Default (WARNING) — no output on a normal run:**

```bash
sbom-validator validate sbom.spdx.json
```

```
Status:  PASS
File:    sbom.spdx.json
Format:  spdx
Issues:  none
```

No log lines appear on stderr because no genuine warnings were raised.

**INFO — pipeline stage transitions visible:**

```bash
sbom-validator validate sbom.spdx.json --log-level INFO 2>validator.log
cat validator.log
```

```
2026-04-08T14:22:01Z INFO     sbom_validator.cli — sbom-validator 0.4.0
2026-04-08T14:22:01Z INFO     sbom_validator.validator — Validation started for: sbom.spdx.json
2026-04-08T14:22:01Z INFO     sbom_validator.format_detector — Format detected: spdx (file: sbom.spdx.json)
2026-04-08T14:22:01Z INFO     sbom_validator.schema_validator — Schema validation passed (0 issues)
2026-04-08T14:22:01Z INFO     sbom_validator.ntia_checker — NTIA check completed: 0 issue(s)
2026-04-08T14:22:01Z INFO     sbom_validator.validator — Validation completed: status=PASS, issues=0
```

**DEBUG — full internal trace:**

```bash
sbom-validator validate sbom.spdx.json --log-level DEBUG 2>&1 | head -20
```

At DEBUG level, every component parse, schema keyword evaluation, and stage transition is logged. This is most useful when the tool rejects a file unexpectedly and you need to identify which pipeline stage failed.

### CI usage patterns

**Suppress all log output (default behaviour — no flag needed):**

```yaml
- name: Validate SBOM
  run: sbom-validator validate sbom.spdx.json
```

**Verbose debug run when investigating a failure:**

```bash
sbom-validator validate sbom.spdx.json --log-level DEBUG 2>debug.log
# Review debug.log after the run
```

**Capture logs to a file while keeping stdout clean for JSON parsing:**

```bash
sbom-validator validate --format json sbom.spdx.json \
  --log-level INFO 2>validator.log | jq '.status'
```

Because log output goes to stderr and JSON output goes to stdout, the two streams do not interfere.

---

## Generating Reports

Use `--report-dir` to write durable HTML and JSON reports after a validation run. This is useful for archiving results alongside the SBOM, feeding a dashboard, or sharing a human-readable summary with stakeholders.

### `--report-dir` option

```
sbom-validator validate <FILE> [--report-dir PATH]
```

| Parameter | Description |
|---|---|
| `PATH` | Directory where reports are written. Created automatically if it does not exist. |

When `--report-dir` is supplied, **both** an HTML report and a JSON report are always written. There is no option to write only one. When `--report-dir` is omitted, no report files are created and the tool behaves identically to v0.1.0.

### Filename convention

Both files use a fixed stem derived from the validated file's base name:

```
sbom-report-<basename>.html
sbom-report-<basename>.json
```

- `<basename>` is the filename without extension (e.g., `bom` for `bom.json`, `my-sbom.cdx` for `my-sbom.cdx.json`).
- The names are stable across runs, so CI pipelines can reference them at a known path without globbing.
- The `generated_at` field inside the report content still records the UTC timestamp of the run.

Example: validating `bom.json` writes:

```
reports/sbom-report-bom.html
reports/sbom-report-bom.json
```

If your workflow retains reports from multiple runs, point `--report-dir` at a run-scoped subdirectory (e.g., `--report-dir reports/$GITHUB_RUN_ID/`) rather than relying on filename uniqueness.

### Example invocation

```bash
sbom-validator validate my-app.spdx.json --report-dir reports/
```

```
Status:  PASS
File:    my-app.spdx.json
Format:  spdx
Issues:  none
```

The two report files are written to `reports/` silently. Validation output continues to go to stdout as normal.

Combined with `--format json` and a log level for CI use:

```bash
sbom-validator validate my-app.spdx.json \
  --format json \
  --report-dir /tmp/sbom-reports \
  --log-level INFO
```

### HTML report

The HTML report is self-contained (inline CSS, no external dependencies) and designed to be viewable in any browser offline. It contains:

- **Header:** tool name and version, generation timestamp (UTC), validated file path, detected format, and an overall status badge (`PASS` in green, `FAIL` in red, `ERROR` in orange).
- **Summary:** counts of errors, warnings, and informational issues.
- **Issues table:** columns — Severity, Rule, Field Path, Message — sorted with ERROR rows first, then WARNING, then INFO. If there are no issues, the table is replaced by "No issues found."
- **Footer:** `Generated by sbom-validator vX.Y.Z`.

### JSON report

The JSON report is the machine-readable contract for downstream tools. All fields are present on every run.

**Full schema:**

```json
{
  "generated_at": "2026-04-08T14:22:01Z",
  "tool_version": "0.2.0",
  "file_path": "/abs/path/to/bom.json",
  "format_detected": "spdx-2.3",
  "status": "PASS",
  "summary": {
    "error_count": 0,
    "warning_count": 0,
    "info_count": 0
  },
  "issues": []
}
```

**Field definitions:**

| Field | Type | Description |
|---|---|---|
| `generated_at` | ISO 8601 UTC string | UTC timestamp at the moment the report was written; format `%Y-%m-%dT%H:%M:%SZ` |
| `tool_version` | string | Installed version of `sbom-validator` (e.g., `"0.2.0"`) |
| `file_path` | string | File path as passed to the CLI; may be relative or absolute |
| `format_detected` | string or null | `"spdx-2.3"`, `"cyclonedx-1.6"`, or `null` if format detection failed |
| `status` | string | `"PASS"`, `"FAIL"`, or `"ERROR"` |
| `summary.error_count` | integer | Number of issues with severity `ERROR` |
| `summary.warning_count` | integer | Number of issues with severity `WARNING` |
| `summary.info_count` | integer | Number of issues with severity `INFO` |
| `issues` | array | All issues, sorted ERROR first then WARNING then INFO; empty array on PASS |
| `issues[*].severity` | string | `"ERROR"`, `"WARNING"`, or `"INFO"` |
| `issues[*].rule` | string | Functional requirement identifier, e.g., `"FR-04"` |
| `issues[*].field_path` | string | JSONPath expression identifying the field involved |
| `issues[*].message` | string | Human-readable description of the issue |

> **Note on `format_detected`:** The JSON report expands the tool's internal format tokens to include the version string. The internal value `"spdx"` becomes `"spdx-2.3"` and `"cyclonedx"` becomes `"cyclonedx-1.6"` in the report. The stdout JSON output from `--format json` uses the shorter internal tokens; only the report file uses the expanded form.

---

## Downloading Pre-built Binaries

Standalone executables are available for Linux (amd64) and Windows (amd64) on the [GitHub Releases page](https://github.com/SuceaCosmin/sbom-validator/releases). These binaries include a bundled Python interpreter and all dependencies — no Python installation is required on the target machine.

Binaries are built automatically by the release workflow whenever a version tag (e.g., `v0.2.0`) is pushed to the repository.

### Linux

```bash
# Download the binary for the target release
curl -L https://github.com/SuceaCosmin/sbom-validator/releases/download/v0.2.0/sbom-validator \
  -o sbom-validator

# Make it executable
chmod +x sbom-validator

# Verify it starts correctly
./sbom-validator --version
```

```
sbom-validator, version 0.2.0
```

```bash
# Validate an SBOM
./sbom-validator validate my-app.spdx.json
```

To make the binary available system-wide, move it to a directory on your `PATH`:

```bash
sudo mv sbom-validator /usr/local/bin/sbom-validator
```

### Windows

Download `sbom-validator.exe` from the [Releases page](https://github.com/SuceaCosmin/sbom-validator/releases) and run it directly from PowerShell or Command Prompt:

```powershell
# Verify it starts correctly
.\sbom-validator.exe --version
```

```
sbom-validator, version 0.2.0
```

```powershell
# Validate an SBOM
.\sbom-validator.exe validate my-app.cdx.json
```

> **Note on Windows antivirus scanning:** The binary uses PyInstaller's `--onefile` mode, which extracts itself to a temporary directory on first run. Antivirus software may slow the first launch while it scans the extracted files. Subsequent launches from the same temporary directory are faster.

---

## Version Support

| Python | Supported |
|--------|-----------|
| 3.12 | Yes |
| 3.11 | Yes |
| 3.10 and below | No |

`sbom-validator` requires Python 3.11 or later. Earlier versions are not tested and are not supported. Use `python --version` to confirm your environment before installing.

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
git clone https://github.com/your-org/sbom-validator.git
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
Issues:  2
  [ERROR] packages[2].supplier: Component 'libfoo' is missing a supplier name (NTIA FR-04) (FR-04)
  [ERROR] packages[2].externalRefs: Component 'libfoo' has no PURL or CPE identifier (FR-07)
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

| Format | Version | File Extension | Status |
|--------|---------|----------------|--------|
| SPDX | 2.3 | `.spdx.json` | Supported |
| CycloneDX | 1.6 | `.cdx.json` or `.json` | Supported |

> **Note:** Format is detected from file content, not the file extension. The tool looks for `"spdxVersion": "SPDX-2.3"` to identify SPDX files, and for `"bomFormat": "CycloneDX"` plus `"specVersion": "1.6"` to identify CycloneDX files. If neither signature is found, or if a different version is detected, the tool exits with code `2` and reports an error.

---

## NTIA Minimum Elements

The [NTIA "Framing Software Component Transparency"](https://www.ntia.gov/files/ntia/publications/framingsbom_20191112.pdf) guidance defines seven data fields that every SBOM must contain to be considered minimally compliant. These fields ensure that anyone receiving an SBOM can identify what software is present, who supplied it, and how components relate to each other — without needing to contact the SBOM author for clarification.

`sbom-validator` checks all seven elements in a single pass (Stage 2 of the validation pipeline). Every component in the SBOM is checked individually, so a single missing supplier field on one package produces a targeted error pointing to that specific package rather than a generic document-level failure.

| NTIA Element | Rule | SPDX 2.3 Field | CycloneDX 1.6 Field |
|---|---|---|---|
| Supplier Name | FR-04 | `packages[*].supplier` | `components[*].supplier.name` |
| Component Name | FR-05 | `packages[*].name` | `components[*].name` |
| Component Version | FR-06 | `packages[*].versionInfo` | `components[*].version` |
| Unique Identifiers | FR-07 | `packages[*].externalRefs` (PURL or CPE) | `components[*].purl` or `components[*].cpe` |
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
sbom-validator, version 0.1.0
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
Issues:  3
  [ERROR] packages[2].supplier: Component 'libfoo' is missing a supplier name (NTIA FR-04) (FR-04)
  [ERROR] packages[2].externalRefs: Component 'libfoo' has no PURL or CPE identifier (FR-07)
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
  "status": "PASS",
  "file": "sbom.spdx.json",
  "format_detected": "spdx",
  "issues": []
}
```

**FAIL example:**

```json
{
  "status": "FAIL",
  "file": "my-app.spdx.json",
  "format_detected": "spdx",
  "issues": [
    {
      "severity": "ERROR",
      "field_path": "packages[2].supplier",
      "message": "Component 'libfoo' is missing a supplier name (NTIA FR-04)",
      "rule": "FR-04"
    },
    {
      "severity": "ERROR",
      "field_path": "packages[2].externalRefs",
      "message": "Component 'libfoo' has no PURL or CPE identifier",
      "rule": "FR-07"
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
| `Status: ERROR` — Unrecognized or unsupported SBOM format | File is SPDX 2.2, CycloneDX 1.5, XML, tag-value, or another format not supported in v0.1.0 | Regenerate the SBOM targeting SPDX 2.3 JSON or CycloneDX 1.6 JSON |
| `Status: ERROR` — file not found | The path passed to `validate` does not exist or is misspelled | Verify the path with `ls` or `dir`; use an absolute path if in doubt |
| `Status: ERROR` — invalid JSON | The file is not valid JSON (truncated, BOM prefix, encoding issue) | Validate the JSON separately with `python -m json.tool <file>` |
| `Status: FAIL` — FR-02 or FR-03 schema errors | The SBOM does not conform to the SPDX 2.3 or CycloneDX 1.6 JSON schema | Read the reported field paths and fix the structural errors in the SBOM; NTIA checks are skipped until schema passes |
| `Status: FAIL` — FR-04 missing supplier | One or more packages lack a `supplier` field, or the value is `NOASSERTION` | Add a `supplier` field in the form `"Organization: <name>"` or `"Tool: <name>"` to every package |
| `Status: FAIL` — FR-06 missing version | One or more components lack a `versionInfo` (SPDX) or `version` (CycloneDX) field | Add a non-empty version string to every component |
| `Status: FAIL` — FR-07 no unique identifier | One or more components have no PURL or CPE | Add a `purl` (CycloneDX) or an `externalRefs` entry with `referenceCategory` `PACKAGE-MANAGER` or `SECURITY` (SPDX) to every component |
| `Status: FAIL` — FR-08 no dependency relationships | The SBOM contains no qualifying relationship entries | Add at least one `DEPENDS_ON` relationship (SPDX) or one `dependencies` entry with a non-empty `dependsOn` list (CycloneDX) |
| `Status: FAIL` — FR-09 no SBOM author | `creationInfo.creators` (SPDX) or `metadata.authors` / `metadata.manufacture` (CycloneDX) is missing or empty | Add at least one creator entry beginning with `"Tool:"` or `"Organization:"` (SPDX), or at least one author with a non-empty `name` (CycloneDX) |

---

## Version Support

| Python | Supported |
|--------|-----------|
| 3.12 | Yes |
| 3.11 | Yes |
| 3.10 and below | No |

`sbom-validator` requires Python 3.11 or later. Earlier versions are not tested and are not supported. Use `python --version` to confirm your environment before installing.

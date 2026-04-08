# ADR-007: Report Content Contract and File Convention

## Status

Accepted

## Context

`sbom-validator` currently produces validation results only on stdout (text or JSON). As the tool moves into regulated environments and security review workflows, stakeholders need durable, shareable artifacts: a human-readable HTML report and a machine-readable JSON report that can be archived alongside the SBOM being validated.

Key constraints that shaped this decision:

- **No new template engine dependency.** Adding Jinja2 would pull in MarkupSafe and increase the binary size for the standalone distribution (ADR-008). Python's stdlib `string.Template` is sufficient for a single static HTML template.
- **Atomic pair semantics.** Both reports describe the same validation run. Delivering only one of the two creates a consistency hazard (a human report with no machine-readable counterpart, or vice versa). Both are always written together.
- **Immutable `models.py`.** The report writer is a consumer of `ValidationResult`; it must not modify the result model or add fields to it.
- **Optional by default.** The report writing path must be a no-op when `--report-dir` is not supplied, preserving backward compatibility with existing CI integrations.

This decision satisfies FR-15 (report generation) and NFR-04 (no additional mandatory dependencies for report output).

## Decision

### New CLI Option

The `validate` subcommand gains a `--report-dir` option:

```
sbom-validator validate <FILE> [--format text|json] [--log-level LEVEL] [--report-dir PATH]
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--report-dir` | `click.Path(file_okay=False, writable=True)` option | `None` | Directory where HTML and JSON reports are written. When omitted, no report files are created. |

When `--report-dir` is supplied, both the HTML report and the JSON report are always written. There is no option to write only one.

### New Module: `report_writer.py`

A `src/sbom_validator/report_writer.py` module exposes a single public function:

```python
# src/sbom_validator/report_writer.py

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


def write_reports(
    result: ValidationResult,
    report_dir: Path,
) -> tuple[Path, Path]:
    """Write HTML and JSON reports for a completed validation run.

    Creates report_dir if it does not already exist.

    Args:
        result: The completed ValidationResult from the validator pipeline.
        report_dir: Directory in which to write the two report files.

    Returns:
        A two-tuple (html_path, json_path) of the paths actually written.

    Raises:
        OSError: If the directory cannot be created or the files cannot
                 be written (e.g., permission denied).
    """
    ...
```

### Interface Contract (Python stub)

```python
# report_writer.py

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sbom_validator.models import ValidationResult


def write_reports(
    result: ValidationResult,
    report_dir: Path,
) -> tuple[Path, Path]: ...
```

`report_writer.py` imports from `sbom_validator.models` (read-only). It does NOT modify `models.py`.

### Filename Convention

Both files share a common stem derived from the validated file and the UTC timestamp of report generation:

```
sbom-report-<basename>-<timestamp>.html
sbom-report-<basename>-<timestamp>.json
```

Where:

- `<basename>` is `Path(result.file_path).stem` (filename without extension, e.g., `bom` for `bom.json`, `my-sbom` for `my-sbom.cdx.json`).
- `<timestamp>` is the UTC time at the moment `write_reports` is called, formatted as `YYYYMMDD-HHMMSS` (e.g., `20260408-142201`). The timestamp is computed once inside `write_reports` and used for both filenames to guarantee the pair shares an identical stem.

Example: validating `bom.json` at 2026-04-08 14:22:01 UTC produces:

```
sbom-report-bom-20260408-142201.html
sbom-report-bom-20260408-142201.json
```

### JSON Report Schema

The JSON report is the machine-readable contract for downstream tools. The key set is fixed for v0.2.0:

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
  "issues": [
    {
      "severity": "ERROR",
      "rule": "FR-02",
      "field_path": "packages.0.name",
      "message": "Field 'name' is required"
    }
  ]
}
```

**Field definitions:**

| Key | Type | Source | Notes |
|---|---|---|---|
| `generated_at` | ISO 8601 UTC string | `datetime.now(timezone.utc)` inside `write_reports` | Format: `%Y-%m-%dT%H:%M:%SZ` |
| `tool_version` | string | `importlib.metadata.version("sbom-validator")` | Reflects installed package version |
| `file_path` | string | `result.file_path` | As recorded by the validator; may be relative or absolute depending on how the CLI was invoked |
| `format_detected` | `"spdx-2.3"` \| `"cyclonedx-1.6"` \| `null` | Derived from `result.format_detected` | The internal token (`"spdx"`, `"cyclonedx"`) is expanded to the full version string for external consumers; `null` when format detection failed |
| `status` | `"PASS"` \| `"FAIL"` \| `"ERROR"` | `result.status.value` | Direct StrEnum serialization |
| `summary.error_count` | integer | Count of issues where `severity == ERROR` | |
| `summary.warning_count` | integer | Count of issues where `severity == WARNING` | |
| `summary.info_count` | integer | Count of issues where `severity == INFO` | |
| `issues` | array | `result.issues` | Sorted by severity: ERROR first, then WARNING, then INFO |
| `issues[*].severity` | string | `issue.severity.value` | |
| `issues[*].rule` | string | `issue.rule` | |
| `issues[*].field_path` | string | `issue.field_path` | |
| `issues[*].message` | string | `issue.message` | |

**Format token expansion:** The internal `format_detected` values `"spdx"` and `"cyclonedx"` are expanded in report output:

| Internal token | JSON report value |
|---|---|
| `"spdx"` | `"spdx-2.3"` |
| `"cyclonedx"` | `"cyclonedx-1.6"` |
| `None` | `null` |

This expansion happens only in report output. `ValidationResult.format_detected` is not changed.

### HTML Report Structure

The HTML report uses Python's `string.Template` with a module-level constant `_HTML_TEMPLATE` defined in `report_writer.py`. No external template engine is used.

The template uses `$`-prefixed substitution variables (e.g., `$tool_version`, `$generated_at`). For multi-row table content, the `write_reports` function builds the inner HTML strings programmatically and substitutes them as single variables.

**Required sections, in order:**

**1. Header**

Contains:
- Tool name and version: `sbom-validator vX.Y.Z`
- Generated-at timestamp: UTC ISO 8601 string (same value as `generated_at` in JSON report)
- Validated file path: `result.file_path`
- Format detected: expanded format string (e.g., `spdx-2.3`) or `Unknown` if `None`
- Overall status badge: the text `PASS`, `FAIL`, or `ERROR` rendered with a distinct background color:
  - `PASS` → green (`#2e7d32` background, white text)
  - `FAIL` → red (`#c62828` background, white text)
  - `ERROR` → orange (`#e65100` background, white text)

**2. Summary**

A three-column row showing:
- Errors: N
- Warnings: N
- Info: N

**3. Issues Table**

Columns (left to right): **Severity** | **Rule** | **Field Path** | **Message**

Rows are sorted by severity: ERROR rows first, then WARNING, then INFO. Within each severity group, original order is preserved.

When `result.issues` is empty and `status == PASS`, the table is replaced by a single paragraph: `No issues found.`

**4. Footer**

Single line: `Generated by sbom-validator vX.Y.Z`

### Write Semantics

- `report_dir` is created with `report_dir.mkdir(parents=True, exist_ok=True)` before any file write.
- HTML is written first, then JSON. If the HTML write succeeds but the JSON write fails (e.g., disk full), the HTML file is retained. No rollback is performed. This is an explicit decision: partial output is preferable to silent loss of the human-readable report.
- File encoding is UTF-8 for both outputs.
- Files are written with standard Python `Path.write_text` / `Path.write_bytes`; no temporary file + rename pattern is used in v0.2.0. Atomic rename is deferred.

### Deferred Scope

The following capabilities are explicitly out of scope for v0.2.0 and must not be implemented:

- **File size and SHA-256 hash** in reports. These require an additional filesystem read and add complexity to the spec file bundling (ADR-008). Deferred to a future version.
- **Atomic write** (write to temp file, rename). Deferred until there is evidence of partial-write failures in practice.
- **CSS framework or external stylesheet.** The HTML template uses inline `<style>` only, to keep the report self-contained and viewable offline.

## Consequences

**Positive:**

- `string.Template` is stdlib; no new runtime dependency.
- Both reports share identical content, generated from the same `ValidationResult` in a single function call. There is no risk of the two reports diverging.
- The JSON schema is versioned implicitly by `tool_version`; consumers can gate on that field.
- `write_reports` returning `(html_path, json_path)` allows the CLI to log the paths written, providing operator feedback.

**Negative:**

- `string.Template` does not support loops or conditionals. The `write_reports` implementation must pre-render table rows as strings and substitute them as a single variable. This is more verbose than a real template engine but keeps the dependency count at zero.
- No rollback on partial write. In the unlikely event of a disk-full condition between the HTML and JSON writes, the operator is left with one of two reports. The consequence is low-severity: they can simply re-run the tool.
- `format_detected` expansion (`"spdx"` → `"spdx-2.3"`) is a hardcoded mapping in `report_writer.py`. If a new format is added, `report_writer.py` must be updated alongside `format_detector.py`.

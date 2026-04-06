# sbom-validator

[![CI](https://github.com/SuceaCosmin/sbom-validator/actions/workflows/ci.yml/badge.svg)](https://github.com/SuceaCosmin/sbom-validator/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

A CLI tool to validate Software Bill of Materials (SBOM) files against format schemas and NTIA minimum element requirements.

Supports **SPDX 2.3 JSON** and **CycloneDX 1.6 JSON**.

---

## Quick Start

```bash
# Install with pipx (recommended)
pipx install sbom-validator

# Validate an SBOM file
sbom-validator validate my-app.spdx.json

# Get structured JSON output (useful in CI/CD)
sbom-validator validate my-app.cdx.json --format json
```

Exit codes: `0` = PASS, `1` = FAIL (validation issues found), `2` = ERROR (tool could not process the file).

---

## What It Checks

Every SBOM is validated in two sequential stages:

**Stage 1 — Schema Conformance**  
The file is checked against the official JSON schema for its format (`spdx-2.3.schema.json` or `cyclonedx-1.6.schema.json`). All schema errors are collected and reported. If schema validation fails, NTIA checking is skipped.

**Stage 2 — NTIA Minimum Elements**  
The file is checked against the seven elements mandated by the NTIA "Framing Software Component Transparency" guidance:

| NTIA Element | FR | What is checked |
|---|---|---|
| Supplier Name | FR-04 | Every component must have a non-empty supplier |
| Component Name | FR-05 | Every component must have a non-empty name |
| Component Version | FR-06 | Every component must have a non-empty version |
| Unique Identifiers | FR-07 | Every component must have at least one PURL or CPE |
| Dependency Relationships | FR-08 | The SBOM must declare at least one relationship |
| Author | FR-09 | The SBOM must identify at least one author |
| Timestamp | FR-10 | The SBOM must include a creation timestamp |

All issues from both stages are reported in a single pass — the tool never stops at the first error.

---

## Installation

### pipx (recommended)

```bash
pipx install sbom-validator
```

### pip

```bash
pip install sbom-validator
```

### From source

```bash
git clone https://github.com/SuceaCosmin/sbom-validator.git
cd sbom-validator
poetry install
```

---

## CLI Reference

```
Usage: sbom-validator validate [OPTIONS] FILE

  Validate an SBOM file against schema and NTIA minimum elements.

Options:
  --format [text|json]  Output format (default: text)
  --help                Show this message and exit.
```

### Text output (default)

```
File:   my-app.spdx.json
Format: spdx
Status: FAIL

Issues (3):
  [ERROR] components[2].supplier — Component 'libfoo' is missing a supplier name (NTIA FR-04)
  [ERROR] components[2].version  — Component 'libfoo' is missing a version (NTIA FR-06)
  [ERROR] relationships          — SBOM declares no dependency relationships (NTIA FR-08)
```

### JSON output (`--format json`)

```json
{
  "status": "FAIL",
  "file": "my-app.spdx.json",
  "format_detected": "spdx",
  "issues": [
    {
      "severity": "ERROR",
      "field_path": "components[2].supplier",
      "message": "Component 'libfoo' is missing a supplier name (NTIA FR-04)",
      "rule": "FR-04"
    }
  ]
}
```

---

## CI/CD Integration

### GitHub Actions

```yaml
- name: Validate SBOM
  run: sbom-validator validate sbom/my-app.spdx.json --format json | tee sbom-results.json
```

### GitLab CI

```yaml
validate-sbom:
  script:
    - sbom-validator validate sbom/my-app.cdx.json
```

---

## Supported Formats

| Format | Version | Detection |
|--------|---------|-----------|
| SPDX JSON | 2.3 only | `spdxVersion == "SPDX-2.3"` |
| CycloneDX JSON | 1.6 only | `bomFormat == "CycloneDX"` + `specVersion == "1.6"` |

Files with unsupported versions (e.g., SPDX 2.2 or CycloneDX 1.5) are rejected with exit code `2` and a clear error message. Format detection is based on file content, not file extension.

---

## Documentation

- [User Guide](docs/user-guide.md) — full installation, usage, and troubleshooting
- [Architecture Overview](docs/architecture/architecture-overview.md) — module design and pipeline
- [Requirements](docs/requirements.md) — functional and non-functional requirements

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

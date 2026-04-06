# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-06

### Added
- SPDX 2.3 JSON format validation against the official SPDX 2.3 JSON schema
- CycloneDX 1.6 JSON format validation against the official CycloneDX 1.6 JSON schema
- NTIA minimum elements compliance checking for all 7 required fields:
  - Supplier Name (FR-04)
  - Component Name (FR-05)
  - Component Version (FR-06)
  - Other Unique Identifiers / PURL / CPE (FR-07)
  - Dependency Relationships (FR-08)
  - Author of SBOM Data (FR-09)
  - Timestamp (FR-10)
- CLI with `validate` command supporting text (default) and JSON output modes
- Exit codes for CI/CD integration: 0 (PASS), 1 (FAIL), 2 (ERROR)
- Format auto-detection from JSON file content (spdxVersion / bomFormat fields)
- Version validation: raises error for unsupported SPDX versions (only 2.3 supported)
  and unsupported CycloneDX versions (only 1.6 supported)
- Two-stage validation pipeline: schema validation gates NTIA checking
- Bundled official JSON schemas (no network access required at validation time)
- Collect-all error reporting: all validation issues reported in a single run

### Technical
- Python 3.11 and 3.12 support
- 358 unit and integration tests with 97% code coverage
- Zero mypy errors, zero ruff lint errors

[Unreleased]: https://github.com/SuceaCosmin/sbom-validator/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SuceaCosmin/sbom-validator/releases/tag/v0.1.0

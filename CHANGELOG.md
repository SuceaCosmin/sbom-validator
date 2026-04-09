# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2026-04-09

### Fixed
- Standalone binary (`sbom-validator.exe` / `sbom-validator`) was silently exiting with code 0
  and producing no output on all previous releases. Root cause: missing `if __name__ == '__main__'`
  guard in `cli.py` — PyInstaller executes the script directly and Click was never invoked.
- CycloneDX XML support (`xmlschema` / `elementpath` packages) not bundled in the standalone
  binary due to missing `collect_submodules()` and `collect_data_files()` entries in the
  PyInstaller spec. Binary would crash silently before processing any XML file.
- ISO 8601 timestamp validation (FR-10) now enforced strictly in NTIA checker.
- `ERROR` validation results now always include at least one structured issue entry.
- Report writer now uses a single UTC timestamp source for both filename and `generated_at` field.
- Fallback tool version in reports changed from hardcoded `"0.2.0"` to `"unknown"`.

### Added
- CycloneDX 1.6 XML format support: detection, strict XSD schema validation (Stage 1),
  and parsing to normalised SBOM model. Full parity with existing JSON pipeline.
- User-friendly validation output: XML namespace prefixes stripped from field paths,
  NTIA rule IDs removed from human-facing text/HTML output (retained in JSON),
  actionable hints added per issue, and a dedicated Hint column in HTML reports.
- Sandbox demo SBOMs in `sandbox/user-demo/` for manual testing across all supported formats.
- Binary smoke test script (`scripts/smoke-test-binary.sh`) covering 14 scenarios including
  startup, PASS/FAIL exit codes across all three formats, JSON output, and report generation.
- Pre-commit hooks (black + ruff) added to prevent lint/format CI failures at commit time.

### Technical
- 501 unit and integration tests passing on Python 3.11 and 3.12.
- Release CI smoke test upgraded from bare `--version` check to full `smoke-test-binary.sh`.

## [0.2.0] - 2026-04-08

### Added
- Structured logging via `--log-level` option (choices: DEBUG, INFO, WARNING, ERROR; default: WARNING). Log output is written exclusively to stderr, keeping stdout clean for `--format json` consumers.
- Post-execution HTML and JSON report generation via `--report-dir PATH` option. Both report files are always written together when the option is provided. Filename convention: `sbom-report-<basename>-<YYYYMMDD-HHMMSS>.html/.json`.
- Standalone binary distribution for Linux (amd64) and Windows (amd64), built with PyInstaller and published to GitHub Releases automatically when a version tag is pushed.

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

[Unreleased]: https://github.com/SuceaCosmin/sbom-validator/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/SuceaCosmin/sbom-validator/compare/v0.2.0...v0.2.2
[0.2.0]: https://github.com/SuceaCosmin/sbom-validator/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/SuceaCosmin/sbom-validator/releases/tag/v0.1.0

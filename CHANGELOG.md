# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-04-30

### Added
- SPDX 3.x JSON-LD format support (`format_detected: "spdx3-jsonld"`, version 3.0.1). Files are detected by the canonical `@context` URL at the document root; schema validation uses a JSON Schema Draft 2020-12 envelope validator; NTIA compliance checking uses a two-pass `@graph` parser that resolves `spdxId` cross-references.
- Full seven-check NTIA minimum element validation for SPDX 3.x files (FR-04 supplier via `suppliedBy` cross-reference; FR-05 component name; FR-06 `packageVersion`; FR-08 `DEPENDS_ON` relationships; FR-09 author via `creationInfo.createdBy` cross-reference; FR-10 `creationInfo.created` timestamp).
- New format constant `FORMAT_SPDX3_JSONLD = "spdx3-jsonld"` and supporting constants `SPDX3_CONTEXT_URL`, `SPDX3_SCHEMA_FILE`, `RULE_SPDX3_SCHEMA = "FR-15"` in `constants.py`.
- New parser module `parsers/spdx3_jsonld_parser.py` with public function `parse_spdx3_jsonld(file_path) -> NormalizedSBOM`.
- Bundled SPDX 3.0.1 JSON Schema (`spdx-3.0.1.schema.json`, Draft 2020-12) for schema-stage validation.
- Bundled CycloneDX auxiliary schemas (`spdx.schema.json`, `jsf-0.82.schema.json`) — previously missing, causing `jsonschema` to attempt remote-reference fetching and emit `DeprecationWarning` on every CycloneDX validation. All schema resolution is now fully local.
- ADR-010 documenting SPDX 3.x JSON-LD detection fingerprint, Draft 2020-12 validator choice, two-pass graph traversal, cross-reference resolution contract, and NTIA field mapping. ADR-001 amended with updated detection priority order.

### Technical
- 701 unit and integration tests passing on Python 3.11 (107 new tests added for SPDX 3.x).
- Zero `DeprecationWarning` instances in the test suite (previously 20 from CycloneDX schema remote-ref fetching).
- Zero mypy errors (strict mode), zero ruff lint/format errors.
- 96% overall code coverage.

## [0.5.0] - 2026-04-29

### Added
- Validation issues are now classified by category. Each `ValidationIssue` carries a `category` field with one of three values: `"FORMAT"` (format detection errors), `"SCHEMA"` (schema validation failures), or `"NTIA"` (NTIA minimum element failures). The `category` field appears in `--format json` stdout output, in the JSON report written by `--report-dir`, and groups issues in text and HTML output. (Issue #13)

### Fixed
- FR-07 (Other Unique Identifiers / PURL / CPE) NTIA check removed. The NTIA minimum elements guidance lists unique identifiers as a recommended best practice rather than a mandatory requirement; enforcing the check produced false positives on otherwise-compliant SBOMs. The `identifiers` field is still parsed and stored per component but is no longer validated. (Issues #11, #12)
- SPDX `DEPENDENCY_OF` relationship type is now recognized as a qualifying relationship for the FR-08 dependency check. Previously only `DEPENDS_ON`, `DYNAMIC_LINK`, `STATIC_LINK`, `RUNTIME_DEPENDENCY_OF`, and `DEV_DEPENDENCY_OF` were recognized; SBOMs that expressed relationships exclusively via `DEPENDENCY_OF` (the semantic inverse of `DEPENDS_ON`) were incorrectly reported as non-compliant. `OPTIONAL_DEPENDENCY_OF` is also now recognized. (Issues #11, #12)

### Changed
- Report filenames are now fixed and predictable: `sbom-report-<basename>.html` / `sbom-report-<basename>.json`. The `<YYYYMMDD-HHMMSS>` timestamp suffix has been removed to enable deterministic CI artefact references. The `generated_at` field inside the report content is unchanged.
- `--format json` stdout output now includes `"tool_version"` as the first key in the JSON object, making every machine-readable result self-identifying without requiring `--report-dir`.
- Running with `--log-level INFO` or `--log-level DEBUG` now emits `sbom-validator <version>` as the first log line to stderr, before any pipeline output.
- Report write failures (`OSError`, e.g. file locked by a JSON viewer) are now non-fatal: the tool warns to stderr and exits with the correct validation exit code (`0`, `1`, or `2`) rather than crashing.

## [0.4.0] - 2026-04-14

### Added
- SPDX 2.3 Tag-Value (`.spdx`) format support: format detection, schema validation
  explicitly skipped (no formal TV schema exists; a logged INFO notice is emitted),
  full NTIA compliance checking via a new line-oriented Tag-Value parser.
  `format_detected` surfaces `"spdx-tv"` in JSON output.
- SPDX 2.3 YAML (`.spdx.yaml`) format support: format detection, schema validation
  against the existing bundled `spdx-2.3.schema.json` (YAML is structurally identical
  to SPDX JSON), full NTIA compliance checking via a YAML-loading wrapper around the
  shared SPDX document parser. `format_detected` surfaces `"spdx-yaml"` in JSON output.
- New format constants `FORMAT_SPDX_TV = "spdx-tv"` and `FORMAT_SPDX_YAML = "spdx-yaml"`
  in `constants.py`.
- `pyyaml >= 6.0` runtime dependency (used via `yaml.safe_load` exclusively).
- `types-PyYAML` development dependency for mypy strict-mode compliance.
- ADR-009 documenting the multi-format detection strategy, schema validation policy,
  parser factoring, and YAML library choice.
- Fixture files for both new formats:
  `valid-full.spdx`, `valid-minimal.spdx`, `missing-supplier.spdx`, `missing-relationships.spdx`,
  `valid-full.spdx.yaml`, `valid-minimal.spdx.yaml`, `missing-supplier.spdx.yaml`,
  `invalid-schema.spdx.yaml`.

### Changed
- `detect_format()` detection priority extended: JSON → CycloneDX XML → SPDX Tag-Value
  → SPDX YAML → `UnsupportedFormatError`. Existing JSON and CycloneDX detection is unchanged.
- `validate_schema()` now accepts `"spdx-tv"` (returns empty list + log) and `"spdx-yaml"`
  (validates as JSON schema) in addition to existing `"spdx"` and `"cyclonedx"`.
- `spdx_parser.py` refactored to expose `_parse_spdx_document(document, source_label)` shared
  helper; `parse_spdx()` is a backward-compatible thin wrapper.

### Technical
- 594 unit and integration tests passing on Python 3.11 (78 new tests added).
- Zero mypy errors (strict mode), zero ruff lint/format errors.
- 96% overall code coverage.

## [0.3.0] - 2026-04-14

### Added
- CycloneDX multi-version support: the validator now accepts CycloneDX 1.3, 1.4, and 1.5 in addition
  to the previously supported 1.6, for both JSON and XML formats. Format detection, schema validation
  (Stage 1), and NTIA checking (Stage 2) all operate correctly across all four versions.
- Bundled official CycloneDX JSON schemas and XSD files for versions 1.3, 1.4, and 1.5
  (`cyclonedx-1.3.schema.json`, `cyclonedx-1.3.schema.xsd`, `cyclonedx-1.4.schema.json`,
  `cyclonedx-1.4.schema.xsd`, `cyclonedx-1.5.schema.json`, `cyclonedx-1.5.schema.xsd`).
  No network access is required at validation time.
- `CYCLONEDX_SUPPORTED_VERSIONS` constant expanded to `frozenset({"1.3", "1.4", "1.5", "1.6"})`,
  replacing the previously implicit single-version assumption.

### Technical
- 516 unit and integration tests passing on Python 3.11.
- Zero mypy errors, zero ruff lint/format errors.
- D1 security deferral from v0.2.2 resolved: `xmlschema`-based XSD loading path formally reviewed;
  no path traversal or unsafe XML parsing risk identified (see `docs/releases/TASKS-v0.3.0.md` G5).

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
- Post-execution HTML and JSON report generation via `--report-dir PATH` option. Both report files are always written together when the option is provided. Filename convention: `sbom-report-<basename>.html/.json`.
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

[Unreleased]: https://github.com/SuceaCosmin/sbom-validator/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/SuceaCosmin/sbom-validator/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/SuceaCosmin/sbom-validator/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/SuceaCosmin/sbom-validator/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/SuceaCosmin/sbom-validator/compare/v0.2.0...v0.2.2
[0.2.0]: https://github.com/SuceaCosmin/sbom-validator/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/SuceaCosmin/sbom-validator/releases/tag/v0.1.0

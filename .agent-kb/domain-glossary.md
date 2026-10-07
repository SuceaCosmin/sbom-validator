# Domain Glossary — sbom-validator

| Term | Meaning | Notes / where it appears |
|------|---------|--------------------------|
| SBOM | Software Bill of Materials — inventory of the components in a piece of software | The input the tool validates |
| SPDX 2.3 | Linux Foundation SBOM standard, version 2.3 | JSON (`spdx`), YAML (`spdx-yaml`), Tag-Value (`spdx-tv`) |
| SPDX 3.x | SPDX 3.0.1, JSON-LD serialisation with an `@graph` of elements | `spdx3-jsonld`; ADR-010 |
| Tag-Value (TV) | Line-oriented SPDX text format (`SPDXVersion: SPDX-2.3`) | Skips schema validation (ADR-009) |
| CycloneDX | OWASP SBOM standard, versions 1.3–1.6 | JSON and XML; `cyclonedx` |
| `bom-ref` | CycloneDX component reference id | Missing → fallback identifier |
| `spdxId` | SPDX element identifier used for cross-references | SPDX 3.x two-pass resolution |
| NTIA minimum elements | US NTIA baseline SBOM data fields | FR-04..FR-10 (FR-07 removed) |
| `NormalizedSBOM` | Format-agnostic internal model produced by every parser | Only input to the NTIA checker |
| `NOASSERTION` | SPDX sentinel meaning "no information" | Normalised to `None` |
| Format fingerprint | Root keys that identify a format (`spdxVersion`, `bomFormat`, `@context`) | Used by `format_detector.py` |
| Schema-invalid fixture | Fails schema validation but **keeps** the format fingerprint | Different from "unrecognized format" (see gotchas) |
| Collect-all | All issues in a stage are gathered in one pass rather than failing fast | ADR-003 |
| PASS / FAIL / ERROR | Validation outcomes → exit codes 0 / 1 / 2 | Compatibility Contract |
| FR-XX / NFR-XX | Functional / non-functional requirement IDs | `docs/requirements.md` |
| Rule code | Constant naming the requirement an issue violates (e.g. `RULE_SUPPLIER`, `RULE_SPDX3_SCHEMA="FR-15"`) | `constants.py` |
| Envelope schema | Inline minimal schema used for SPDX 3.x instead of the full vendor schema | ADR-010 Amendment 1 |

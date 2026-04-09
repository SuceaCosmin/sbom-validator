# SBOM Validator — Release Task Tracker (`v0.2.2`)

> Patch release: binary fix, CycloneDX XML support, UX improvements, and process hardening.

## Release Metadata

- **Release:** `v0.2.2`
- **Branch:** `develop` → `master`
- **Status:** `✅ Ready for Release`

## Scope

### In Scope
- Fix standalone binary (broken since v0.1.0 — no `__main__` guard, missing xmlschema bundling)
- CycloneDX 1.6 XML validation support (detected, schema-validated, parsed)
- User-facing output improvements (humanised paths, hints, no rule IDs in HTML/text)
- Binary smoke test script and CI gate upgrade
- Pre-commit hooks for lint/format prevention
- Version number alignment (`0.2.0` → `0.2.2`)

### Out of Scope
- New validation formats or rules
- Breaking CLI contract changes

---

## Task Breakdown

| ID | Task | Status |
|----|------|--------|
| R1 | CycloneDX XML detection, schema validation, parser | ✅ |
| R2 | UX output improvements (paths, hints, hint column) | ✅ |
| R3 | Fix `__main__` guard in cli.py | ✅ |
| R4 | Add `xmlschema`/`elementpath` hidden imports to spec | ✅ |
| R5 | Binary smoke test script (`scripts/smoke-test-binary.sh`) | ✅ |
| R6 | Upgrade CI release smoke test | ✅ |
| R7 | Pre-commit hooks (black + ruff) | ✅ |
| R8 | Version bump to 0.2.2 + CHANGELOG | ✅ |
| R9 | Release tracker (this file) | ✅ |

---

## Gate Evidence

| Gate | Status | Evidence |
|------|--------|----------|
| G1 Planning | ✅ | Scope confirmed, tracker created |
| G2 Architecture | ✅ | ADR-001 updated for CDX XML; no new ADR required |
| G3 TDD Build | ✅ | 501 tests passing (Python 3.11 + 3.12) |
| G4 Quality Review | ✅ | ruff, black, mypy all clean |
| G5 Security | ⚠️ Deferred | `xmlschema` dependency — formal review deferred to v0.3.x (D1) |
| G6 CI Stability | ✅ | Pre-commit hooks prevent recurrence; CI green |
| G7 Docs Sync | ✅ | CHANGELOG, README, ADRs updated |
| G8 Release Readiness | ✅ | Version consistent; smoke test passes 14/14 |
| G9 Token Analytics | ✅ | `docs/releases/token-report-v0.2.2.html` and `docs/releases/token-delta-v0.2.1_to_v0.2.2.html` generated. CI gate added to enforce pre-tag execution going forward. |

## Deferrals

| ID | Description | Severity | Planned Release |
|----|-------------|----------|-----------------|
| D1 | G5 Security review for `xmlschema` dependency | MEDIUM | v0.3.x |

## Final Verdict

- **Recommendation:** `GO` ✅
- **Approved by (Human):** SuceaCosmin
- **Date:** 2026-04-09
- **Notes:** Supersedes v0.2.1 binary. Fixes broken binary across all previous releases.

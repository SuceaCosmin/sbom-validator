# Gotchas — sbom-validator

> Hard-won traps. Agents add entries here (knowledge write-back) in the same PR that uncovered them.

## Import ordering (ruff I001) is the #1 CI failure cause
- **Symptom:** CI lint fails on files that look fine.
- **Cause:** third-party and first-party (`sbom_validator`) imports mixed in one block, or `from __future__` not first.
- **Rule:** four groups with blank lines — `__future__`, stdlib, third-party, first-party. Write them correctly; don't rely on `ruff --fix`. Applies to tests too.

## jsonschema validators must always get `registry=`
- **Symptom:** non-deterministic failures in air-gapped environments; hidden network access.
- **Cause:** a validator without an explicit `registry=` falls back to remote HTTP `$ref` resolution, violating "no network calls at runtime" (ADR-003).
- **Rule:** never instantiate `Draft7Validator`, `Draft202012Validator` or any jsonschema validator without `registry=`. Use `registry=_build_cdx_registry()` for CycloneDX; `registry=Registry()` (empty, isolating) for schemas without external `$ref` targets.

## Schema-invalid fixtures must keep their format fingerprint
- **Symptom:** a "schema-invalid" test yields exit 2 / unrecognized format instead of a schema FAIL.
- **Cause:** the fixture dropped `spdxVersion` / `bomFormat` / `@context`, so format detection failed first.
- **Rule:** schema-invalid fixtures fail JSON-schema validation but still contain the fingerprint. "Unrecognized format" is a separate scenario.

## Lint fixes lost after rebase
- **Symptom:** CI fails on issues that were fixed locally.
- **Cause:** pre-commit hooks do not fire during `git rebase`, so commit-time fixes can be lost.
- **Rule:** after any rebase/merge, re-run `quality_gate` from scratch and commit any fixes before pushing.

## Vendor schema quirks must go through an ADR amendment (v0.6.0, G4 M-01)
- **Symptom:** a silent workaround for a vendor-schema incompatibility was committed and caught at G4, causing a rework loop.
- **Cause:** generated schema artefacts (e.g. `if/then/else` branches, `$ref AnyClass` catch-alls) blocked the ADR's approach mid-implementation.
- **Rule:** stop, raise to the architect, amend the ADR, then implement (see ADR-010 Amendment 1).

## Click path validation must not pre-empt the structured ERROR contract (v0.6.1, R-12)
- **Symptom:** a plain `click.Path(exists=True)` on `FILE` makes a missing file a Click usage error (exit 2, stderr, no JSON on stdout, no reports).
- **Rule:** keep `_LenientExistingPath` in `cli.py`; it swallows only `click.BadParameter` and passes the raw argument to `validate()`. Re-verify this on any Click major upgrade (see ADR-005 Amendment 1).

## Binary builds need frozen-mode paths
- **Symptom:** the binary cannot find schemas.
- **Cause:** schema paths resolved relative to source files break under PyInstaller.
- **Rule:** keep `_schemas_dir()` `sys._MEIPASS`-compatible and schemas bundled via `datas` in `sbom_validator.spec`, which globs every `*.json`/`*.xsd` from `src/sbom_validator/schemas/` (the build fails if none are found), so new schemas need no spec edit (ADR-008).

## Version drift across meta-documents every release
- **Symptom:** stale version numbers / format tables after release.
- **Cause:** no owner for reference documents.
- **Rule:** the release closeout task updates every file in `drift_prone_docs` (CLAUDE.md, `.agent-kb/architecture.md`, `docs/requirements.md` header and JSON examples, the `NormalizedSBOM.format` docstring in `models.py`).

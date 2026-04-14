# Release Task Tracker Convention

This directory stores one task tracker per release cycle.

## Naming

- Required file pattern: `TASKS-v<MAJOR>.<MINOR>.<PATCH>.md`
- Examples:
  - `TASKS-v0.2.1.md`
  - `TASKS-v0.3.0.md`

## Purpose

- Track release-specific planning, execution, status, and evidence.
- Provide a canonical progress source for the current release in flight.
- Keep top-level `TASKS.md` as historical/global context, not detailed release execution.

## Required Workflow

At release planning start:
1. Create `docs/releases/TASKS-vX.Y.Z.md` from `docs/releases/TASKS-template.md`
2. Populate task breakdown with owner, dependencies, and acceptance criteria
3. Update statuses during execution (`✅`, `🔄`, `⏳`, `🔒`, `❌`)

Before release approval:
1. Confirm all tasks are resolved or explicitly deferred with rationale
2. Ensure tracker contents align with changelog and release brief
3. Link the tracker in PR/release notes when possible

## Required Analytics Reports (mandatory for each release)

Each release must include the following reports before the release tag is pushed.
Both are CI-enforced in `.github/workflows/release.yml`.

1. `docs/releases/token-report-vX.Y.Z.html`
   - Token usage evaluation for the release
2. `docs/releases/token-delta-vA.B.C_to_vX.Y.Z.html`
   - Delta analysis vs previous release
3. `docs/releases/workflow-report-vX.Y.Z.html`
   - Per-agent efficiency evaluation, gate compliance analysis, and benchmark vs previous release

If a release spans multiple work sessions, aggregate all sessions into the same
release token report and provide per-session subtotals plus a release total.

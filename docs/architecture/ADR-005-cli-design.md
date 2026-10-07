# ADR-005: CLI Design

## Status

Accepted. Amended by Amendment 1 (v0.6.1, see end of document).

## Context

`sbom-validator` is a command-line tool that CI/CD pipelines will invoke. The CLI must be:

- Scriptable: well-defined exit codes (FR-13) that pipeline gates can branch on.
- Discoverable: `--help` output that tells operators how to use it without consulting documentation.
- Extensible: the command structure should accommodate future subcommands (e.g., `validate`, `report`, `inspect`) without a breaking redesign.
- Lightweight: the CLI layer should not add heavy transitive dependencies to the package.

Two Python CLI frameworks were considered: **Click** and **Typer**.

**Click** is a mature, widely adopted framework for building Python CLIs. It uses Python decorators to define commands, options, and arguments. Click has no mandatory transitive dependencies beyond `colorama` on Windows. It is the CLI foundation used by many tools in the Python packaging and security ecosystem, including `pip`, `black`, `twine`, and — most relevantly — the `cyclonedx-bom` reference implementation and tools in the SPDX Python ecosystem.

**Typer** is a newer framework built on top of Click that uses Python type annotations and function signatures to declare CLI parameters. Its primary appeal is reduced boilerplate. However, Typer has a documented optional but commonly installed dependency on `rich` for enhanced output, and its dependency chain includes indirection through Click anyway (Typer is a wrapper, not a replacement). More importantly, Typer's design is optimized for simple, single-file CLIs; complex nested command groups require more effort than in Click. Typer also introduces a layer of "magic" (annotation introspection) that can produce confusing behavior when combined with `mypy` strict mode.

The deciding factors in favor of Click:

1. **Ecosystem alignment**: tools that users will likely run alongside `sbom-validator` (CycloneDX Python library, SPDX tools) already depend on Click. Adding Click does not add net new dependencies in the common installation scenario.
2. **Stability**: Click's API has been stable across major versions. Typer's API has changed more frequently as the project matures.
3. **No hidden dependency chain**: Click's extras are optional. Typer's `rich` integration, while optional, is often pulled in by default installation patterns.
4. **mypy compatibility**: Click's decorator-based API plays cleanly with mypy strict mode. Typer's annotation introspection can require workarounds for strict mode.

## Decision

The CLI is implemented using **Click**, with the following structure:

**Top-level group:**

```
sbom-validator [--version] [--help]
```

Implemented as a Click group (`@click.group()`), enabling future subcommands.

**`validate` subcommand:**

```
sbom-validator validate <FILE> [--format text|json]
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `FILE` | Click path argument (see Amendment 1; originally specified as `Path(exists=True)`, but shipped as `Path(exists=False)` through v0.6.0) | (required) | Path to the SBOM file to validate |
| `--format` | Click `Choice(["text", "json"])` option | `text` | Output format |

> **Correction (Amendment 1):** the original text of this ADR stated that `FILE` used `click.Path(exists=True)` to fail early with a Click usage error. That was never the implemented behaviour: the argument has been `click.Path(exists=False)` since v0.1.0, and a missing file is reported by `validate()` as a structured `ERROR` result (exit 2, text/JSON on stdout, `--report-dir` reports written). That structured behaviour is the intended and contract-locked one; a Click usage error (stderr only, no JSON) would violate the stdout/JSON contract. See Amendment 1 for how `exists=True` semantics are now applied without losing it.

**Exit codes:**

Click's `ctx.exit(code)` or `sys.exit(code)` is called explicitly after rendering output:

| Code | Condition |
|---|---|
| `0` | `ValidationResult.status == PASS` |
| `1` | `ValidationResult.status == FAIL` |
| `2` | `ValidationResult.status == ERROR` or any unexpected exception |

Unexpected exceptions (not caught by the validator's own error handling) are caught at the CLI boundary, formatted as an `ERROR`-status result, written to the selected output format, and exit with code `2`. This ensures the JSON output contract (FR-11) is upheld even on unexpected failures.

**`--version` flag:**

Implemented via Click's `@click.version_option()` decorator. The version string is read from the package metadata (`importlib.metadata.version("sbom-validator")`), keeping it in sync with `pyproject.toml` without duplication.

**Output rendering:**

The `validate` subcommand calls `validate(file_path)` from the core library, receives a `ValidationResult`, and dispatches to either `render_text(result)` or `render_json(result)` based on `--format`. Renderers write to `stdout`. All diagnostic messages unrelated to validation output (e.g., "Reading file...") are prohibited — `stdout` must be clean for JSON mode to be machine-parseable.

## Consequences

**Positive:**

- Click is already likely present in the environment given ecosystem overlap, reducing net dependency additions.
- The `@click.group()` structure allows future subcommands (`sbom-validator report`, `sbom-validator inspect`) without a CLI redesign.
- ~~`click.Path(exists=True)` provides clean, early validation of the file path argument with Click's standard error messaging.~~ Withdrawn: see Amendment 1. A missing file is reported via the structured `ERROR` result, not Click's usage error.
- `@click.version_option()` with `importlib.metadata` keeps version management in one place (`pyproject.toml`).
- Exit codes are explicit integers in the Click handler, making them easy to find and audit.

**Negative:**

- Click's decorator syntax is more verbose than Typer's annotation-based style, requiring more lines of code for equivalent functionality. This is a stylistic trade-off, not a functional one.
- Click does not automatically generate shell completion scripts for all shells without additional setup (though `click.shell_completion` is available for bash/zsh/fish). This is deferred to a future version.
- Click's testing utilities (`CliRunner`) add a minor learning curve for contributors unfamiliar with Click internals, though they are well-documented.

---

## Amendment 1 (v0.6.1): `FILE` uses an `exists=True`-based path type that preserves structured ERROR output

Status: Accepted (design, task 1.B1). Closes review item R-12. Supersedes nothing; the exit-code and output decisions above are unchanged.

### Context

Review item R-12 asked that the `FILE` argument of `validate` use `click.Path(exists=True)`, as this ADR originally claimed. Verified facts:

1. The code uses `click.Path(exists=False)` (`src/sbom_validator/cli.py`, `validate_cmd`). The original ADR text was wrong about the implementation.
2. Plain `click.Path(exists=True)` fails during parameter parsing, before the command body runs. Click emits `Error: Invalid value for 'FILE': ... does not exist.` plus usage on **stderr**, and exits with code 2. The exit code coincides with the contract, but the stdout contract breaks: `--format json` would produce no JSON, text mode no `Status: ERROR` block, and `--report-dir` would write nothing. The Compatibility Contract (stable JSON output, structured ERROR, fixed-name reports) forbids this.
3. Behaviour today for a directory passed as `FILE`: `validate()` returns `ERROR` with a single `FR-01` issue, message `Cannot read file: <path>`, `file` equal to the raw argument; exit 2. A missing file returns `ERROR` with `File not found: <path>`. Both verified against the repo at v0.6.0. (The directory case on Linux should be re-verified by the tests at 2.C1; the code path is the same `detect_format` read failure.)
4. Locked dependency: click 8.3.2. `click.Path.convert(self, value: str | os.PathLike[str], param: Parameter | None, ctx: Context | None) -> str | bytes | os.PathLike[str]`. All failures are raised via `self.fail()`, which raises `click.BadParameter` (a `click.UsageError`/`ClickException` subclass). With `path_type=None` and `resolve_path=False` (defaults), the returned value is the raw argument unchanged, so `file` equals the raw argument.

### Decision

Introduce a private `click.Path` subclass in `cli.py` (no new module, no new dependency):

- It is constructed with `exists=True` (so the declared parameter semantics, `--help` metavar and shell-completion hints state that the argument is an existing path), `dir_okay=True`, `file_okay=True`, and otherwise Click defaults.
- It overrides `convert()`: it delegates to `super().convert()` and catches `click.BadParameter`. On failure (missing path, or unreadable path) it returns the raw `str(value)` unchanged. It never raises for a path problem, never writes to stderr, and never alters the value.
- `validate_cmd` is unchanged apart from the decorator type: the value flows into `validate(Path(file))`, which already produces the structured `ERROR` result for missing files, directories and unreadable files. Single code path, no duplicated error rendering.
- `dir_okay` stays `True` on purpose. Setting `dir_okay=False` would add a second failure class that the interceptor would also swallow, with no behavioural difference. A directory continues to flow into `validate()` and yields structured `ERROR`, exit 2 (human decision at H1: confirmed).
- Exit-code and rendering behaviour: exit 2, `Status: ERROR` text or the JSON object on stdout, reports written when `--report-dir` is given, `file` field equal to the raw argument, logs on stderr only.

### Interface stub

```python
# src/sbom_validator/cli.py  (private; not part of the public API)
from __future__ import annotations

import os

import click


class _LenientExistingPath(click.Path):
    """click.Path(exists=True) that defers path problems to validate().

    A missing or unreadable path does not abort argument parsing; the raw
    argument string is passed through so that validate() reports a
    structured ERROR result (exit 2, output on stdout, reports written).
    """

    def __init__(self) -> None:
        super().__init__(exists=True, file_okay=True, dir_okay=True)

    def convert(
        self,
        value: str | os.PathLike[str],
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> str:
        try:
            super().convert(value, param, ctx)
        except click.BadParameter:
            pass
        return os.fspath(value)


# Usage:
# @click.argument("file", type=_LenientExistingPath())
```

Notes for the implementer: `os.fspath(value)` returns `str` for `str`/`PathLike[str]` input, satisfying mypy strict with the narrower `-> str` return (covariant override of `str | bytes | os.PathLike[str]`). Discarding the result of `super().convert()` is deliberate: `resolve_path` is off, so the result equals the input. Keep imports in the four-group order required by the repo conventions. Do not catch broader exceptions than `click.BadParameter`.

### Alternatives considered

- **Custom `click.Command` subclass overriding `parse_args`/`invoke` to catch `UsageError`.** Rejected: it intercepts every usage error (bad `--format`, unknown options, missing FILE), which must remain Click usage errors; it couples to Click internals and complicates `main`/group wiring.
- **Plain `exists=True`.** Rejected: breaks the stdout/JSON/`--report-dir` contract for a missing file (see Context 2).
- **`exists=False` (status quo) with a docstring fix only.** Viable and zero-risk, but rejected by the human at H1 in favour of closing R-12 with the declared `exists=True` semantics.
- **`dir_okay=False`.** Rejected, see Decision.

### Consequences

**Positive:** The argument's declared semantics match the ADR's intent. A single error path remains. No new module, dependency or public API.

**Negative / honest trade-off (risk K2):** Because the interceptor swallows the failure, `exists=True` is effectively behaviour-neutral. The benefit is declarative and documentary (help/completion metadata, one code path), not a new validation outcome. The subclass depends on Click's `Path.convert` raising `click.BadParameter`; this holds for click 8.3.2 (locked), and a Click major upgrade should re-verify it (a regression test with a missing file, JSON mode, will fail loudly if it does not).

**Compatibility Contract:** No locked surface changes. Command and option names, exit codes (0/1/2), JSON keys (`status`, `file`, `format_detected`, `issues`), stdout/stderr separation, and `--report-dir` file names are all unchanged, and observable behaviour for missing files and directories is identical to v0.6.0. Hence a PATCH release with no migration notes.

**Required tests (to be written at 2.C1):** missing file with `--format json` (valid JSON on stdout, `status` ERROR, `file` equals the raw argument, exit 2); missing file in text mode; missing file with `--report-dir` (reports written); directory as `FILE` (ERROR, exit 2); existing valid file unchanged; unreadable-path interception where portable.

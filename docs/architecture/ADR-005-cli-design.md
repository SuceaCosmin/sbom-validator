# ADR-005: CLI Design

## Status

Accepted

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
| `FILE` | Click `Path(exists=True)` argument | (required) | Path to the SBOM JSON file to validate |
| `--format` | Click `Choice(["text", "json"])` option | `text` | Output format |

The `FILE` argument uses `click.Path(exists=True)` to produce a clear "file not found" error before any validation logic runs, rather than catching a `FileNotFoundError` deep in the validator stack.

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
- `click.Path(exists=True)` provides clean, early validation of the file path argument with Click's standard error messaging.
- `@click.version_option()` with `importlib.metadata` keeps version management in one place (`pyproject.toml`).
- Exit codes are explicit integers in the Click handler, making them easy to find and audit.

**Negative:**

- Click's decorator syntax is more verbose than Typer's annotation-based style, requiring more lines of code for equivalent functionality. This is a stylistic trade-off, not a functional one.
- Click does not automatically generate shell completion scripts for all shells without additional setup (though `click.shell_completion` is available for bash/zsh/fish). This is deferred to a future version.
- Click's testing utilities (`CliRunner`) add a minor learning curve for contributors unfamiliar with Click internals, though they are well-documented.

# ADR-006: Structured Logging Design

## Status

Accepted

## Context

As `sbom-validator` matures toward production use in CI/CD pipelines, operators need visibility into what the tool is doing without polluting the validation output. Three concerns drive this decision:

1. **Stdout purity:** ADR-005 established that `--format json` writes a machine-readable JSON object to stdout. Any diagnostic text interleaved with that output would corrupt the JSON, breaking downstream parsers. Logging must never touch stdout.

2. **Signal-to-noise in normal operation:** Most CI runs succeed. Emitting INFO-level chatter on every run adds noise to build logs. The default behavior must be quiet.

3. **Debuggability when things go wrong:** When a file is unexpectedly rejected, operators need a way to see exactly which pipeline stage failed and why, without recompiling or patching the tool.

The Python standard library `logging` module satisfies all three concerns without adding any new dependencies. Third-party logging libraries (structlog, loguru, etc.) were considered and rejected: they add transitive dependencies, their configuration APIs differ from the stdlib, and they provide no meaningful benefit for a single-binary CLI tool.

This decision satisfies FR-14 (operator observability) and NFR-03 (zero-noise default operation).

## Decision

### New CLI Option

The `validate` subcommand gains a `--log-level` option:

```
sbom-validator validate <FILE> [--format text|json] [--log-level LEVEL]
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--log-level` | `Choice(["DEBUG","INFO","WARNING","ERROR"], case_sensitive=False)` | `WARNING` | Minimum severity of log messages emitted to stderr |

When `--log-level` is **omitted**, logging runs at `WARNING` level. This means the tool is not silent — genuine warnings are always surfaced — but INFO and DEBUG messages (which are high-volume) are suppressed during normal operation.

### New Module: `logging_config.py`

A `src/sbom_validator/logging_config.py` module provides a single public function called once at CLI startup, before the pipeline runs:

```python
# src/sbom_validator/logging_config.py

import logging
import sys


LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def configure_logging(level: str) -> None:
    """Configure the root sbom_validator logger.

    Sets up a single StreamHandler writing to stderr with a standard
    format string.  Must be called once, at CLI startup, before any
    pipeline module is imported or invoked.

    Args:
        level: One of "DEBUG", "INFO", "WARNING", "ERROR"
               (case-insensitive).  Invalid values are silently
               coerced to "WARNING" to preserve the no-noise default.
    """
    numeric = getattr(logging, level.upper(), logging.WARNING)
    logger = logging.getLogger("sbom_validator")
    logger.setLevel(numeric)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(numeric)
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
```

`configure_logging` MUST be called before any other `sbom_validator` module logs a message. The correct call site is the `validate_cmd` Click handler in `cli.py`, as the very first statement of the function body.

### Interface Contract (Python stub)

```python
# logging_config.py

import logging
import sys

LOG_FORMAT: str
DATE_FORMAT: str

def configure_logging(level: str) -> None: ...
```

### Logger Naming Convention

All loggers in the project follow the `sbom_validator.<module_name>` hierarchy:

| Module | Logger name |
|---|---|
| `cli.py` | `sbom_validator.cli` |
| `format_detector.py` | `sbom_validator.format_detector` |
| `schema_validator.py` | `sbom_validator.schema_validator` |
| `parsers/spdx_parser.py` | `sbom_validator.spdx_parser` |
| `parsers/cyclonedx_parser.py` | `sbom_validator.cyclonedx_parser` |
| `ntia_checker.py` | `sbom_validator.ntia_checker` |
| `validator.py` | `sbom_validator.validator` |
| `report_writer.py` | `sbom_validator.report_writer` |

Each module acquires its logger at module level via:

```python
import logging
log = logging.getLogger(__name__)
```

Because `__name__` follows the package hierarchy, this automatically satisfies the naming convention.

### Log Points Per Module

The following table defines the **required** log points. These are the minimum contract; modules may add additional DEBUG-level messages for internal state.

**`cli.py`**

| Event | Level | Message template |
|---|---|---|
| Tool startup | INFO | `"sbom-validator %s"` (version string, emitted immediately after `configure_logging`) |

This is always the first log line when INFO or DEBUG level is active. It appears before any pipeline module logs, giving operators an immediate version fingerprint in the log stream.

**`format_detector.py`**

| Event | Level | Message template |
|---|---|---|
| Format identified | INFO | `"Format detected: %s (file: %s)"` |
| Unsupported format or version | WARNING | `"Unsupported format in %s: %s"` |
| JSON parse failure | WARNING | `"Failed to parse JSON from %s: %s"` |

**`schema_validator.py`**

| Event | Level | Message template |
|---|---|---|
| Schema validation begins | DEBUG | `"Running schema validation for format %s"` |
| Schema validation passes | INFO | `"Schema validation passed (%d issues)"` |
| Schema validation finds errors | INFO | `"Schema validation found %d error(s)"` |

**`parsers/spdx_parser.py` and `parsers/cyclonedx_parser.py`**

| Event | Level | Message template |
|---|---|---|
| Parse begins | DEBUG | `"Parsing %s as %s"` |
| Parse succeeds | DEBUG | `"Parsed %d component(s), %d relationship(s)"` |
| Parse raises ParseError | WARNING | `"Parse error in %s: %s"` |

**`ntia_checker.py`**

| Event | Level | Message template |
|---|---|---|
| NTIA check begins | DEBUG | `"Running NTIA minimum elements check"` |
| NTIA check completes | INFO | `"NTIA check completed: %d issue(s)"` |

**`validator.py`**

| Event | Level | Message template |
|---|---|---|
| Pipeline begins | INFO | `"Validation started for: %s"` |
| Stage transitions | DEBUG | `"Stage %s → %s"` |
| Pipeline completes | INFO | `"Validation completed: status=%s, issues=%d"` |
| Any unexpected exception caught | ERROR | `"Unexpected error during validation of %s: %s"` |

### Log Format String

```
%(asctime)s %(levelname)-8s %(name)s — %(message)s
```

Example output lines (INFO level, first two lines of a typical run):

```
2026-04-08T14:22:01Z INFO     sbom_validator.cli — sbom-validator 0.4.0
2026-04-08T14:22:01Z INFO     sbom_validator.validator — Validation started for: bom.json
```

- `%(asctime)s` uses `datefmt="%Y-%m-%dT%H:%M:%SZ"` for UTC-like ISO 8601 display. (Note: the stdlib `logging` module uses local time by default; to emit genuine UTC, the handler's formatter subclass must override `converter = time.gmtime`. This is implemented in `configure_logging`.)
- `%(levelname)-8s` left-pads to 8 characters for columnar alignment.
- `%(name)s` is the full dotted logger name for traceability.

### Logging When `--log-level` Is Omitted

When `--log-level` is not supplied, `configure_logging("WARNING")` is called. This means:

- DEBUG and INFO messages are suppressed.
- WARNING messages are emitted. This is intentional: genuine warnings (e.g., a deprecated field encountered during parsing) should always reach the operator, even in quiet mode.
- The tool does NOT run silently by default. Silent-by-default (`ERROR` level) was considered but rejected because it would hide actionable warnings that do not constitute failures.

### stdout/stderr Separation Guarantee

`configure_logging` attaches a `StreamHandler(sys.stderr)` handler exclusively. No log record ever writes to `sys.stdout`. This is a hard requirement that preserves the stdout JSON contract established in ADR-005.

Click's `click.echo()` (used for validation output) writes to stdout. These two streams are independent and will not interleave.

## Consequences

**Positive:**

- Zero new dependencies: `logging`, `sys` are stdlib modules.
- The `WARNING` default ensures no log noise in passing CI runs while still surfacing genuine warnings.
- The `sbom_validator.*` logger hierarchy allows library consumers who embed `sbom_validator` to configure logging independently via standard `logging` configuration mechanisms.
- `configure_logging` is idempotent with respect to handler duplication (checks `logger.handlers` before adding).

**Negative:**

- The stdlib `logging` module does not emit structured (JSON) logs. If a future requirement calls for machine-readable log output, this decision would need to be revisited (create ADR-NNN to supersede).
- Timestamps in log output reflect the local system clock unless the `converter` override is applied. The `configure_logging` implementation must remember to set `formatter.converter = time.gmtime` for true UTC output — this is a subtle stdlib requirement.
- `configure_logging` must be called before any module-level code logs a message. Python's module import system makes this ordering constraint invisible; it must be enforced by convention and documented in the briefing.

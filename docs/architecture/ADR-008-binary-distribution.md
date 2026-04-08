# ADR-008: Binary Distribution Toolchain

## Status

Accepted

## Context

`sbom-validator` is distributed primarily as a Python package installable via `pip`. However, several target user groups — security auditors, compliance teams, and operators in air-gapped environments — cannot or will not install Python and a virtual environment. They need a standalone executable that can be dropped onto a system and run directly.

Two Python-to-binary toolchains were evaluated:

**PyInstaller >= 6.0** bundles a Python interpreter and all imported modules into a single executable. It has broad ecosystem support, an active community, excellent documentation for handling data files and hidden imports, and is the most widely used tool for this purpose in the Python security/DevSecOps space. Its spec file format (`*.spec`) is a plain Python script, making it auditable and version-controllable.

**Nuitka** compiles Python source to C and then to native code via a C compiler. It produces smaller, faster binaries, but requires a C compiler toolchain on the build host, produces much longer build times, and has historically had compatibility issues with heavy import-time side effects in packages like `spdx-tools` and `cyclonedx-bom`. The CI matrix would require installing GCC/MSVC on every runner.

PyInstaller is chosen because:

1. No C compiler required — simpler CI matrix.
2. The spec file is the single source of truth for bundling: datas, hiddenimports, and excludes are explicit and reviewable.
3. PyInstaller's `--onefile` mode produces a single-file executable that satisfies the "drop and run" distribution requirement.
4. PyInstaller >= 6.0 supports Python 3.11 and 3.12 and has native support for `importlib.resources` path resolution in frozen bundles.

This decision satisfies NFR-05 (standalone binary distribution) and NFR-06 (cross-platform release artifacts).

## Decision

### Toolchain

- **PyInstaller >= 6.0**, added to `[tool.poetry.group.dev.dependencies]` in `pyproject.toml`.
- Build mode: `--onefile` (single executable file).
- Entry point: `src/sbom_validator/cli.py:main` (the Click group).

### Output Artifact Names

| Platform | Artifact name |
|---|---|
| Linux (ubuntu-latest) | `sbom-validator` |
| Windows (windows-latest) | `sbom-validator.exe` |

Both artifacts are uploaded to the GitHub Release associated with the triggering tag.

### Schema File Bundling

`schema_validator.py` loads schemas via a `__file__`-relative path:

```python
_SCHEMAS_DIR = Path(__file__).parent / "schemas"
```

In a PyInstaller frozen binary, `__file__` is not available in the expected way; the bundle root is at `sys._MEIPASS` (the temp directory where `--onefile` extracts itself). The source code must be updated to use a compatibility shim:

```python
# schema_validator.py  — frozen-compatible schema path resolution

import sys
from pathlib import Path


def _schemas_dir() -> Path:
    """Return the path to the bundled schemas directory.

    Works in both normal (development) and PyInstaller frozen modes.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "schemas"
    return Path(__file__).parent / "schemas"
```

`_SCHEMAS_DIR` is replaced by a call to `_schemas_dir()` at the point of use (either at module level or lazily inside `_load_schema`). The lazy approach is preferred because `sys._MEIPASS` is only valid after the binary has extracted itself, which occurs before any user code runs in practice but is safer to access lazily.

The `sbom_validator.spec` file must declare both schema files in the `datas` list using PyInstaller's `(source, dest)` tuple format:

```python
datas=[
    (str(schemas_dir / "spdx-2.3.schema.json"), "schemas"),
    (str(schemas_dir / "cyclonedx-1.6.schema.json"), "schemas"),
]
```

The destination `"schemas"` is a relative path inside the bundle; it maps to `sys._MEIPASS/schemas/` at runtime.

### Hidden Imports

PyInstaller performs static analysis to discover imports. Several modules used by `spdx-tools` and `cyclonedx-bom` use dynamic imports (plugin systems, entry points) that static analysis misses.

However, `sbom-validator` does **not** use `spdx-tools` or `cyclonedx-bom` in its critical path. Format detection and parsing are implemented as custom code in `format_detector.py`, `parsers/spdx_parser.py`, and `parsers/cyclonedx_parser.py`. Both libraries are listed as runtime dependencies in `pyproject.toml` but no module in `src/sbom_validator/` currently imports them.

The recommendation is to **exclude** both libraries from the binary to reduce size and eliminate the hidden-import risk:

```python
# In sbom_validator.spec
excludes=["spdx_tools", "cyclonedx"],
```

If a future version of the parsers imports these libraries, the `excludes` list must be updated accordingly. This is explicitly called out as a maintenance risk.

The `jsonschema` package uses a plugin-like pattern for format checkers. The following hidden import is required:

```python
hiddenimports=["jsonschema.validators", "jsonschema._format", "jsonschema._keywords"],
```

### Spec File

The following is the complete content of `sbom_validator.spec`, committed to the repository root. The Developer task copies this file verbatim; any changes to bundling behavior must go through this spec file.

```python
# sbom_validator.spec
# PyInstaller spec for sbom-validator standalone binary.
# Run: pyinstaller sbom_validator.spec
# Output: dist/sbom-validator  (Linux) or dist/sbom-validator.exe  (Windows)

from pathlib import Path
import sys

src_root = Path(SPECPATH)
schemas_dir = src_root / "src" / "sbom_validator" / "schemas"

a = Analysis(
    [str(src_root / "src" / "sbom_validator" / "cli.py")],
    pathex=[str(src_root / "src")],
    binaries=[],
    datas=[
        (str(schemas_dir / "spdx-2.3.schema.json"), "schemas"),
        (str(schemas_dir / "cyclonedx-1.6.schema.json"), "schemas"),
    ],
    hiddenimports=[
        "jsonschema.validators",
        "jsonschema._format",
        "jsonschema._keywords",
        "sbom_validator.parsers.spdx_parser",
        "sbom_validator.parsers.cyclonedx_parser",
        "sbom_validator.logging_config",
        "sbom_validator.report_writer",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["spdx_tools", "cyclonedx"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="sbom-validator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
```

Notes on the spec:

- `SPECPATH` is a PyInstaller built-in variable set to the directory containing the spec file (the repo root). Using `Path(SPECPATH)` avoids hardcoded absolute paths, making the spec portable across developer machines and CI runners.
- `onefile=True` inside `EXE(...)` is equivalent to the `--onefile` CLI flag when using a spec file.
- `upx=True` enables UPX compression if UPX is installed on the build host; PyInstaller gracefully falls back to no compression if UPX is absent. CI runners do not need to install UPX.
- The `name="sbom-validator"` parameter controls the output filename. On Windows, PyInstaller automatically appends `.exe`.

### GitHub Actions Release Workflow

A new file `.github/workflows/release.yml` is created. The existing `ci.yml` is NOT modified.

**Trigger:** `push: tags: ['v*.*.*']` — fires when a tag matching the semver pattern is pushed to any branch. The tag must be created manually by a maintainer following the release checklist.

**Permissions:** `permissions: contents: write` is required at the job level so that `softprops/action-gh-release@v2` can create a release and upload assets.

**Interface Contract (release.yml content):**

```yaml
# .github/workflows/release.yml

name: Release

on:
  push:
    tags:
      - 'v*.*.*'

permissions:
  contents: write

jobs:
  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --with dev

      - name: Build binary
        run: poetry run pyinstaller sbom_validator.spec

      - name: Smoke test
        run: ./dist/sbom-validator --version

      - name: Upload to GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/sbom-validator

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --with dev

      - name: Build binary
        run: poetry run pyinstaller sbom_validator.spec

      - name: Smoke test
        run: .\dist\sbom-validator.exe --version

      - name: Upload to GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/sbom-validator.exe
```

The smoke test (`--version`) verifies that the binary starts, the entry point resolves, and the embedded package metadata is accessible. It does not validate a real SBOM file. A more thorough integration test (passing a known-good fixture) is recommended in a future version.

### Interface Contract (Python stubs for modified module)

```python
# schema_validator.py  (modified function — frozen-compatible path resolution)

import sys
from pathlib import Path


def _schemas_dir() -> Path:
    """Return path to bundled schemas, compatible with PyInstaller frozen mode."""
    ...
```

No new public functions are added to existing modules. The change is confined to `schema_validator.py`'s private path resolution helper.

## Consequences

**Positive:**

- PyInstaller's spec file is a plain Python script: auditable, diffable, and version-controlled alongside the source.
- The `_schemas_dir()` shim is the only change required to existing source files; all other bundling configuration lives in the spec.
- Excluding `spdx-tools` and `cyclonedx-bom` reduces binary size by an estimated 20–40 MB (these libraries bundle their own schema files and data assets).
- The release workflow is fully automated: tagging triggers the build, smoke test, and upload pipeline. No manual upload steps.

**Negative:**

- `sys._MEIPASS` is a PyInstaller internal attribute, not a documented Python API. If PyInstaller changes this attribute in a future major version, `_schemas_dir()` must be updated. This is mitigated by pinning `pyinstaller >= 6.0` and reviewing release notes on upgrades.
- `--onefile` mode extracts to a temporary directory on first run, which is slower than a directory-based installation on some filesystems (particularly when antivirus scanning is active on Windows). This is a known PyInstaller trade-off accepted for simplicity of distribution.
- The spec file hardcodes Python subpackage paths (`parsers/spdx_parser`, `parsers/cyclonedx_parser`) as hidden imports. New submodules added to the package must be evaluated for inclusion in `hiddenimports`.
- The smoke test only checks `--version`. A broken schema path (e.g., wrong `datas` destination) would not be caught until a real file is validated. The Developer should extend the smoke test to run `validate` against a bundled fixture file.

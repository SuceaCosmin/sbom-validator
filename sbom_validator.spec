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

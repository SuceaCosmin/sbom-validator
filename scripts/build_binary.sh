#!/usr/bin/env bash
set -euo pipefail
poetry run pyinstaller sbom_validator.spec

#!/usr/bin/env bash
# smoke-test-binary.sh
#
# Validates a built sbom-validator binary against real fixtures.
# Checks output content AND exit codes — not just whether the process starts.
#
# Usage:
#   bash scripts/smoke-test-binary.sh ./dist/sbom-validator          (Linux)
#   bash scripts/smoke-test-binary.sh ./dist/sbom-validator.exe      (Windows/CI)
#
# Exit: 0 if all checks pass, 1 on first failure.

set -uo pipefail

BINARY="${1:?Usage: $0 <path-to-binary>}"
FIXTURES="tests/fixtures"
PASS=0
FAIL=0

# Colors (suppressed if not a tty)
if [ -t 1 ]; then
  GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
else
  GREEN=''; RED=''; NC=''
fi

ok()   { echo -e "${GREEN}PASS${NC}  $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}FAIL${NC}  $1"; FAIL=$((FAIL+1)); }

run() {
  local label="$1"; shift
  local expected_exit="$1"; shift
  local expected_text="$1"; shift

  local output actual_exit
  output=$("$BINARY" "$@" 2>&1); actual_exit=$?

  if [ "$actual_exit" -ne "$expected_exit" ]; then
    fail "$label — expected exit $expected_exit, got $actual_exit"
    echo "    output: $output"
    return
  fi

  if [ -n "$expected_text" ] && ! echo "$output" | grep -qF "$expected_text"; then
    fail "$label — output did not contain: '$expected_text'"
    echo "    output: $output"
    return
  fi

  ok "$label"
}

echo "Binary: $BINARY"
echo "---"

# --- Startup checks ---
run "--version outputs version string"         0 "sbom-validator"  --version
run "--help outputs usage"                     0 "Usage:"           --help

# --- SPDX JSON ---
run "SPDX valid-full       → PASS exit 0"     0 "PASS"  validate "$FIXTURES/spdx/valid-full.spdx.json"
run "SPDX valid-minimal    → PASS exit 0"     0 "PASS"  validate "$FIXTURES/spdx/valid-minimal.spdx.json"
run "SPDX invalid-schema   → FAIL exit 1"     1 "FAIL"  validate "$FIXTURES/spdx/invalid-schema.spdx.json"
run "SPDX missing-supplier → FAIL exit 1"     1 "FAIL"  validate "$FIXTURES/spdx/missing-supplier.spdx.json"

# --- CycloneDX JSON ---
run "CDX JSON valid-full       → PASS exit 0" 0 "PASS"  validate "$FIXTURES/cyclonedx/valid-full.cdx.json"
run "CDX JSON invalid-schema   → FAIL exit 1" 1 "FAIL"  validate "$FIXTURES/cyclonedx/invalid-schema.cdx.json"
run "CDX JSON missing-supplier → FAIL exit 1" 1 "FAIL"  validate "$FIXTURES/cyclonedx/missing-supplier.cdx.json"

# --- CycloneDX XML ---
run "CDX XML valid-full       → PASS exit 0"  0 "PASS"  validate "$FIXTURES/cyclonedx/valid-full.cdx.xml"
run "CDX XML invalid-schema   → FAIL exit 1"  1 "FAIL"  validate "$FIXTURES/cyclonedx/invalid-schema.cdx.xml"
run "CDX XML missing-supplier → FAIL exit 1"  1 "FAIL"  validate "$FIXTURES/cyclonedx/missing-supplier.cdx.xml"

# --- JSON output format ---
run "JSON output contains 'status' key"       0 '"status"'  validate --format json "$FIXTURES/spdx/valid-full.spdx.json"

# --- Report generation ---
REPORT_TMP=$(mktemp -d)
"$BINARY" validate --report-dir "$REPORT_TMP" "$FIXTURES/spdx/valid-full.spdx.json" > /dev/null 2>&1 || true
if ls "$REPORT_TMP"/*.html "$REPORT_TMP"/*.json > /dev/null 2>&1; then
  ok "--report-dir generates HTML and JSON files"
else
  fail "--report-dir did not generate report files"
fi
rm -rf "$REPORT_TMP"

# --- Summary ---
echo "---"
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

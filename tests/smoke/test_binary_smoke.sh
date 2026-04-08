#!/usr/bin/env bash
# Smoke test for the PyInstaller standalone binary.
# Run from the repository root:
#   BINARY_PATH=./dist/sbom-validator bash tests/smoke/test_binary_smoke.sh
#
# The script runs all tests and exits non-zero if any failed.
# It does NOT exit on the first failure — every test always runs.

set -uo pipefail

# ---------------------------------------------------------------------------
# Binary resolution
# ---------------------------------------------------------------------------
if [[ -z "${BINARY_PATH:-}" ]]; then
    if [[ -f "./dist/sbom-validator.exe" ]]; then
        BINARY_PATH="./dist/sbom-validator.exe"
    else
        BINARY_PATH="./dist/sbom-validator"
    fi
fi

BINARY="$BINARY_PATH"

# ---------------------------------------------------------------------------
# Fixture paths (relative to repo root)
# ---------------------------------------------------------------------------
FIXTURE_SPDX_VALID="tests/fixtures/spdx/valid-full.spdx.json"
FIXTURE_CDX_VALID="tests/fixtures/cyclonedx/valid-full.cdx.json"
FIXTURE_SPDX_INVALID="tests/fixtures/spdx/invalid-schema.spdx.json"

# ---------------------------------------------------------------------------
# Temp directory for --report-dir test (cleaned up via trap)
# ---------------------------------------------------------------------------
REPORT_DIR="/tmp/sbom-smoke-test-$$"
mkdir -p "$REPORT_DIR"

cleanup() {
    rm -rf "$REPORT_DIR"
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
FAILURES=0

pass() {
    echo "  PASS: $1"
}

fail() {
    echo "  FAIL: $1"
    FAILURES=$(( FAILURES + 1 ))
}

run_test() {
    # run_test <test-name> <expected-exit-code> <command...>
    local name="$1"
    local expected_exit="$2"
    shift 2

    echo ""
    echo "TEST: $name"

    actual_exit=0
    output=$("$@" 2>&1) || actual_exit=$?

    if [[ "$actual_exit" -eq "$expected_exit" ]]; then
        pass "$name (exit $actual_exit)"
    else
        fail "$name — expected exit $expected_exit, got $actual_exit"
        echo "       output: $output"
    fi

    # Return the output so callers can inspect it
    printf '%s' "$output"
}

# ---------------------------------------------------------------------------
# Guard: binary must exist
# ---------------------------------------------------------------------------
echo "Using binary: $BINARY"
if [[ ! -f "$BINARY" ]]; then
    echo "ERROR: binary not found at $BINARY"
    echo "Set BINARY_PATH to the correct path, e.g.:"
    echo "  BINARY_PATH=./dist/sbom-validator bash tests/smoke/test_binary_smoke.sh"
    exit 1
fi

# ---------------------------------------------------------------------------
# Test 1: --version exits 0 and output contains a version-like string
# ---------------------------------------------------------------------------
echo ""
echo "TEST: --version exits 0 and prints version string"
VERSION_OUTPUT=""
VERSION_EXIT=0
VERSION_OUTPUT=$("$BINARY" --version 2>&1) || VERSION_EXIT=$?

if [[ "$VERSION_EXIT" -eq 0 ]]; then
    pass "--version exits 0"
else
    fail "--version expected exit 0, got $VERSION_EXIT"
fi

# Match a basic semver-like pattern: digits.digits.digits anywhere in the output
if echo "$VERSION_OUTPUT" | grep -qE '[0-9]+\.[0-9]+\.[0-9]'; then
    pass "--version output contains version string ('$VERSION_OUTPUT')"
else
    fail "--version output does not contain a version number; got: '$VERSION_OUTPUT'"
fi

# ---------------------------------------------------------------------------
# Test 2: validate valid SPDX fixture → exit 0
# ---------------------------------------------------------------------------
echo ""
echo "TEST: validate valid SPDX full fixture exits 0"
SPDX_EXIT=0
"$BINARY" validate "$FIXTURE_SPDX_VALID" > /dev/null 2>&1 || SPDX_EXIT=$?
if [[ "$SPDX_EXIT" -eq 0 ]]; then
    pass "validate valid SPDX → exit 0"
else
    fail "validate valid SPDX → expected exit 0, got $SPDX_EXIT"
fi

# ---------------------------------------------------------------------------
# Test 3: validate valid CycloneDX fixture → exit 0
# ---------------------------------------------------------------------------
echo ""
echo "TEST: validate valid CycloneDX full fixture exits 0"
CDX_EXIT=0
"$BINARY" validate "$FIXTURE_CDX_VALID" > /dev/null 2>&1 || CDX_EXIT=$?
if [[ "$CDX_EXIT" -eq 0 ]]; then
    pass "validate valid CycloneDX → exit 0"
else
    fail "validate valid CycloneDX → expected exit 0, got $CDX_EXIT"
fi

# ---------------------------------------------------------------------------
# Test 4: validate invalid-schema SPDX fixture → exit 1
# ---------------------------------------------------------------------------
echo ""
echo "TEST: validate invalid-schema SPDX fixture exits 1"
INVALID_EXIT=0
"$BINARY" validate "$FIXTURE_SPDX_INVALID" > /dev/null 2>&1 || INVALID_EXIT=$?
if [[ "$INVALID_EXIT" -eq 1 ]]; then
    pass "validate invalid-schema SPDX → exit 1"
else
    fail "validate invalid-schema SPDX → expected exit 1, got $INVALID_EXIT"
fi

# ---------------------------------------------------------------------------
# Test 5: validate nonexistent file → exit 2
# ---------------------------------------------------------------------------
echo ""
echo "TEST: validate nonexistent file exits 2"
MISSING_EXIT=0
"$BINARY" validate nonexistent-file.json > /dev/null 2>&1 || MISSING_EXIT=$?
if [[ "$MISSING_EXIT" -eq 2 ]]; then
    pass "validate nonexistent file → exit 2"
else
    fail "validate nonexistent file → expected exit 2, got $MISSING_EXIT"
fi

# ---------------------------------------------------------------------------
# Test 6: validate with --format json → exit 0 and output is valid JSON
# ---------------------------------------------------------------------------
echo ""
echo "TEST: validate valid SPDX with --format json exits 0 and output is valid JSON"
JSON_EXIT=0
JSON_OUTPUT=""
JSON_OUTPUT=$("$BINARY" validate "$FIXTURE_SPDX_VALID" --format json 2>&1) || JSON_EXIT=$?

if [[ "$JSON_EXIT" -eq 0 ]]; then
    pass "--format json exits 0"
else
    fail "--format json → expected exit 0, got $JSON_EXIT"
fi

if echo "$JSON_OUTPUT" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
    pass "--format json output is valid JSON"
else
    fail "--format json output is not valid JSON; got: $(echo "$JSON_OUTPUT" | head -5)"
fi

# ---------------------------------------------------------------------------
# Test 7: validate with --log-level DEBUG → exit 0
# ---------------------------------------------------------------------------
echo ""
echo "TEST: validate valid SPDX with --log-level DEBUG exits 0"
DEBUG_EXIT=0
"$BINARY" validate "$FIXTURE_SPDX_VALID" --log-level DEBUG > /dev/null 2>&1 || DEBUG_EXIT=$?
if [[ "$DEBUG_EXIT" -eq 0 ]]; then
    pass "--log-level DEBUG exits 0"
else
    fail "--log-level DEBUG → expected exit 0, got $DEBUG_EXIT"
fi

# ---------------------------------------------------------------------------
# Test 8: validate with --report-dir → exit 0, .html and .json files created
# ---------------------------------------------------------------------------
echo ""
echo "TEST: validate valid SPDX with --report-dir creates .html and .json reports"
REPORT_EXIT=0
"$BINARY" validate "$FIXTURE_SPDX_VALID" --report-dir "$REPORT_DIR" > /dev/null 2>&1 || REPORT_EXIT=$?

if [[ "$REPORT_EXIT" -eq 0 ]]; then
    pass "--report-dir exits 0"
else
    fail "--report-dir → expected exit 0, got $REPORT_EXIT"
fi

HTML_COUNT=$(find "$REPORT_DIR" -maxdepth 1 -name "*.html" 2>/dev/null | wc -l)
JSON_COUNT=$(find "$REPORT_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)

if [[ "$HTML_COUNT" -ge 1 ]]; then
    pass "--report-dir produced at least one .html file"
else
    fail "--report-dir produced no .html file in $REPORT_DIR (found $HTML_COUNT)"
fi

if [[ "$JSON_COUNT" -ge 1 ]]; then
    pass "--report-dir produced at least one .json file"
else
    fail "--report-dir produced no .json file in $REPORT_DIR (found $JSON_COUNT)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "========================================"
if [[ "$FAILURES" -eq 0 ]]; then
    echo "All smoke tests PASSED."
    echo "========================================"
    exit 0
else
    echo "FAILED: $FAILURES smoke test(s) did not pass."
    echo "========================================"
    exit 1
fi

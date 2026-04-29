"""Central constants for sbom-validator.

All domain-significant string literals that appear in logic (format names,
validation rule codes, supported version strings) must be defined here and
imported by the modules that need them.
"""

from sbom_validator.models import IssueCategory

# ── Format identifiers ─────────────────────────────────────────────────────
# Returned by detect_format() and threaded through the whole pipeline.
FORMAT_SPDX = "spdx"  # SPDX 2.3 JSON
FORMAT_SPDX_TV = "spdx-tv"  # SPDX 2.3 Tag-Value
FORMAT_SPDX_YAML = "spdx-yaml"  # SPDX 2.3 YAML
FORMAT_CYCLONEDX = "cyclonedx"

# ── Supported specification versions ───────────────────────────────────────
SPDX_SUPPORTED_VERSION = "SPDX-2.3"
CYCLONEDX_SUPPORTED_VERSIONS: frozenset[str] = frozenset({"1.3", "1.4", "1.5", "1.6"})
CYCLONEDX_BOM_FORMAT_VALUE = "CycloneDX"  # value of the "bomFormat" JSON field
CYCLONEDX_XML_NAMESPACE_PREFIX = "http://cyclonedx.org/schema/bom/"
CYCLONEDX_SUPPORTED_XML_NAMESPACES: frozenset[str] = frozenset(
    f"{CYCLONEDX_XML_NAMESPACE_PREFIX}{v}" for v in CYCLONEDX_SUPPORTED_VERSIONS
)

# ── JSON field names used for format detection ─────────────────────────────
SPDX_FIELD_VERSION = "spdxVersion"
CDX_FIELD_BOM_FORMAT = "bomFormat"
CDX_FIELD_SPEC_VERSION = "specVersion"

# ── NTIA validation rule codes ─────────────────────────────────────────────
RULE_FORMAT_DETECTION = "FR-01"
RULE_SPDX_SCHEMA = "FR-02"
RULE_CDX_SCHEMA = "FR-03"
RULE_SUPPLIER = "FR-04"
RULE_COMPONENT_NAME = "FR-05"
RULE_VERSION = "FR-06"
RULE_RELATIONSHIPS = "FR-08"
RULE_AUTHOR = "FR-09"
RULE_TIMESTAMP = "FR-10"

# ── Issue category display constants ───────────────────────────────────────
CATEGORY_LABELS: dict[str, str] = {
    IssueCategory.FORMAT: "Format / Detection Errors",
    IssueCategory.SCHEMA: "Schema Issues",
    IssueCategory.NTIA: "NTIA Compliance Issues",
}
CATEGORY_ORDER: list[str] = [IssueCategory.FORMAT, IssueCategory.SCHEMA, IssueCategory.NTIA]

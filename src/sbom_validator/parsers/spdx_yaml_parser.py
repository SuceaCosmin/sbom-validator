"""Parser for SPDX 2.3 YAML SBOM files.

SPDX YAML is structurally identical to SPDX JSON — same field names, same
nesting — so this module loads the YAML document with yaml.safe_load and then
delegates all field extraction to the shared _parse_spdx_document helper from
spdx_parser.py.

The format field in the returned NormalizedSBOM is set to "spdx-yaml" to
surface the serialization format in ValidationResult.format_detected.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from sbom_validator.exceptions import ParseError
from sbom_validator.models import NormalizedSBOM
from sbom_validator.parsers.spdx_parser import _parse_spdx_document

logger = logging.getLogger(__name__)


def parse_spdx_yaml(file_path: Path) -> NormalizedSBOM:
    """Parse an SPDX 2.3 YAML file into a NormalizedSBOM.

    Loads the YAML document using yaml.safe_load (never bare yaml.load),
    then delegates field extraction to _parse_spdx_document.

    Raises:
        ParseError: If the file cannot be read, is empty, contains invalid
            YAML, or is missing required SPDX fields.
    """
    logger.debug("Parsing SPDX YAML file: %s", file_path)

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ParseError(f"Cannot read SPDX YAML file '{file_path}': {e}") from e

    if not raw_text.strip():
        raise ParseError(f"SPDX YAML file '{file_path}' is empty.")

    try:
        document: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        raise ParseError(f"SPDX YAML file '{file_path}' contains invalid YAML: {e}") from e

    if not isinstance(document, dict):
        raise ParseError(
            f"SPDX YAML file '{file_path}' must be a YAML mapping at the root level; "
            f"got {type(document).__name__}."
        )

    # Delegate field extraction to the shared SPDX document parser.
    # Override format to "spdx-yaml" so callers can distinguish the serialization.
    base_sbom = _parse_spdx_document(document, str(file_path))

    logger.debug(
        "SPDX YAML parsed: %d components, %d relationships",
        len(base_sbom.components),
        len(base_sbom.relationships),
    )

    return NormalizedSBOM(
        format="spdx-yaml",
        author=base_sbom.author,
        timestamp=base_sbom.timestamp,
        components=base_sbom.components,
        relationships=base_sbom.relationships,
    )

"""Structured logging configuration for sbom-validator (ADR-006)."""

from __future__ import annotations

import logging
import sys
import time

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s \u2014 %(message)s"
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
    # getattr may return a non-int if the attribute exists but isn't a level;
    # guard against that by ensuring we have an int.
    if not isinstance(numeric, int):
        numeric = logging.WARNING

    logger = logging.getLogger("sbom_validator")
    logger.setLevel(numeric)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(numeric)
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        formatter.converter = time.gmtime
        handler.setFormatter(formatter)
        logger.addHandler(handler)

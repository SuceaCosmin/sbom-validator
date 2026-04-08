"""Unit tests for sbom_validator.logging_config (TDD red phase).

These tests describe the intended behavior of the logging_config module
per ADR-006. They WILL fail until the Developer creates
src/sbom_validator/logging_config.py.

Test layout
-----------
TestConfigureLoggingLevel       -- level argument is applied correctly
TestConfigureLoggingHandler     -- handler is attached to the right logger/stream
TestConfigureLoggingFormat      -- format string includes logger name
TestConfigureLoggingIdempotency -- calling configure_logging twice is safe
TestConfigureLoggingPropagation -- records at/above level appear; below are suppressed
"""

from __future__ import annotations

import logging
import sys

import pytest
from sbom_validator.logging_config import LOG_FORMAT, configure_logging

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LOGGER_NAME = "sbom_validator"


def _get_sbom_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def _clear_sbom_logger() -> None:
    """Remove all handlers from the sbom_validator logger and reset level."""
    logger = _get_sbom_logger()
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)


# ---------------------------------------------------------------------------
# Autouse fixture: ensure logger is clean before/after each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_logger():
    """Reset the sbom_validator logger around every test."""
    _clear_sbom_logger()
    yield
    _clear_sbom_logger()


# ===========================================================================
# TestConfigureLoggingLevel
# ===========================================================================


class TestConfigureLoggingLevel:
    """configure_logging sets the correct numeric level on the logger."""

    def test_debug_level_is_set(self):
        # Arrange / Act
        configure_logging("DEBUG")
        # Assert
        logger = _get_sbom_logger()
        assert logger.level == logging.DEBUG

    def test_info_level_is_set(self):
        configure_logging("INFO")
        logger = _get_sbom_logger()
        assert logger.level == logging.INFO

    def test_warning_level_is_set(self):
        configure_logging("WARNING")
        logger = _get_sbom_logger()
        assert logger.level == logging.WARNING

    def test_error_level_is_set(self):
        configure_logging("ERROR")
        logger = _get_sbom_logger()
        assert logger.level == logging.ERROR

    def test_lowercase_debug_is_accepted(self):
        """ADR-006: level argument is case-insensitive."""
        configure_logging("debug")
        logger = _get_sbom_logger()
        assert logger.level == logging.DEBUG

    def test_lowercase_warning_is_accepted(self):
        configure_logging("warning")
        logger = _get_sbom_logger()
        assert logger.level == logging.WARNING

    def test_invalid_level_coerces_to_warning(self):
        """ADR-006: invalid values are silently coerced to WARNING."""
        configure_logging("INVALID_LEVEL")
        logger = _get_sbom_logger()
        assert logger.level == logging.WARNING


# ===========================================================================
# TestConfigureLoggingHandler
# ===========================================================================


class TestConfigureLoggingHandler:
    """configure_logging installs exactly one StreamHandler pointing to stderr."""

    def test_handler_is_added_to_sbom_validator_logger(self):
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        assert len(logger.handlers) == 1

    def test_handler_is_stream_handler(self):
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)

    def test_handler_writes_to_stderr(self):
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        handler = logger.handlers[0]
        # The stream must be sys.stderr, not sys.stdout
        assert handler.stream is sys.stderr

    def test_handler_does_not_write_to_stdout(self):
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        handler = logger.handlers[0]
        assert handler.stream is not sys.stdout

    def test_handler_level_matches_configured_level(self):
        configure_logging("INFO")
        logger = _get_sbom_logger()
        handler = logger.handlers[0]
        assert handler.level == logging.INFO


# ===========================================================================
# TestConfigureLoggingFormat
# ===========================================================================


class TestConfigureLoggingFormat:
    """The handler formatter includes the logger name as required by ADR-006."""

    def test_formatter_is_set_on_handler(self):
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        handler = logger.handlers[0]
        assert handler.formatter is not None

    def test_format_string_contains_logger_name_placeholder(self):
        """The format string must contain %(name)s for traceability."""
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        handler = logger.handlers[0]
        # Access the _fmt attribute of the formatter
        fmt_string = handler.formatter._fmt  # type: ignore[union-attr]
        assert "%(name)s" in fmt_string

    def test_format_string_contains_levelname_placeholder(self):
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        handler = logger.handlers[0]
        fmt_string = handler.formatter._fmt  # type: ignore[union-attr]
        assert "%(levelname)" in fmt_string

    def test_format_string_contains_message_placeholder(self):
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        handler = logger.handlers[0]
        fmt_string = handler.formatter._fmt  # type: ignore[union-attr]
        assert "%(message)s" in fmt_string

    def test_log_format_module_constant_contains_name(self):
        """LOG_FORMAT constant exported from the module includes %(name)s."""
        assert "%(name)s" in LOG_FORMAT

    def test_log_format_module_constant_contains_levelname(self):
        assert "%(levelname)" in LOG_FORMAT

    def test_log_format_module_constant_contains_message(self):
        assert "%(message)s" in LOG_FORMAT

    def test_logger_name_appears_in_emitted_output(self, caplog):
        """Records emitted to the sbom_validator hierarchy include the logger name."""
        configure_logging("DEBUG")
        child_logger = logging.getLogger("sbom_validator.test_module")
        with caplog.at_level(logging.DEBUG, logger="sbom_validator"):
            child_logger.debug("test message for name check")
        assert "sbom_validator.test_module" in caplog.text


# ===========================================================================
# TestConfigureLoggingIdempotency
# ===========================================================================


class TestConfigureLoggingIdempotency:
    """Calling configure_logging more than once must not duplicate handlers."""

    def test_calling_twice_does_not_add_second_handler(self):
        configure_logging("DEBUG")
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        assert len(logger.handlers) == 1

    def test_calling_three_times_still_has_one_handler(self):
        configure_logging("WARNING")
        configure_logging("INFO")
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        assert len(logger.handlers) == 1

    def test_handler_count_stays_one_with_different_levels(self):
        """Even with different levels on subsequent calls, no new handler is added."""
        configure_logging("ERROR")
        configure_logging("DEBUG")
        logger = _get_sbom_logger()
        assert len(logger.handlers) == 1


# ===========================================================================
# TestConfigureLoggingPropagation
# ===========================================================================


class TestConfigureLoggingPropagation:
    """Records at or above the configured level are captured; below are suppressed."""

    def test_debug_level_captures_debug_messages(self, caplog):
        configure_logging("DEBUG")
        with caplog.at_level(logging.DEBUG, logger="sbom_validator"):
            logging.getLogger("sbom_validator.test").debug("a debug message")
        assert "a debug message" in caplog.text

    def test_warning_level_suppresses_debug_messages(self, caplog):
        configure_logging("WARNING")
        with caplog.at_level(logging.DEBUG, logger="sbom_validator"):
            logging.getLogger("sbom_validator.test").debug("suppressed debug message")
        # caplog captures at the propagation level; however the logger level
        # itself must suppress this — assert the logger won't pass it through
        logger = _get_sbom_logger()
        assert not logger.isEnabledFor(logging.DEBUG)

    def test_warning_level_allows_warning_messages(self, caplog):
        configure_logging("WARNING")
        with caplog.at_level(logging.WARNING, logger="sbom_validator"):
            logging.getLogger("sbom_validator.test").warning("a warning message")
        assert "a warning message" in caplog.text

    def test_info_level_suppresses_debug_messages(self, caplog):
        configure_logging("INFO")
        logger = _get_sbom_logger()
        assert not logger.isEnabledFor(logging.DEBUG)

    def test_info_level_allows_info_messages(self, caplog):
        configure_logging("INFO")
        with caplog.at_level(logging.INFO, logger="sbom_validator"):
            logging.getLogger("sbom_validator.test").info("an info message")
        assert "an info message" in caplog.text

    def test_error_level_suppresses_warning_messages(self, caplog):
        configure_logging("ERROR")
        logger = _get_sbom_logger()
        assert not logger.isEnabledFor(logging.WARNING)

    def test_error_level_allows_error_messages(self, caplog):
        configure_logging("ERROR")
        with caplog.at_level(logging.ERROR, logger="sbom_validator"):
            logging.getLogger("sbom_validator.test").error("an error message")
        assert "an error message" in caplog.text

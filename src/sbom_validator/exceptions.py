"""Custom exceptions for sbom-validator."""


class SBOMValidatorError(Exception):
    """Base exception for all sbom-validator errors."""


class ParseError(SBOMValidatorError):
    """Raised when an SBOM file cannot be parsed."""


class UnsupportedFormatError(SBOMValidatorError):
    """Raised when the SBOM format cannot be detected or is not supported."""

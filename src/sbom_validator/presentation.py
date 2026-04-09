"""Helpers for human-friendly validation output rendering."""

from __future__ import annotations

import re

_XML_NAMESPACE_RE = re.compile(r"\{[^}]+\}")
_XML_TAG_PREFIX_RE = re.compile(r"Tag '([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)'")
_NTIA_RULE_SUFFIX_RE = re.compile(r"\s*\(NTIA\s+FR-\d+\)\s*$")
_REQUIRED_PROPERTY_RE = re.compile(r"^'([^']+)' is a required property$")


def humanize_field_path(field_path: str) -> str:
    """Return a user-friendly field path for CLI/HTML display."""
    if not field_path:
        return field_path
    # XML validators often emit expanded namespaces; hide them in user-facing output.
    return _XML_NAMESPACE_RE.sub("", field_path)


def humanize_message(message: str) -> str:
    """Return a user-friendly issue message for CLI/HTML display."""
    if not message:
        return message
    # Remove expanded XML namespaces from tags in messages.
    clean = _XML_NAMESPACE_RE.sub("", message)
    # Convert compact prefix-style references (e.g. bom:name) to plain element names.
    clean = _XML_TAG_PREFIX_RE.sub(lambda m: f"Element '{m.group(2)}'", clean)
    # Hide internal NTIA rule IDs from end-user text.
    clean = _NTIA_RULE_SUFFIX_RE.sub("", clean)

    required_property = _REQUIRED_PROPERTY_RE.match(clean)
    if required_property:
        prop = required_property.group(1)
        return f"Missing required field '{prop}'. " f"Hint: add '{prop}' at this location."

    if "missing required attribute 'type'" in clean:
        return (
            "Missing required attribute 'type'. "
            "Hint: set component type (for example 'library', 'application', or 'framework')."
        )

    if "missing a supplier name" in clean:
        return (
            f"{clean}. Hint: provide a supplier/organization name for this component."
            if not clean.endswith(".")
            else f"{clean} Hint: provide a supplier/organization name for this component."
        )

    if "Element 'name' expected." in clean and "Unexpected child with tag" in clean:
        return (
            f"{clean} Hint: ensure the component includes <name> before <version>."
            if not clean.endswith(".")
            else f"{clean} Hint: ensure the component includes <name> before <version>."
        )

    return clean


def split_message_and_hint(message: str) -> tuple[str, str | None]:
    """Split a humanized message into primary message and optional hint."""
    base, sep, hint = message.partition(" Hint: ")
    if not sep:
        return message, None
    return base.strip(), hint.strip() or None

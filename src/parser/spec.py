"""FieldSpec definition and type coercion for JRDB fixed-length records."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSpec:
    """Definition of a single field in a JRDB fixed-length record.

    Attributes:
        name: Column name for the parsed DataFrame.
        offset: 1-based byte offset (matching JRDB spec docs).
        length: Field length in bytes.
        field_type: One of "numeric", "text", "decimal", "hex".
        scale: Decimal places (e.g. ZZ9.9 → scale=1).
        signed: Whether the field can have a minus sign.
        description: Human-readable description.
    """

    name: str
    offset: int
    length: int
    field_type: str
    scale: int = 0
    signed: bool = False
    description: str = ""


def coerce(text: str, field_type: str, scale: int = 0, signed: bool = False) -> object:
    """Convert a stripped text value to the appropriate Python type.

    Args:
        text: Raw text after CP932 decode and strip.
        field_type: One of "numeric", "text", "decimal", "hex".
        scale: Decimal places for "decimal" type.
        signed: Whether minus sign is possible.

    Returns:
        Converted value, or None for empty/unparseable fields.
    """
    if field_type == "text":
        return text if text else None

    if field_type == "hex":
        if not text:
            return None
        try:
            return int(text, 16)
        except ValueError:
            return None

    if field_type == "numeric":
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    if field_type == "decimal":
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            # Handle ZZ9.9 format where value might be without decimal point
            try:
                return int(text) / (10**scale) if scale > 0 else float(text)
            except ValueError:
                return None

    return text

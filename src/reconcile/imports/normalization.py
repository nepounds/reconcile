"""Deterministic normalization helpers for imported bank descriptions."""

from __future__ import annotations

import re

from reconcile.exceptions import ValidationError

_ALLOWED_NOISE_PATTERN = re.compile(r"[^A-Z0-9\s]")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_bank_description(description: str) -> str:
    """Normalize a raw bank description without mutating the original value."""
    if not isinstance(description, str):
        raise ValidationError("bank description must be a string")

    stripped = description.strip()
    if not stripped:
        raise ValidationError("bank description cannot be blank")

    uppercased = stripped.upper()
    without_noise = _ALLOWED_NOISE_PATTERN.sub(" ", uppercased)
    normalized = _WHITESPACE_PATTERN.sub(" ", without_noise).strip()

    if not normalized:
        raise ValidationError("bank description cannot be blank after normalization")

    return normalized
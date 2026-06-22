"""Money parsing and formatting helpers using integer cents only."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from reconcile.exceptions import MoneyError

_MONEY_RE = re.compile(r"^[+-]?\$?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?$")


def parse_money_to_cents(value: str) -> int:
    """Convert a dollar amount string into integer cents without using floats."""
    if not isinstance(value, str):
        raise MoneyError("Money value must be a string.")

    text = value.strip()
    if not text:
        raise MoneyError("Money value cannot be blank.")

    if text in {"$", "+$", "-$"}:
        raise MoneyError("Money value must include digits.")

    if not _MONEY_RE.fullmatch(text):
        raise MoneyError(f"Invalid money value: {value!r}.")

    normalized = text.replace("$", "").replace(",", "")

    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise MoneyError(f"Invalid money value: {value!r}.") from exc

    if not amount.is_finite():
        raise MoneyError("Money value must be finite.")

    exponent = amount.as_tuple().exponent
    if not isinstance(exponent, int) or exponent < -2:
        raise MoneyError("Money value cannot have more than two decimal places.")

    return int(amount * 100)


def format_cents(cents: int) -> str:
    """Format integer cents as a dollar string with two decimal places."""
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise MoneyError("Cents value must be an integer, not bool or another type.")

    sign = "-" if cents < 0 else ""
    absolute_cents = abs(cents)
    dollars, remaining_cents = divmod(absolute_cents, 100)
    return f"{sign}{dollars}.{remaining_cents:02d}"

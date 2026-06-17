"""Scoring helpers for fuzzy reconciliation candidates."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from reconcile.exceptions import ValidationError

_AMOUNT_WEIGHT = 0.60
_DATE_WEIGHT = 0.25
_DESCRIPTION_WEIGHT = 0.15
_DEFAULT_DUPLICATE_PENALTY = 25.0


def _validate_int_cents(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an integer number of cents")
    return value


def _validate_non_negative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be a non-negative integer")
    if value < 0:
        raise ValidationError(f"{field_name} cannot be negative")
    return value


def _validate_date(value: object, field_name: str) -> date:
    if isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a date, not datetime")
    if not isinstance(value, date):
        raise ValidationError(f"{field_name} must be a date")
    return value


def _validate_duplicate_penalty(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValidationError("duplicate_penalty_amount must be numeric")
    return float(value)


def _clamp_score(score: float) -> float:
    return max(0.0, min(100.0, float(score)))


def days_between(left: date, right: date) -> int:
    """Return the absolute number of days between two dates."""
    left_date = _validate_date(left, "left")
    right_date = _validate_date(right, "right")
    return abs((left_date - right_date).days)


def score_amount_match(
    bank_amount_cents: int,
    ledger_amount_cents: int,
    *,
    tolerance_cents: int = 5,
) -> float:
    """Score amount similarity using signed integer cents."""
    bank_amount = _validate_int_cents(
        bank_amount_cents,
        "bank_amount_cents",
    )
    ledger_amount = _validate_int_cents(
        ledger_amount_cents,
        "ledger_amount_cents",
    )
    tolerance = _validate_non_negative_int(
        tolerance_cents,
        "tolerance_cents",
    )

    if bank_amount == ledger_amount:
        return 100.0

    if (bank_amount < 0 < ledger_amount) or (
        ledger_amount < 0 < bank_amount
    ):
        return 0.0

    delta = abs(bank_amount - ledger_amount)
    if delta > tolerance:
        return 0.0

    if tolerance == 0:
        return 0.0

    return _clamp_score(((tolerance + 1 - delta) / (tolerance + 1)) * 100.0)


def score_date_match(
    bank_date: date,
    ledger_date: date,
    *,
    date_window_days: int = 3,
) -> float:
    """Score date similarity within a configurable date window."""
    bank_dt = _validate_date(bank_date, "bank_date")
    ledger_dt = _validate_date(ledger_date, "ledger_date")
    window = _validate_non_negative_int(
        date_window_days,
        "date_window_days",
    )

    delta = abs((bank_dt - ledger_dt).days)
    if delta == 0:
        return 100.0

    if delta > window:
        return 0.0

    if window == 0:
        return 0.0

    return _clamp_score(((window + 1 - delta) / (window + 1)) * 100.0)


def _normalize_description(description: str | None) -> str:
    if description is None:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", description.lower())
    return " ".join(normalized.split())


def _description_tokens(description: str) -> set[str]:
    return set(description.split())


def score_description_match(
    bank_description: str | None,
    ledger_description: str | None,
) -> float:
    """Score description similarity with deterministic token overlap."""
    bank_normalized = _normalize_description(bank_description)
    ledger_normalized = _normalize_description(ledger_description)

    if not bank_normalized or not ledger_normalized:
        return 0.0

    if bank_normalized == ledger_normalized:
        return 100.0

    bank_tokens = _description_tokens(bank_normalized)
    ledger_tokens = _description_tokens(ledger_normalized)

    if not bank_tokens or not ledger_tokens:
        return 0.0

    if bank_tokens <= ledger_tokens or ledger_tokens <= bank_tokens:
        return 100.0

    overlap = bank_tokens & ledger_tokens
    if not overlap:
        return 0.0

    jaccard = len(overlap) / len(bank_tokens | ledger_tokens)
    containment = len(overlap) / min(len(bank_tokens), len(ledger_tokens))
    score = ((containment * 0.70) + (jaccard * 0.30)) * 100.0

    return _clamp_score(score)


def score_reconciliation_candidate(
    *,
    bank_amount_cents: int,
    ledger_amount_cents: int,
    bank_date: date,
    ledger_date: date,
    bank_description: str | None,
    ledger_description: str | None,
    bank_duplicate_group_id: str | None = None,
    tolerance_cents: int = 5,
    date_window_days: int = 3,
    duplicate_penalty_amount: float = _DEFAULT_DUPLICATE_PENALTY,
) -> dict[str, Any]:
    """Score a bank-to-ledger reconciliation candidate."""
    penalty_amount = _validate_duplicate_penalty(duplicate_penalty_amount)
    amount_score = score_amount_match(
        bank_amount_cents,
        ledger_amount_cents,
        tolerance_cents=tolerance_cents,
    )
    date_score = score_date_match(
        bank_date,
        ledger_date,
        date_window_days=date_window_days,
    )
    description_score = score_description_match(
        bank_description,
        ledger_description,
    )

    amount_delta_cents = bank_amount_cents - ledger_amount_cents
    date_delta_days = (bank_date - ledger_date).days
    duplicate_penalty = penalty_amount if bank_duplicate_group_id else 0.0

    raw_score = (
        (amount_score * _AMOUNT_WEIGHT)
        + (date_score * _DATE_WEIGHT)
        + (description_score * _DESCRIPTION_WEIGHT)
        - duplicate_penalty
    )
    final_score = _clamp_score(raw_score)

    reasons: list[str] = []
    if amount_score == 100.0:
        reasons.append("Amounts match exactly.")
    elif amount_score > 0.0:
        reasons.append("Amounts are within tolerance.")
    else:
        reasons.append("Amounts are outside tolerance or have opposite signs.")

    if date_score == 100.0:
        reasons.append("Dates match exactly.")
    elif date_score > 0.0:
        reasons.append("Dates are within the configured date window.")
    else:
        reasons.append("Dates are outside the configured date window.")

    if description_score == 100.0:
        reasons.append("Descriptions match after normalization.")
    elif description_score > 0.0:
        reasons.append("Descriptions share overlapping tokens.")
    else:
        reasons.append("Descriptions do not provide useful support.")

    if duplicate_penalty:
        reasons.append("Duplicate-flagged bank transaction received a penalty.")

    return {
        "score": final_score,
        "amount_score": amount_score,
        "date_score": date_score,
        "description_score": description_score,
        "amount_delta_cents": amount_delta_cents,
        "date_delta_days": date_delta_days,
        "duplicate_penalty": duplicate_penalty,
        "score_explanation": {
            "formula": (
                "score = amount_score * 0.60 + date_score * 0.25 "
                "+ description_score * 0.15 - duplicate_penalty"
            ),
            "reason": " ".join(reasons),
            "reasons": reasons,
        },
    }


__all__ = [
    "days_between",
    "score_amount_match",
    "score_date_match",
    "score_description_match",
    "score_reconciliation_candidate",
]

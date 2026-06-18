"""Limited split reconciliation candidate discovery and scoring."""

from __future__ import annotations

from datetime import date, datetime
from itertools import combinations

from reconcile.exceptions import ValidationError
from reconcile.reconciliation.scoring import (
    score_amount_match,
    score_date_match,
    score_description_match,
)

_AMOUNT_WEIGHT = 0.70
_DATE_WEIGHT = 0.25
_DESCRIPTION_WEIGHT = 0.05


def _clamp_score(score: float) -> float:
    return max(0.0, min(100.0, float(score)))


def _validate_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an integer")
    return value


def _validate_non_negative_int(value: object, field_name: str) -> int:
    value = _validate_int(value, field_name)
    if value < 0:
        raise ValidationError(f"{field_name} cannot be negative")
    return value


def _validate_non_negative_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValidationError(f"{field_name} must be a number")
    number = float(value)
    if number < 0.0:
        raise ValidationError(f"{field_name} cannot be negative")
    return number


def _validate_max_components(value: object) -> int:
    max_components = _validate_int(value, "max_components")
    if max_components < 2:
        raise ValidationError("max_components cannot be less than 2")
    if max_components > 3:
        raise ValidationError("max_components cannot be greater than 3")
    return max_components


def _date_value(value: object, field_name: str) -> date:
    if isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a date, not datetime")
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an ISO date") from exc
    raise ValidationError(f"{field_name} must be a date string or date")


def _movement_id(movement: dict[str, object]) -> str:
    for key in (
        "ledger_cash_movement_id",
        "cash_movement_id",
        "journal_entry_line_id",
        "line_id",
    ):
        value = movement.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    journal_entry_id = movement.get("journal_entry_id")
    amount_cents = movement.get("amount_cents")
    entry_date = movement.get("entry_date")
    return f"movement:{journal_entry_id}:{entry_date}:{amount_cents}"


def _line_id(movement: dict[str, object]) -> str | None:
    for key in ("journal_entry_line_id", "line_id"):
        value = movement.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _movement_sort_key(movement: dict[str, object]) -> tuple[object, ...]:
    return (
        _date_value(movement.get("entry_date"), "entry_date").isoformat(),
        _validate_int(movement.get("amount_cents"), "amount_cents"),
        str(movement.get("journal_entry_id") or ""),
        str(_line_id(movement) or ""),
        _movement_id(movement),
    )


def _bank_description(bank_transaction: dict[str, object]) -> str | None:
    normalized = bank_transaction.get("description_normalized")
    raw = bank_transaction.get("description_raw")
    description = bank_transaction.get("description")

    for value in (normalized, raw, description):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _movement_description(movement: dict[str, object]) -> str | None:
    description = movement.get("description")
    line_description = movement.get("line_description")

    for value in (description, line_description):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _same_nonzero_sign(amounts: list[int]) -> bool:
    if not amounts:
        return False
    first = amounts[0]
    if first == 0:
        return False
    if first > 0:
        return all(amount > 0 for amount in amounts)
    return all(amount < 0 for amount in amounts)


def _component_summary(
    movement: dict[str, object],
    *,
    bank_date: date,
    description_score: float,
    date_score: float,
) -> dict[str, object]:
    entry_date = _date_value(movement.get("entry_date"), "entry_date")
    return {
        "ledger_cash_movement_id": _movement_id(movement),
        "journal_entry_id": movement.get("journal_entry_id"),
        "journal_entry_line_id": _line_id(movement),
        "entry_date": entry_date.isoformat(),
        "amount_cents": _validate_int(movement.get("amount_cents"), "amount_cents"),
        "description": movement.get("description"),
        "line_description": movement.get("line_description"),
        "date_delta_days": abs((bank_date - entry_date).days),
        "date_score": date_score,
        "description_score": description_score,
    }


def score_split_candidate(
    bank_transaction: dict[str, object],
    component_movements: list[dict[str, object]],
    *,
    amount_tolerance_cents: int = 5,
    date_window_days: int = 3,
    split_penalty: float = 5.0,
) -> dict[str, object]:
    """Score one bank transaction against two or three ledger cash movements."""
    tolerance = _validate_non_negative_int(
        amount_tolerance_cents,
        "amount_tolerance_cents",
    )
    window = _validate_non_negative_int(date_window_days, "date_window_days")
    penalty = _validate_non_negative_number(split_penalty, "split_penalty")

    if not 2 <= len(component_movements) <= 3:
        raise ValidationError("split candidates must contain two or three components")

    bank_amount = _validate_int(bank_transaction.get("amount_cents"), "amount_cents")
    bank_date = _date_value(
        bank_transaction.get("transaction_date"),
         "transaction_date"
    )

    component_amounts = [
        _validate_int(movement.get("amount_cents"), "amount_cents")
        for movement in component_movements
    ]
    component_total = sum(component_amounts)
    component_count = len(component_movements)
    component_movement_ids = [
        _movement_id(movement) for movement in component_movements
    ]

    signs_valid = _same_nonzero_sign(component_amounts) and _same_nonzero_sign(
        [bank_amount, component_amounts[0]],
    )

    amount_delta = bank_amount - component_total
    amount_score = (
        score_amount_match(
            bank_amount,
            component_total,
            tolerance_cents=tolerance,
        )
        if signs_valid
        else 0.0
    )

    bank_description = _bank_description(bank_transaction)
    date_scores: list[float] = []
    description_scores: list[float] = []
    component_date_deltas: list[int] = []
    components: list[dict[str, object]] = []

    for movement in component_movements:
        entry_date = _date_value(movement.get("entry_date"), "entry_date")
        date_delta = abs((bank_date - entry_date).days)
        component_date_deltas.append(date_delta)

        date_score = score_date_match(
            bank_date,
            entry_date,
            date_window_days=window,
        )
        description_score = score_description_match(
            bank_description,
            _movement_description(movement),
        )

        date_scores.append(date_score)
        description_scores.append(description_score)
        components.append(
            _component_summary(
                movement,
                bank_date=bank_date,
                date_score=date_score,
                description_score=description_score,
            ),
        )

    date_delta_days = max(component_date_deltas)
    date_score = min(date_scores) if date_scores else 0.0
    description_score = max(description_scores) if description_scores else 0.0

    raw_score = (
        (amount_score * _AMOUNT_WEIGHT)
        + (date_score * _DATE_WEIGHT)
        + (description_score * _DESCRIPTION_WEIGHT)
        - penalty
    )
    final_score = _clamp_score(raw_score)

    reasons: list[str] = []
    if not signs_valid:
        reasons.append("Split components and bank transaction do not share one sign.")
    elif amount_score == 100.0:
        reasons.append("Component total matches the bank amount exactly.")
    elif amount_score > 0.0:
        reasons.append("Component total is within amount tolerance.")
    else:
        reasons.append("Component total is outside amount tolerance.")

    if date_score == 100.0:
        reasons.append("Every component date matches the bank date exactly.")
    elif date_score > 0.0:
        reasons.append("Every component date is inside the date window.")
    else:
        reasons.append("At least one component date is outside the date window.")

    if description_score == 100.0:
        reasons.append("At least one component description matches the bank text.")
    elif description_score > 0.0:
        reasons.append("At least one component description supports the match.")
    else:
        reasons.append("Descriptions do not provide useful support.")

    if penalty:
        reasons.append("Split penalty was applied.")

    return {
        "score": final_score,
        "amount_score": amount_score,
        "date_score": date_score,
        "description_score": description_score,
        "split_penalty": penalty,
        "amount_delta_cents": amount_delta,
        "date_delta_days": date_delta_days,
        "component_count": component_count,
        "component_total_cents": component_total,
        "component_movement_ids": component_movement_ids,
        "components": components,
        "score_explanation": {
            "formula": (
                "score = amount_score * 0.70 + date_score * 0.25 "
                "+ description_score * 0.05 - split_penalty"
            ),
            "description_score_method": "best_component_description_score",
            "date_score_method": "minimum_component_date_score",
            "component_date_delta_days": component_date_deltas,
            "reason": " ".join(reasons),
            "reasons": reasons,
        },
    }


def _candidate_sort_key(candidate: dict[str, object]) -> tuple[object, ...]:
    return (
        -float(candidate["score"]),
        abs(int(candidate["amount_delta_cents"])),
        int(candidate["date_delta_days"]),
        int(candidate["component_count"]),
        tuple(str(value) for value in candidate["component_movement_ids"]),
    )


def find_split_candidates(
    bank_transaction: dict[str, object],
    ledger_cash_movements: list[dict[str, object]],
    *,
    amount_tolerance_cents: int = 5,
    date_window_days: int = 3,
    max_components: int = 3,
) -> list[dict[str, object]]:
    """Return bounded two- or three-component split candidates."""
    tolerance = _validate_non_negative_int(
        amount_tolerance_cents,
        "amount_tolerance_cents",
    )
    window = _validate_non_negative_int(date_window_days, "date_window_days")
    max_component_count = _validate_max_components(max_components)

    bank_amount = _validate_int(bank_transaction.get("amount_cents"), "amount_cents")
    bank_date = _date_value(
        bank_transaction.get("transaction_date"), 
        "transaction_date"
    )

    sorted_movements = sorted(ledger_cash_movements, key=_movement_sort_key)
    candidates: list[dict[str, object]] = []

    for component_count in range(2, max_component_count + 1):
        for component_tuple in combinations(sorted_movements, component_count):
            components = list(component_tuple)
            amounts = [
                _validate_int(movement.get("amount_cents"), "amount_cents")
                for movement in components
            ]

            if not _same_nonzero_sign(amounts):
                continue
            if not _same_nonzero_sign([bank_amount, amounts[0]]):
                continue

            total = sum(amounts)
            if abs(bank_amount - total) > tolerance:
                continue

            date_deltas = [
                abs(
                    (
                        bank_date
                        - _date_value(movement.get("entry_date"), "entry_date")
                    ).days
                )
                for movement in components
            ]
            if any(delta > window for delta in date_deltas):
                continue

            candidate = score_split_candidate(
                bank_transaction,
                components,
                amount_tolerance_cents=tolerance,
                date_window_days=window,
            )
            candidates.append(candidate)

    candidates.sort(key=_candidate_sort_key)
    return candidates


__all__ = [
    "find_split_candidates",
    "score_split_candidate",
]
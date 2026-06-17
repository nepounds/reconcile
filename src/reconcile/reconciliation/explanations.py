"""Build JSON-serializable reconciliation match explanations."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _iso(value: object) -> object:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def build_exact_match_explanation(
    *,
    bank_transaction_id: str,
    ledger_cash_movement_id: str | None,
    amount_cents: int,
    transaction_date: object,
    entry_date: object,
    reason: str = "amount_and_date_matched_exactly",
    candidate_count: int | None = None,
    blocked_reason: str | None = None,
    duplicate_group_id: str | None = None,
) -> dict[str, object]:
    """Return a plain explanation for an exact amount/date match decision."""
    explanation: dict[str, object] = {
        "reason": reason,
        "bank_transaction_id": bank_transaction_id,
        "ledger_cash_movement_id": ledger_cash_movement_id,
        "amount_cents": amount_cents,
        "transaction_date": _iso(transaction_date),
        "entry_date": _iso(entry_date),
        "matched_fields": ["amount_cents", "transaction_date"],
        "message": "Bank amount and ledger cash movement date matched exactly.",
    }
    if candidate_count is not None:
        explanation["candidate_count"] = candidate_count
    if blocked_reason is not None:
        explanation["blocked_reason"] = blocked_reason
    if duplicate_group_id is not None:
        explanation["duplicate_group_id"] = duplicate_group_id
    return explanation


def build_unmatched_explanation(
    *,
    bank_transaction_id: str,
    amount_cents: int,
    transaction_date: object,
    reason: str = "no_exact_ledger_cash_movement_matched",
    ledger_cash_movement_id: str | None = None,
    entry_date: object | None = None,
    duplicate_group_id: str | None = None,
    blocked_reason: str | None = None,
    candidate_count: int | None = None,
) -> dict[str, object]:
    """Return a plain explanation for an unmatched bank transaction."""
    explanation: dict[str, Any] = {
        "reason": reason,
        "bank_transaction_id": bank_transaction_id,
        "ledger_cash_movement_id": ledger_cash_movement_id,
        "amount_cents": amount_cents,
        "transaction_date": _iso(transaction_date),
        "entry_date": _iso(entry_date),
        "message": "No exact ledger cash movement matched this bank transaction.",
    }
    if duplicate_group_id is not None:
        explanation["duplicate_group_id"] = duplicate_group_id
    if blocked_reason is not None:
        explanation["blocked_reason"] = blocked_reason
    if candidate_count is not None:
        explanation["candidate_count"] = candidate_count
    return explanation


__all__ = [
    "build_exact_match_explanation",
    "build_unmatched_explanation",
]

"""Trial balance report generation from projected ledger state."""

from __future__ import annotations

import sqlite3
from typing import Any

from reconcile.accounts.models import VALID_ACCOUNT_TYPES, VALID_NORMAL_BALANCES
from reconcile.exceptions import ValidationError

TRIAL_BALANCE_QUERY = """
    SELECT
        a.account_id AS account_id,
        a.code AS account_code,
        a.name AS account_name,
        a.account_type AS account_type,
        a.normal_balance AS normal_balance,
        COALESCE(b.debit_total_cents, 0) AS debit_total_cents,
        COALESCE(b.credit_total_cents, 0) AS credit_total_cents,
        COALESCE(b.balance_cents, 0) AS balance_cents
    FROM accounts AS a
    LEFT JOIN account_balances AS b
        ON b.account_id = a.account_id
    ORDER BY a.code ASC, a.account_id ASC
"""


def generate_trial_balance(
    connection: sqlite3.Connection,
) -> list[dict[str, int | str]]:
    """Generate trial balance rows from account and balance projections."""
    rows = connection.execute(TRIAL_BALANCE_QUERY).fetchall()
    return [_build_trial_balance_row(row) for row in rows]


def trial_balance_totals(
    rows: list[dict[str, int | str]],
) -> dict[str, int | bool]:
    """Summarize debit, credit, and ending balance totals for report rows."""
    total_debits = _sum_int_field(rows, "debit_total_cents")
    total_credits = _sum_int_field(rows, "credit_total_cents")
    total_ending_debits = _sum_int_field(rows, "ending_debit_balance_cents")
    total_ending_credits = _sum_int_field(rows, "ending_credit_balance_cents")

    return {
        "total_debits_cents": total_debits,
        "total_credits_cents": total_credits,
        "total_ending_debit_balance_cents": total_ending_debits,
        "total_ending_credit_balance_cents": total_ending_credits,
        "is_balanced": total_ending_debits == total_ending_credits,
    }


def _build_trial_balance_row(row: sqlite3.Row) -> dict[str, int | str]:
    account_type = _validate_account_type(row["account_type"])
    normal_balance = _validate_normal_balance(row["normal_balance"])
    debit_total = _validate_non_negative_int(
        row["debit_total_cents"],
        "debit_total_cents",
    )
    credit_total = _validate_non_negative_int(
        row["credit_total_cents"],
        "credit_total_cents",
    )
    balance = _validate_int(row["balance_cents"], "balance_cents")
    ending_debit, ending_credit = _ending_balance_columns(
        normal_balance=normal_balance,
        balance_cents=balance,
    )

    return {
        "account_id": _validate_required_str(row["account_id"], "account_id"),
        "account_code": _validate_required_str(row["account_code"], "account_code"),
        "account_name": _validate_required_str(row["account_name"], "account_name"),
        "account_type": account_type,
        "normal_balance": normal_balance,
        "debit_total_cents": debit_total,
        "credit_total_cents": credit_total,
        "ending_debit_balance_cents": ending_debit,
        "ending_credit_balance_cents": ending_credit,
    }


def _ending_balance_columns(
    *,
    normal_balance: str,
    balance_cents: int,
) -> tuple[int, int]:
    if balance_cents == 0:
        return 0, 0

    amount = abs(balance_cents)
    if normal_balance == "debit":
        if balance_cents > 0:
            return amount, 0
        return 0, amount

    if balance_cents > 0:
        return 0, amount
    return amount, 0


def _validate_account_type(value: Any) -> str:
    if not isinstance(value, str) or value not in VALID_ACCOUNT_TYPES:
        raise ValidationError(f"invalid account_type in trial balance: {value!r}")
    return value


def _validate_normal_balance(value: Any) -> str:
    if not isinstance(value, str) or value not in VALID_NORMAL_BALANCES:
        raise ValidationError(f"invalid normal_balance in trial balance: {value!r}")
    return value


def _validate_required_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"invalid {field_name} in trial balance: {value!r}")
    return value


def _validate_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"invalid {field_name} in trial balance: {value!r}")
    return value


def _validate_non_negative_int(value: Any, field_name: str) -> int:
    cents = _validate_int(value, field_name)
    if cents < 0:
        raise ValidationError(f"invalid {field_name} in trial balance: {value!r}")
    return cents


def _sum_int_field(rows: list[dict[str, int | str]], field_name: str) -> int:
    total = 0
    for row in rows:
        value = row.get(field_name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(f"invalid {field_name} in trial balance totals")
        total += value
    return total

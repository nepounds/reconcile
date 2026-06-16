"""Account balance projection helpers."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any

from reconcile.accounts.models import NormalBalance, validate_normal_balance
from reconcile.events.models import LedgerEvent
from reconcile.exceptions import ValidationError

BalanceRow = dict[str, int | str | None]


def apply_journal_entry_posted_to_balances(
    connection: sqlite3.Connection,
    event: LedgerEvent,
) -> None:
    """Apply a JournalEntryPosted event to the account_balances projection."""
    if event.event_type != "JournalEntryPosted":
        raise ValidationError(
            "balance projection only supports JournalEntryPosted events"
    )   

    if event.event_sequence is None:
        raise ValidationError("event_sequence is required for balance projection")

    lines = _extract_lines(event)
    deltas = _group_line_deltas(lines)
    affected_account_ids = sorted(deltas)

    if _already_applied(connection, affected_account_ids, event.event_sequence):
        return

    updated_at = event.event_timestamp

    for account_id in affected_account_ids:
        normal_balance = _get_account_normal_balance(connection, account_id)
        current_balance = _get_existing_balance_totals(connection, account_id)

        debit_total_cents = (
            current_balance["debit_total_cents"]
            + deltas[account_id]["debit_total_cents"]
        )
        credit_total_cents = (
            current_balance["credit_total_cents"]
            + deltas[account_id]["credit_total_cents"]
        )
        balance_cents = _calculate_balance_cents(
            debit_total_cents=debit_total_cents,
            credit_total_cents=credit_total_cents,
            normal_balance=normal_balance,
        )

        connection.execute(
            """
            INSERT INTO account_balances (
                account_id,
                debit_total_cents,
                credit_total_cents,
                balance_cents,
                updated_at,
                last_event_sequence
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET
                debit_total_cents = excluded.debit_total_cents,
                credit_total_cents = excluded.credit_total_cents,
                balance_cents = excluded.balance_cents,
                updated_at = excluded.updated_at,
                last_event_sequence = excluded.last_event_sequence
            """,
            (
                account_id,
                debit_total_cents,
                credit_total_cents,
                balance_cents,
                updated_at,
                event.event_sequence,
            ),
        )

    connection.commit()


def get_account_balance(
    connection: sqlite3.Connection,
    account_id: str,
) -> BalanceRow | None:
    """Return one account balance row, or None when no projection row exists."""
    if not isinstance(account_id, str) or not account_id.strip():
        raise ValidationError("account_id is required")

    row = connection.execute(
        """
        SELECT
            account_id,
            debit_total_cents,
            credit_total_cents,
            balance_cents,
            updated_at,
            last_event_sequence
        FROM account_balances
        WHERE account_id = ?
        """,
        (account_id,),
    ).fetchone()

    if row is None:
        return None

    return _balance_row_to_dict(row)


def list_account_balances(connection: sqlite3.Connection) -> list[BalanceRow]:
    """Return all account balance rows in stable account_id order."""
    rows = connection.execute(
        """
        SELECT
            account_id,
            debit_total_cents,
            credit_total_cents,
            balance_cents,
            updated_at,
            last_event_sequence
        FROM account_balances
        ORDER BY account_id
        """
    ).fetchall()

    return [_balance_row_to_dict(row) for row in rows]


def _extract_lines(event: LedgerEvent) -> list[dict[str, Any]]:
    lines = event.payload.get("lines")

    if not isinstance(lines, list) or not lines:
        raise ValidationError("JournalEntryPosted payload requires lines")

    for line in lines:
        if not isinstance(line, dict):
            raise ValidationError("journal lines must be dictionaries")

    return lines


def _group_line_deltas(
    lines: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    deltas: dict[str, dict[str, int]] = defaultdict(
        lambda: {"debit_total_cents": 0, "credit_total_cents": 0}
    )

    for line in lines:
        account_id = _validated_account_id(line.get("account_id"))
        side = _validated_side(line.get("side"))
        amount_cents = _validated_amount_cents(line.get("amount_cents"))

        if side == "debit":
            deltas[account_id]["debit_total_cents"] += amount_cents
        else:
            deltas[account_id]["credit_total_cents"] += amount_cents

    return dict(deltas)


def _validated_account_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("journal line account_id is required")
    return value


def _validated_side(value: Any) -> str:
    if value not in {"debit", "credit"}:
        raise ValidationError("journal line side must be debit or credit")
    return str(value)


def _validated_amount_cents(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("journal line amount_cents must be an integer")
    if value <= 0:
        raise ValidationError("journal line amount_cents must be positive")
    return value


def _already_applied(
    connection: sqlite3.Connection,
    account_ids: list[str],
    event_sequence: int,
) -> bool:
    placeholders = ", ".join("?" for _ in account_ids)
    rows = connection.execute(
        f"""
        SELECT account_id, last_event_sequence
        FROM account_balances
        WHERE account_id IN ({placeholders})
        """,
        tuple(account_ids),
    ).fetchall()

    if len(rows) != len(account_ids):
        return False

    return all(
        row["last_event_sequence"] is not None
        and row["last_event_sequence"] >= event_sequence
        for row in rows
    )


def _get_account_normal_balance(
    connection: sqlite3.Connection,
    account_id: str,
) -> str:
    row = connection.execute(
        """
        SELECT normal_balance
        FROM accounts
        WHERE account_id = ?
        """,
        (account_id,),
    ).fetchone()

    if row is None:
        raise ValidationError(f"account does not exist: {account_id}")

    return validate_normal_balance(row["normal_balance"])


def _get_existing_balance_totals(
    connection: sqlite3.Connection,
    account_id: str,
) -> dict[str, int]:
    row = connection.execute(
        """
        SELECT debit_total_cents, credit_total_cents
        FROM account_balances
        WHERE account_id = ?
        """,
        (account_id,),
    ).fetchone()

    if row is None:
        return {"debit_total_cents": 0, "credit_total_cents": 0}

    return {
        "debit_total_cents": row["debit_total_cents"],
        "credit_total_cents": row["credit_total_cents"],
    }


def _calculate_balance_cents(
    *,
    debit_total_cents: int,
    credit_total_cents: int,
    normal_balance: str,
) -> int:
    if normal_balance == NormalBalance.DEBIT:
        return debit_total_cents - credit_total_cents
    if normal_balance == NormalBalance.CREDIT:
        return credit_total_cents - debit_total_cents

    raise ValidationError("invalid normal balance")


def _balance_row_to_dict(sqlite_row: sqlite3.Row) -> BalanceRow:
    return {
        "account_id": sqlite_row["account_id"],
        "debit_total_cents": sqlite_row["debit_total_cents"],
        "credit_total_cents": sqlite_row["credit_total_cents"],
        "balance_cents": sqlite_row["balance_cents"],
        "updated_at": sqlite_row["updated_at"],
        "last_event_sequence": sqlite_row["last_event_sequence"],
    }
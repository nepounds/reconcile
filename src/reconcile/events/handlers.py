"""Projection handlers for ledger events.

Step 7 intentionally handles account-opening events only. Future event types
raise ValidationError until their projection behavior is implemented.
"""

from __future__ import annotations

import sqlite3

from reconcile.accounts.models import Account
from reconcile.events.models import LedgerEvent
from reconcile.exceptions import ValidationError

ACCOUNT_OPENED = "AccountOpened"
_REQUIRED_ACCOUNT_OPENED_FIELDS = {
    "account_id",
    "code",
    "name",
    "account_type",
    "normal_balance",
    "is_active",
    "opened_at",
    "closed_at",
}


def apply_event(connection: sqlite3.Connection, event: LedgerEvent) -> None:
    """Apply a supported ledger event to its projection table."""
    if not isinstance(event, LedgerEvent):
        raise ValidationError("event must be a LedgerEvent")

    if event.event_type == ACCOUNT_OPENED:
        _apply_account_opened(connection, event)
        return

    raise ValidationError(f"unsupported event type for Step 7: {event.event_type}")


def _apply_account_opened(
    connection: sqlite3.Connection,
    event: LedgerEvent,
) -> None:
    payload = event.payload
    missing_fields = sorted(_REQUIRED_ACCOUNT_OPENED_FIELDS - payload.keys())
    if missing_fields:
        joined_fields = ", ".join(missing_fields)
        raise ValidationError(f"AccountOpened payload missing fields: {joined_fields}")

    account = Account(
        account_id=payload["account_id"],
        code=payload["code"],
        name=payload["name"],
        account_type=payload["account_type"],
        normal_balance=payload["normal_balance"],
        is_active=payload["is_active"],
        opened_at=payload["opened_at"],
        closed_at=payload["closed_at"],
    )

    if _account_id_exists(connection, account.account_id):
        raise ValidationError(f"account_id already exists: {account.account_id}")
    if _account_code_exists(connection, account.code):
        raise ValidationError(f"account code already exists: {account.code}")

    try:
        connection.execute(
            """
            INSERT INTO accounts (
                account_id,
                code,
                name,
                account_type,
                normal_balance,
                is_active,
                opened_at,
                closed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account.account_id,
                account.code,
                account.name,
                account.account_type,
                account.normal_balance,
                1 if account.is_active else 0,
                account.opened_at,
                account.closed_at,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise ValidationError("account projection insert failed") from exc

    connection.commit()


def _account_id_exists(connection: sqlite3.Connection, account_id: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM accounts WHERE account_id = ?",
        (account_id,),
    ).fetchone()
    return row is not None


def _account_code_exists(connection: sqlite3.Connection, code: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM accounts WHERE code = ?",
        (code,),
    ).fetchone()
    return row is not None

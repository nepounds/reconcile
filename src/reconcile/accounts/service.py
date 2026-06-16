"""Account application service.

Financial state changes in this module go through ledger events first. The
accounts table is a projection of AccountOpened events, not the source of truth.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from reconcile.accounts.models import Account
from reconcile.events.handlers import apply_event
from reconcile.events.models import LedgerEvent
from reconcile.events.store import append_event
from reconcile.exceptions import ValidationError

ACCOUNT_OPENED = "AccountOpened"


def open_account(
    connection: sqlite3.Connection,
    account: Account,
    *,
    source: str = "manual",
    actor: str | None = None,
    correlation_id: str | None = None,
) -> Account:
    """Open an account by appending and applying an AccountOpened event."""
    if not isinstance(account, Account):
        raise ValidationError("account must be an Account")

    # Rebuild the model to keep service-level validation explicit even when a
    # caller passes an Account instance that was created elsewhere.
    validated_account = Account(
        account_id=account.account_id,
        code=account.code,
        name=account.name,
        account_type=account.account_type,
        normal_balance=account.normal_balance,
        is_active=account.is_active,
        opened_at=account.opened_at,
        closed_at=account.closed_at,
    )

    _reject_duplicate_account_id(connection, validated_account.account_id)
    _reject_duplicate_account_code(connection, validated_account.code)

    timestamp = _utc_timestamp()
    event = LedgerEvent(
        event_id=f"evt-account-opened-{uuid4()}",
        event_type=ACCOUNT_OPENED,
        event_version=1,
        event_timestamp=timestamp,
        effective_date=_effective_date_from_opened_at(validated_account.opened_at),
        source=source,
        actor=actor,
        correlation_id=correlation_id,
        causation_id=None,
        payload=_account_opened_payload(validated_account),
        created_at=timestamp,
    )

    stored_event = append_event(connection, event)

    try:
        apply_event(connection, stored_event)
    except Exception:
        connection.rollback()
        raise

    return validated_account


def get_account_by_id(
    connection: sqlite3.Connection,
    account_id: str,
) -> Account | None:
    """Return an account by account ID, or None when it does not exist."""
    _validate_lookup_value(account_id, "account_id")
    row = connection.execute(
        """
        SELECT account_id, code, name, account_type, normal_balance,
               is_active, opened_at, closed_at
        FROM accounts
        WHERE account_id = ?
        """,
        (account_id,),
    ).fetchone()
    return _account_from_row(row) if row is not None else None


def get_account_by_code(
    connection: sqlite3.Connection,
    code: str,
) -> Account | None:
    """Return an account by account code, or None when it does not exist."""
    _validate_lookup_value(code, "code")
    row = connection.execute(
        """
        SELECT account_id, code, name, account_type, normal_balance,
               is_active, opened_at, closed_at
        FROM accounts
        WHERE code = ?
        """,
        (code,),
    ).fetchone()
    return _account_from_row(row) if row is not None else None


def list_accounts(connection: sqlite3.Connection) -> list[Account]:
    """Return projected accounts in stable account-code order."""
    rows = connection.execute(
        """
        SELECT account_id, code, name, account_type, normal_balance,
               is_active, opened_at, closed_at
        FROM accounts
        ORDER BY code
        """,
    ).fetchall()
    return [_account_from_row(row) for row in rows]


def _account_opened_payload(account: Account) -> dict[str, object]:
    return {
        "account_id": account.account_id,
        "code": account.code,
        "name": account.name,
        "account_type": account.account_type,
        "normal_balance": account.normal_balance,
        "is_active": account.is_active,
        "opened_at": account.opened_at,
        "closed_at": account.closed_at,
    }


def _reject_duplicate_account_id(
    connection: sqlite3.Connection,
    account_id: str,
) -> None:
    if get_account_by_id(connection, account_id) is not None:
        raise ValidationError(f"account_id already exists: {account_id}")


def _reject_duplicate_account_code(
    connection: sqlite3.Connection,
    code: str,
) -> None:
    if get_account_by_code(connection, code) is not None:
        raise ValidationError(f"account code already exists: {code}")


def _validate_lookup_value(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} cannot be blank")


def _account_from_row(row: sqlite3.Row) -> Account:
    return Account(
        account_id=row["account_id"],
        code=row["code"],
        name=row["name"],
        account_type=row["account_type"],
        normal_balance=row["normal_balance"],
        is_active=bool(row["is_active"]),
        opened_at=row["opened_at"],
        closed_at=row["closed_at"],
    )


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _effective_date_from_opened_at(opened_at: str) -> str:
    if "T" in opened_at:
        return opened_at.split("T", 1)[0]
    if len(opened_at) >= 10:
        return opened_at[:10]
    return opened_at

"""Event projection handlers for Reconcile."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from reconcile.events.models import LedgerEvent
from reconcile.exceptions import ValidationError
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.validation import validate_journal_entry


def apply_event(connection: sqlite3.Connection, event: LedgerEvent) -> None:
    """Apply a ledger event to its SQLite projection tables."""
    if event.event_type == "AccountOpened":
        _apply_account_opened(connection, event)
        return

    if event.event_type == "JournalEntryPosted":
        if "lines" not in event.payload:
            raise ValidationError(
                f"unsupported event type: {event.event_type}"
            )
        _apply_journal_entry_posted(connection, event)
        return

    raise ValidationError(f"unsupported event type: {event.event_type}")


def _apply_account_opened(
    connection: sqlite3.Connection,
    event: LedgerEvent,
) -> None:
    payload = event.payload

    _require_payload_fields(
        payload,
        {
            "account_id",
            "code",
            "name",
            "account_type",
            "normal_balance",
            "is_active",
            "opened_at",
            "closed_at",
        },
    )

    _reject_duplicate_account_id(connection, str(payload["account_id"]))
    _reject_duplicate_account_code(connection, str(payload["code"]))

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
                payload["account_id"],
                payload["code"],
                payload["name"],
                payload["account_type"],
                payload["normal_balance"],
                int(bool(payload["is_active"])),
                payload["opened_at"],
                payload["closed_at"],
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise ValidationError("account projection failed") from exc


def _apply_journal_entry_posted(
    connection: sqlite3.Connection,
    event: LedgerEvent,
) -> None:
    journal_entry = _journal_entry_from_payload(event.payload)

    _reject_duplicate_journal_entry_id(
        connection,
        journal_entry.journal_entry_id,
    )
    _validate_line_ids_are_unique_in_projection(connection, journal_entry)
    _validate_referenced_accounts_are_active(connection, journal_entry)

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO journal_entries (
                    journal_entry_id,
                    event_id,
                    entry_date,
                    description,
                    status,
                    reversed_by_entry_id,
                    reversal_of_entry_id,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    journal_entry.journal_entry_id,
                    event.event_id,
                    journal_entry.entry_date.isoformat(),
                    journal_entry.description,
                    "posted",
                    None,
                    None,
                    event.created_at,
                ),
            )

            for line in journal_entry.lines:
                connection.execute(
                    """
                    INSERT INTO journal_entry_lines (
                        line_id,
                        journal_entry_id,
                        account_id,
                        side,
                        amount_cents,
                        description,
                        line_number
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        line.line_id,
                        line.journal_entry_id,
                        line.account_id,
                        line.side,
                        line.amount_cents,
                        line.description,
                        line.line_number,
                    ),
                )
    except sqlite3.IntegrityError as exc:
        raise ValidationError("journal entry projection failed") from exc


def _journal_entry_from_payload(
    payload: dict[str, object],
) -> JournalEntry:
    lines_payload = payload.get("lines")
    if not isinstance(lines_payload, list):
        raise ValidationError("journal entry payload lines must be a list")

    lines = [
        _journal_line_from_payload(line_payload)
        for line_payload in lines_payload
    ]

    try:
        entry_date = datetime.fromisoformat(
            str(payload["entry_date"]),
        ).date()
    except (KeyError, ValueError) as exc:
        raise ValidationError("invalid journal entry payload date") from exc

    try:
        journal_entry = JournalEntry(
            journal_entry_id=str(payload["journal_entry_id"]),
            entry_date=entry_date,
            description=str(payload["description"]),
            lines=lines,
            source=str(payload.get("source", "event")),
            external_reference=payload.get("external_reference"),
        )
    except TypeError:
        journal_entry = JournalEntry(
            journal_entry_id=str(payload["journal_entry_id"]),
            entry_date=entry_date,
            description=str(payload["description"]),
            lines=lines,
            external_reference=payload.get("external_reference"),
        )

    validate_journal_entry(journal_entry)
    return journal_entry


def _journal_line_from_payload(
    payload: object,
) -> JournalLine:
    if not isinstance(payload, dict):
        raise ValidationError("journal line payload must be a dictionary")

    return JournalLine(
        line_id=str(payload["line_id"]),
        journal_entry_id=str(payload["journal_entry_id"]),
        account_id=str(payload["account_id"]),
        side=str(payload["side"]),
        amount_cents=payload["amount_cents"],
        description=payload.get("description"),
        line_number=payload["line_number"],
    )


def _reject_duplicate_account_id(
    connection: sqlite3.Connection,
    account_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT 1
        FROM accounts
        WHERE account_id = ?
        """,
        (account_id,),
    ).fetchone()

    if row is not None:
        raise ValidationError(f"account_id already exists: {account_id}")


def _reject_duplicate_account_code(
    connection: sqlite3.Connection,
    code: str,
) -> None:
    row = connection.execute(
        """
        SELECT 1
        FROM accounts
        WHERE code = ?
        """,
        (code,),
    ).fetchone()

    if row is not None:
        raise ValidationError(f"account code already exists: {code}")


def _reject_duplicate_journal_entry_id(
    connection: sqlite3.Connection,
    journal_entry_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT 1
        FROM journal_entries
        WHERE journal_entry_id = ?
        """,
        (journal_entry_id,),
    ).fetchone()

    if row is not None:
        raise ValidationError(
            f"duplicate journal_entry_id: {journal_entry_id}",
        )


def _validate_line_ids_are_unique_in_projection(
    connection: sqlite3.Connection,
    journal_entry: JournalEntry,
) -> None:
    for line in journal_entry.lines:
        row = connection.execute(
            """
            SELECT 1
            FROM journal_entry_lines
            WHERE line_id = ?
            """,
            (line.line_id,),
        ).fetchone()

        if row is not None:
            raise ValidationError(f"duplicate journal line_id: {line.line_id}")


def _validate_referenced_accounts_are_active(
    connection: sqlite3.Connection,
    journal_entry: JournalEntry,
) -> None:
    for account_id in {line.account_id for line in journal_entry.lines}:
        row = connection.execute(
            """
            SELECT is_active
            FROM accounts
            WHERE account_id = ?
            """,
            (account_id,),
        ).fetchone()

        if row is None:
            raise ValidationError(f"missing account: {account_id}")

        if int(row["is_active"]) != 1:
            raise ValidationError(f"inactive account: {account_id}")
        

def _require_payload_fields(
    payload: dict[str, object],
    required_fields: set[str],
) -> None:
    missing_fields = sorted(required_fields - set(payload))
    if missing_fields:
        raise ValidationError(
            f"missing fields in event payload: {', '.join(missing_fields)}"
        )
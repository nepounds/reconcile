"""Journal posting services for Reconcile."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from reconcile.events.handlers import apply_event
from reconcile.events.models import LedgerEvent
from reconcile.events.store import append_event
from reconcile.exceptions import ValidationError
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.validation import validate_journal_entry


def post_journal_entry(
    connection: sqlite3.Connection,
    journal_entry: JournalEntry,
    *,
    source: str = "manual",
    actor: str | None = None,
    correlation_id: str | None = None,
) -> JournalEntry:
    """Post a balanced journal entry through an append-only event."""
    validate_journal_entry(journal_entry)
    clean_source = _validate_required_string(source, "source")

    _reject_duplicate_journal_entry_id(
        connection,
        journal_entry.journal_entry_id,
    )
    _validate_referenced_accounts_are_active(connection, journal_entry)

    timestamp = datetime.now(UTC).isoformat()
    event = LedgerEvent(
        event_id=f"evt-{uuid4()}",
        event_type="JournalEntryPosted",
        event_version=1,
        event_timestamp=timestamp,
        effective_date=journal_entry.entry_date.isoformat(),
        source=clean_source,
        actor=actor,
        correlation_id=correlation_id,
        causation_id=None,
        payload=_journal_entry_payload(journal_entry, clean_source),
        created_at=timestamp,
    )

    stored_event = append_event(connection, event)
    apply_event(connection, stored_event)

    return journal_entry


def get_journal_entry_by_id(
    connection: sqlite3.Connection,
    journal_entry_id: str,
) -> JournalEntry | None:
    """Return a posted journal entry by ID, or None when missing."""
    clean_id = _validate_required_string(
        journal_entry_id,
        "journal_entry_id",
    )

    entry_row = connection.execute(
        """
        SELECT
            journal_entry_id,
            entry_date,
            description
        FROM journal_entries
        WHERE journal_entry_id = ?
        """,
        (clean_id,),
    ).fetchone()

    if entry_row is None:
        return None

    return _journal_entry_from_row(connection, entry_row)


def list_journal_entries(
    connection: sqlite3.Connection,
) -> list[JournalEntry]:
    """Return posted journal entries in stable entry-date order."""
    entry_rows = connection.execute(
        """
        SELECT
            journal_entry_id,
            entry_date,
            description
        FROM journal_entries
        ORDER BY entry_date, journal_entry_id
        """
    ).fetchall()

    return [
        _journal_entry_from_row(connection, entry_row)
        for entry_row in entry_rows
    ]


def _journal_entry_payload(
    journal_entry: JournalEntry,
    source: str,
) -> dict[str, object]:
    return {
        "journal_entry_id": journal_entry.journal_entry_id,
        "entry_date": journal_entry.entry_date.isoformat(),
        "description": journal_entry.description,
        "source": source,
        "external_reference": journal_entry.external_reference,
        "lines": [
            {
                "line_id": line.line_id,
                "journal_entry_id": line.journal_entry_id,
                "account_id": line.account_id,
                "side": line.side,
                "amount_cents": line.amount_cents,
                "description": line.description,
                "line_number": line.line_number,
            }
            for line in journal_entry.lines
        ],
    }


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


def _journal_entry_from_row(
    connection: sqlite3.Connection,
    entry_row: sqlite3.Row,
) -> JournalEntry:
    line_rows = connection.execute(
        """
        SELECT
            line_id,
            journal_entry_id,
            account_id,
            side,
            amount_cents,
            description,
            line_number
        FROM journal_entry_lines
        WHERE journal_entry_id = ?
        ORDER BY line_number
        """,
        (entry_row["journal_entry_id"],),
    ).fetchall()

    lines = [
        JournalLine(
            line_id=row["line_id"],
            journal_entry_id=row["journal_entry_id"],
            account_id=row["account_id"],
            side=row["side"],
            amount_cents=row["amount_cents"],
            description=row["description"],
            line_number=row["line_number"],
        )
        for row in line_rows
    ]

    return _make_journal_entry(
        journal_entry_id=entry_row["journal_entry_id"],
        entry_date=datetime.fromisoformat(entry_row["entry_date"]).date(),
        description=entry_row["description"],
        lines=lines,
        source="projection",
        external_reference=None,
    )


def _make_journal_entry(
    *,
    journal_entry_id: str,
    entry_date,
    description: str,
    lines: list[JournalLine],
    source: str,
    external_reference: str | None,
) -> JournalEntry:
    try:
        return JournalEntry(
            journal_entry_id=journal_entry_id,
            entry_date=entry_date,
            description=description,
            lines=lines,
            source=source,
            external_reference=external_reference,
        )
    except TypeError:
        return JournalEntry(
            journal_entry_id=journal_entry_id,
            entry_date=entry_date,
            description=description,
            lines=lines,
            external_reference=external_reference,
        )


def _validate_required_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")

    clean_value = value.strip()
    if not clean_value:
        raise ValidationError(f"{field_name} cannot be blank")

    return clean_value
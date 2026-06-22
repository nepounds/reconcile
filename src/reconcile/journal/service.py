"""Journal posting services for Reconcile."""

from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
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
            line_id=str(row["line_id"]),
            journal_entry_id=str(row["journal_entry_id"]),
            account_id=str(row["account_id"]),
            side=str(row["side"]),
            amount_cents=int(row["amount_cents"]),
            description=(
                str(row["description"])
                if row["description"] is not None
                else None
            ),
            line_number=int(row["line_number"]),
        )
        for row in line_rows
    ]

    return _make_journal_entry(
        journal_entry_id=str(entry_row["journal_entry_id"]),
        entry_date=datetime.fromisoformat(str(entry_row["entry_date"])).date(),
        description=str(entry_row["description"]),
        lines=lines,
        source="projection",
        external_reference=None,
    )


def _make_journal_entry(
    *,
    journal_entry_id: str,
    entry_date: date,
    description: str,
    lines: list[JournalLine],
    source: str,
    external_reference: str | None,
) -> JournalEntry:
    return JournalEntry(
        journal_entry_id=journal_entry_id,
        entry_date=entry_date,
        description=description,
        lines=lines,
        source=source,
        external_reference=external_reference,
    )


def _validate_required_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")

    clean_value = value.strip()
    if not clean_value:
        raise ValidationError(f"{field_name} cannot be blank")

    return clean_value


def reverse_journal_entry(
    connection: sqlite3.Connection,
    journal_entry_id: str,
    *,
    reversal_entry_id: str | None = None,
    reversal_date: date | None = None,
    description: str | None = None,
    source: str = "manual",
    actor: str | None = None,
    correlation_id: str | None = None,
) -> JournalEntry:
    """Reverse a posted journal entry through an immutable reversal event."""
    if not isinstance(journal_entry_id, str) or not journal_entry_id.strip():
        raise ValidationError("journal_entry_id cannot be blank")

    original_id = journal_entry_id.strip()
    clean_source = _validate_required_string(source, "source")

    original = connection.execute(
        """
        SELECT
            journal_entry_id,
            entry_date,
            description,
            status,
            reversed_by_entry_id,
            reversal_of_entry_id
        FROM journal_entries
        WHERE journal_entry_id = ?
        """,
        (original_id,),
    ).fetchone()

    if original is None:
        raise ValidationError("original journal entry does not exist")

    if original["status"] != "posted":
        raise ValidationError("only posted journal entries can be reversed")

    if original["reversed_by_entry_id"] is not None:
        raise ValidationError("journal entry has already been reversed")

    if original["reversal_of_entry_id"] is not None:
        raise ValidationError("reversal entries cannot be reversed")

    if reversal_date is None:
        effective_reversal_date = date.fromisoformat(str(original["entry_date"]))
    elif isinstance(reversal_date, datetime) or not isinstance(reversal_date, date):
        raise ValidationError("reversal_date must be a date")
    else:
        effective_reversal_date = reversal_date

    if reversal_entry_id is None:
        final_reversal_id = f"REV-{uuid4()}"
    elif not isinstance(reversal_entry_id, str) or not reversal_entry_id.strip():
        raise ValidationError("reversal_entry_id cannot be blank")
    else:
        final_reversal_id = reversal_entry_id.strip()

    existing_reversal = connection.execute(
        """
        SELECT 1
        FROM journal_entries
        WHERE journal_entry_id = ?
        """,
        (final_reversal_id,),
    ).fetchone()

    if existing_reversal is not None:
        raise ValidationError("reversal journal entry already exists")

    original_lines = connection.execute(
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
        ORDER BY line_number ASC, line_id ASC
        """,
        (original_id,),
    ).fetchall()

    if not original_lines:
        raise ValidationError("original journal entry has no lines")

    final_description = (
        description.strip()
        if isinstance(description, str) and description.strip()
        else f"Reversal of {original_id}: {original['description']}"
    )

    if description is not None and (
        not isinstance(description, str) or not description.strip()
    ):
        raise ValidationError("description cannot be blank")

    reversal_lines: list[JournalLine] = []

    for original_line in original_lines:
        if original_line["side"] == "debit":
            reversal_side = "credit"
        elif original_line["side"] == "credit":
            reversal_side = "debit"
        else:
            raise ValidationError("invalid original journal line side")

        line_number = int(original_line["line_number"])

        reversal_lines.append(
            JournalLine(
                line_id=f"{final_reversal_id}-line-{line_number}",
                journal_entry_id=final_reversal_id,
                account_id=original_line["account_id"],
                side=reversal_side,
                amount_cents=int(original_line["amount_cents"]),
                description=original_line["description"],
                line_number=line_number,
            )
        )

    reversal_entry = JournalEntry(
        journal_entry_id=final_reversal_id,
        entry_date=effective_reversal_date,
        description=final_description,
        lines=reversal_lines,
        source=clean_source,
        external_reference=original_id,
    )
    validate_journal_entry(reversal_entry)

    now = datetime.now(UTC).isoformat()

    event = LedgerEvent(
        event_id=f"event-{uuid4()}",
        event_type="JournalEntryReversed",
        event_version=1,
        event_timestamp=now,
        effective_date=effective_reversal_date.isoformat(),
        source=clean_source,
        actor=actor,
        correlation_id=correlation_id,
        causation_id=None,
        payload={
            "original_journal_entry_id": original_id,
            "reversal_journal_entry_id": final_reversal_id,
            "reversal_date": effective_reversal_date.isoformat(),
            "description": final_description,
            "source": clean_source,
            "external_reference": original_id,
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
                for line in reversal_lines
            ],
        },
        created_at=now,
    )

    stored_event = append_event(connection, event)
    apply_event(connection, stored_event)

    return reversal_entry
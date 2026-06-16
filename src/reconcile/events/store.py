"""Append-only SQLite event store."""

from __future__ import annotations

import json
import sqlite3

from reconcile.events.models import LedgerEvent
from reconcile.exceptions import ValidationError


def append_event(connection: sqlite3.Connection, event: LedgerEvent) -> LedgerEvent:
    """Append one ledger event and return it with its database sequence."""

    payload_json = json.dumps(event.payload, sort_keys=True, separators=(",", ":"))
    created_at = event.created_at or event.event_timestamp

    try:
        cursor = connection.execute(
            """
            INSERT INTO ledger_events (
                event_id,
                event_type,
                event_version,
                event_timestamp,
                effective_date,
                source,
                actor,
                correlation_id,
                causation_id,
                payload_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.event_type,
                event.event_version,
                event.event_timestamp,
                event.effective_date,
                event.source,
                event.actor,
                event.correlation_id,
                event.causation_id,
                payload_json,
                created_at,
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        raise ValidationError("event_id must be unique") from error

    return LedgerEvent(
        event_sequence=cursor.lastrowid,
        event_id=event.event_id,
        event_type=event.event_type,
        event_version=event.event_version,
        event_timestamp=event.event_timestamp,
        effective_date=event.effective_date,
        source=event.source,
        actor=event.actor,
        correlation_id=event.correlation_id,
        causation_id=event.causation_id,
        payload=event.payload,
        created_at=created_at,
    )


def load_events(connection: sqlite3.Connection) -> list[LedgerEvent]:
    """Load all ledger events ordered by event sequence."""

    rows = connection.execute(
        """
        SELECT
            event_sequence,
            event_id,
            event_type,
            event_version,
            event_timestamp,
            effective_date,
            source,
            actor,
            correlation_id,
            causation_id,
            payload_json,
            created_at
        FROM ledger_events
        ORDER BY event_sequence ASC
        """
    ).fetchall()

    return [_row_to_event(row) for row in rows]


def load_event_by_id(
    connection: sqlite3.Connection,
    event_id: str,
) -> LedgerEvent | None:
    """Load one ledger event by ID, or None when no event exists."""

    if not isinstance(event_id, str) or not event_id.strip():
        raise ValidationError("event_id cannot be blank")

    row = connection.execute(
        """
        SELECT
            event_sequence,
            event_id,
            event_type,
            event_version,
            event_timestamp,
            effective_date,
            source,
            actor,
            correlation_id,
            causation_id,
            payload_json,
            created_at
        FROM ledger_events
        WHERE event_id = ?
        """,
        (event_id,),
    ).fetchone()

    if row is None:
        return None

    return _row_to_event(row)


def load_events_by_type(
    connection: sqlite3.Connection,
    event_type: str,
) -> list[LedgerEvent]:
    """Load ledger events of one type ordered by event sequence."""

    if not isinstance(event_type, str) or not event_type.strip():
        raise ValidationError("event_type cannot be blank")

    rows = connection.execute(
        """
        SELECT
            event_sequence,
            event_id,
            event_type,
            event_version,
            event_timestamp,
            effective_date,
            source,
            actor,
            correlation_id,
            causation_id,
            payload_json,
            created_at
        FROM ledger_events
        WHERE event_type = ?
        ORDER BY event_sequence ASC
        """,
        (event_type,),
    ).fetchall()

    return [_row_to_event(row) for row in rows]


def _row_to_event(row: sqlite3.Row) -> LedgerEvent:
    payload = json.loads(row["payload_json"])

    if not isinstance(payload, dict):
        raise ValidationError("stored payload must be a JSON object")

    return LedgerEvent(
        event_sequence=row["event_sequence"],
        event_id=row["event_id"],
        event_type=row["event_type"],
        event_version=row["event_version"],
        event_timestamp=row["event_timestamp"],
        effective_date=row["effective_date"],
        source=row["source"],
        actor=row["actor"],
        correlation_id=row["correlation_id"],
        causation_id=row["causation_id"],
        payload=payload,
        created_at=row["created_at"],
    )
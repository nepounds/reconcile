"""Projection clearing and rebuild workflow for Reconcile."""

from __future__ import annotations

import sqlite3

from reconcile.events.handlers import apply_event
from reconcile.events.store import load_events

PROJECTION_TABLES_IN_DELETE_ORDER = (
    "reconciliation_match_ledger_links",
    "reconciliation_matches",
    "reconciliation_runs",
    "bank_transactions",
    "bank_statement_imports",
    "account_balances",
    "journal_entry_lines",
    "journal_entries",
    "accounts",
)


def clear_projections(connection: sqlite3.Connection) -> None:
    """Clear derived projection tables without deleting ledger events."""
    for table_name in PROJECTION_TABLES_IN_DELETE_ORDER:
        connection.execute(f"DELETE FROM {table_name}")

    connection.commit()


def _event_sequence_sort_key(event) -> int:
    if event.event_sequence is None:
        return 0

    return event.event_sequence


def rebuild_projections(connection: sqlite3.Connection) -> None:
    """Rebuild all projection tables by replaying append-only ledger events."""
    clear_projections(connection)

    events = sorted(load_events(connection), key=_event_sequence_sort_key)

    for event in events:
        apply_event(connection, event)

    connection.commit()


def projection_row_counts(connection: sqlite3.Connection) -> dict[str, int]:
    """Return row counts for projection tables."""
    counts: dict[str, int] = {}

    for table_name in PROJECTION_TABLES_IN_DELETE_ORDER:
        row = connection.execute(
            f"SELECT COUNT(*) AS row_count FROM {table_name}"
        ).fetchone()
        counts[table_name] = int(row["row_count"])

    return counts
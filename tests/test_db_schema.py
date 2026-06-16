"""Tests for SQLite connection and schema initialization."""

from __future__ import annotations

import sqlite3

import pytest

from reconcile.db import connect, initialize_schema
from reconcile.exceptions import ValidationError

REQUIRED_TABLES = {
    "ledger_events",
    "accounts",
    "journal_entries",
    "journal_entry_lines",
    "account_balances",
    "bank_statement_imports",
    "bank_transactions",
    "reconciliation_runs",
    "reconciliation_matches",
    "reconciliation_match_ledger_links",
}

REQUIRED_COLUMNS = {
    "ledger_events": {
        "event_sequence",
        "event_id",
        "event_type",
        "event_version",
        "event_timestamp",
        "effective_date",
        "source",
        "actor",
        "correlation_id",
        "causation_id",
        "payload_json",
        "created_at",
    },
    "accounts": {
        "account_id",
        "code",
        "name",
        "account_type",
        "normal_balance",
        "is_active",
        "opened_at",
        "closed_at",
    },
    "journal_entries": {
        "journal_entry_id",
        "event_id",
        "entry_date",
        "description",
        "status",
        "reversed_by_entry_id",
        "reversal_of_entry_id",
        "created_at",
    },
    "journal_entry_lines": {
        "line_id",
        "journal_entry_id",
        "account_id",
        "side",
        "amount_cents",
        "description",
        "line_number",
    },
    "account_balances": {
        "account_id",
        "debit_total_cents",
        "credit_total_cents",
        "balance_cents",
        "updated_at",
        "last_event_sequence",
    },
    "bank_statement_imports": {
        "import_id",
        "source_name",
        "file_name",
        "file_hash",
        "imported_at",
        "row_count",
    },
    "bank_transactions": {
        "bank_transaction_id",
        "import_id",
        "transaction_date",
        "posted_date",
        "description_raw",
        "description_normalized",
        "amount_cents",
        "external_id",
        "check_number",
        "row_hash",
        "duplicate_group_id",
        "created_at",
    },
    "reconciliation_runs": {
        "reconciliation_run_id",
        "cash_account_id",
        "statement_start_date",
        "statement_end_date",
        "started_at",
        "completed_at",
        "status",
        "config_json",
    },
    "reconciliation_matches": {
        "reconciliation_match_id",
        "reconciliation_run_id",
        "bank_transaction_id",
        "match_type",
        "score",
        "amount_delta_cents",
        "date_delta_days",
        "status",
        "explanation_json",
        "created_at",
    },
    "reconciliation_match_ledger_links": {
        "reconciliation_match_id",
        "journal_entry_id",
        "journal_entry_line_id",
        "amount_cents",
    },
}


def test_connect_returns_sqlite_connection(tmp_path):
    connection = connect(tmp_path / "reconcile.db")

    try:
        assert isinstance(connection, sqlite3.Connection)
    finally:
        connection.close()


def test_connect_sets_row_factory_to_sqlite_row(tmp_path):
    connection = connect(tmp_path / "reconcile.db")

    try:
        assert connection.row_factory is sqlite3.Row
    finally:
        connection.close()


def test_connect_enables_foreign_keys(tmp_path):
    connection = connect(tmp_path / "reconcile.db")

    try:
        enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        assert enabled == 1
    finally:
        connection.close()


def test_connect_creates_parent_directories(tmp_path):
    db_path = tmp_path / "nested" / "folder" / "reconcile.db"

    connection = connect(db_path)

    try:
        assert db_path.parent.exists()
        assert db_path.exists()
    finally:
        connection.close()


@pytest.mark.parametrize("blank_path", ["", "   "])
def test_connect_rejects_blank_path_values(blank_path):
    with pytest.raises(ValidationError, match="blank"):
        connect(blank_path)


def test_initialize_schema_creates_every_required_table(tmp_path):
    connection = connect(tmp_path / "reconcile.db")

    try:
        initialize_schema(connection)
        tables = _table_names(connection)
        assert REQUIRED_TABLES <= tables
    finally:
        connection.close()


def test_initialize_schema_is_idempotent(tmp_path):
    connection = connect(tmp_path / "reconcile.db")

    try:
        initialize_schema(connection)
        initialize_schema(connection)
        tables = _table_names(connection)
        assert REQUIRED_TABLES <= tables
    finally:
        connection.close()


@pytest.mark.parametrize("table_name", sorted(REQUIRED_COLUMNS))
def test_required_columns_exist_on_each_table(tmp_path, table_name):
    connection = connect(tmp_path / "reconcile.db")

    try:
        initialize_schema(connection)
        columns = _column_names(connection, table_name)
        assert REQUIRED_COLUMNS[table_name] <= columns
    finally:
        connection.close()


def test_ledger_events_event_id_is_unique(tmp_path):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)

    try:
        _insert_ledger_event(connection, "event-1")

        with pytest.raises(sqlite3.IntegrityError):
            _insert_ledger_event(connection, "event-1")
    finally:
        connection.close()


def test_accounts_code_is_unique(tmp_path):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)

    try:
        _insert_account(connection, "account-1", "1000")

        with pytest.raises(sqlite3.IntegrityError):
            _insert_account(connection, "account-2", "1000")
    finally:
        connection.close()


def test_foreign_key_enforcement_works(tmp_path):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)

    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO journal_entries (
                    journal_entry_id,
                    event_id,
                    entry_date,
                    description,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "journal-entry-1",
                    "missing-event",
                    "2026-01-01",
                    "Missing event",
                    "posted",
                    "2026-01-01T00:00:00",
                ),
            )
    finally:
        connection.close()


@pytest.mark.parametrize("side", ["increase", "", "DEBIT"])
def test_journal_entry_lines_side_rejects_invalid_values(tmp_path, side):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)

    try:
        _insert_minimum_journal_dependencies(connection)

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO journal_entry_lines (
                    line_id,
                    journal_entry_id,
                    account_id,
                    side,
                    amount_cents,
                    line_number
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("line-bad-side", "journal-entry-1", "account-1", side, 100, 1),
            )
    finally:
        connection.close()


@pytest.mark.parametrize("amount_cents", [0, -1])
def test_journal_entry_lines_amount_cents_rejects_zero_or_negative_values(
    tmp_path,
    amount_cents,
):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)

    try:
        _insert_minimum_journal_dependencies(connection)

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO journal_entry_lines (
                    line_id,
                    journal_entry_id,
                    account_id,
                    side,
                    amount_cents,
                    line_number
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "line-bad-amount",
                    "journal-entry-1",
                    "account-1",
                    "debit",
                    amount_cents,
                    1,
                ),
            )
    finally:
        connection.close()


def test_ledger_events_event_sequence_autoincrements(tmp_path):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)

    try:
        _insert_ledger_event(connection, "event-1")
        _insert_ledger_event(connection, "event-2")

        rows = connection.execute(
            """
            SELECT event_id, event_sequence
            FROM ledger_events
            ORDER BY event_sequence
            """
        ).fetchall()

        assert [row["event_id"] for row in rows] == ["event-1", "event-2"]
        assert rows[1]["event_sequence"] == rows[0]["event_sequence"] + 1
    finally:
        connection.close()


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()
    return {row["name"] for row in rows}


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _insert_ledger_event(connection: sqlite3.Connection, event_id: str) -> None:
    connection.execute(
        """
        INSERT INTO ledger_events (
            event_id,
            event_type,
            event_timestamp,
            effective_date,
            source,
            payload_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            "TestEvent",
            "2026-01-01T00:00:00",
            "2026-01-01",
            "test",
            "{}",
            "2026-01-01T00:00:00",
        ),
    )


def _insert_account(connection: sqlite3.Connection, account_id: str, code: str) -> None:
    connection.execute(
        """
        INSERT INTO accounts (
            account_id,
            code,
            name,
            account_type,
            normal_balance,
            opened_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (account_id, code, "Cash", "asset", "debit", "2026-01-01T00:00:00"),
    )


def _insert_minimum_journal_dependencies(connection: sqlite3.Connection) -> None:
    _insert_ledger_event(connection, "event-1")
    _insert_account(connection, "account-1", "1000")
    connection.execute(
        """
        INSERT INTO journal_entries (
            journal_entry_id,
            event_id,
            entry_date,
            description,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "journal-entry-1",
            "event-1",
            "2026-01-01",
            "Owner contribution",
            "posted",
            "2026-01-01T00:00:00",
        ),
    )

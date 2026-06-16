"""Tests for projection clearing and rebuild workflows."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.events.models import LedgerEvent
from reconcile.events.store import append_event, load_events
from reconcile.exceptions import ValidationError
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import post_journal_entry
from reconcile.projections.balances import get_account_balance, list_account_balances
from reconcile.projections.rebuild import (
    clear_projections,
    projection_row_counts,
    rebuild_projections,
)


def _connection(tmp_path: Path) -> sqlite3.Connection:
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)
    return connection


def _account(
    account_id: str,
    code: str,
    name: str,
    account_type: str,
    normal_balance: str,
) -> Account:
    return Account(
        account_id=account_id,
        code=code,
        name=name,
        account_type=account_type,
        normal_balance=normal_balance,
        is_active=True,
        opened_at="2026-01-01T00:00:00",
    )


def _open_standard_accounts(connection: sqlite3.Connection) -> None:
    open_account(
        connection,
        account=_account("acct-cash", "1000", "Cash", "asset", "debit"),
    )
    open_account(
        connection,
        account=_account("acct-equity", "3000", "Owner Equity", "equity", "credit"),
    )
    open_account(
        connection,
        account=_account("acct-revenue", "4000", "Revenue", "revenue", "credit"),
    )
    open_account(
        connection,
        account=_account("acct-expense", "5000", "Expense", "expense", "debit"),
    )


def _owner_contribution_entry() -> JournalEntry:
    return JournalEntry(
        journal_entry_id="je-owner-contribution",
        entry_date=date(2026, 1, 1),
        description="Owner contribution",
        source="manual",
        external_reference=None,
        lines=[
            JournalLine(
                line_id="line-owner-cash",
                journal_entry_id="je-owner-contribution",
                account_id="acct-cash",
                side="debit",
                amount_cents=500_000,
                description="Cash received",
                line_number=1,
            ),
            JournalLine(
                line_id="line-owner-equity",
                journal_entry_id="je-owner-contribution",
                account_id="acct-equity",
                side="credit",
                amount_cents=500_000,
                description="Owner equity",
                line_number=2,
            ),
        ],
    )


def _cash_sale_entry() -> JournalEntry:
    return JournalEntry(
        journal_entry_id="je-cash-sale",
        entry_date=date(2026, 1, 2),
        description="Cash sale",
        source="manual",
        external_reference=None,
        lines=[
            JournalLine(
                line_id="line-sale-cash",
                journal_entry_id="je-cash-sale",
                account_id="acct-cash",
                side="debit",
                amount_cents=125_00,
                description="Cash received",
                line_number=1,
            ),
            JournalLine(
                line_id="line-sale-revenue",
                journal_entry_id="je-cash-sale",
                account_id="acct-revenue",
                side="credit",
                amount_cents=125_00,
                description="Revenue earned",
                line_number=2,
            ),
        ],
    )


def _expense_payment_entry() -> JournalEntry:
    return JournalEntry(
        journal_entry_id="je-expense-payment",
        entry_date=date(2026, 1, 3),
        description="Expense payment",
        source="manual",
        external_reference=None,
        lines=[
            JournalLine(
                line_id="line-expense",
                journal_entry_id="je-expense-payment",
                account_id="acct-expense",
                side="debit",
                amount_cents=50_00,
                description="Expense incurred",
                line_number=1,
            ),
            JournalLine(
                line_id="line-expense-cash",
                journal_entry_id="je-expense-payment",
                account_id="acct-cash",
                side="credit",
                amount_cents=50_00,
                description="Cash paid",
                line_number=2,
            ),
        ],
    )


def _post_standard_entries(connection: sqlite3.Connection) -> None:
    post_journal_entry(connection, journal_entry=_owner_contribution_entry())
    post_journal_entry(connection, journal_entry=_cash_sale_entry())
    post_journal_entry(connection, journal_entry=_expense_payment_entry())


def _table_count(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])


def _event_ids(connection: sqlite3.Connection) -> list[str]:
    return [event.event_id for event in load_events(connection)]


def _event_sequences(connection: sqlite3.Connection) -> list[int | None]:
    return [event.event_sequence for event in load_events(connection)]


def _balance_snapshot(connection: sqlite3.Connection) -> list[dict[str, object]]:
    return [dict(row) for row in list_account_balances(connection)]


def _journal_entry_snapshot(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            journal_entry_id,
            event_id,
            entry_date,
            description,
            status,
            reversed_by_entry_id,
            reversal_of_entry_id,
            created_at
        FROM journal_entries
        ORDER BY journal_entry_id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _journal_line_snapshot(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
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
        ORDER BY journal_entry_id, line_number
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _account_snapshot(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            account_id,
            code,
            name,
            account_type,
            normal_balance,
            is_active,
            opened_at,
            closed_at
        FROM accounts
        ORDER BY code
        """
    ).fetchall()
    return [dict(row) for row in rows]


def test_clear_projections_clears_accounts(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    clear_projections(connection)

    assert _table_count(connection, "accounts") == 0


def test_clear_projections_clears_journal_entries(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    post_journal_entry(connection, journal_entry=_owner_contribution_entry())

    clear_projections(connection)

    assert _table_count(connection, "journal_entries") == 0


def test_clear_projections_clears_journal_entry_lines(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    post_journal_entry(connection, journal_entry=_owner_contribution_entry())

    clear_projections(connection)

    assert _table_count(connection, "journal_entry_lines") == 0


def test_clear_projections_clears_account_balances(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    post_journal_entry(connection, journal_entry=_owner_contribution_entry())

    clear_projections(connection)

    assert _table_count(connection, "account_balances") == 0


def test_clear_projections_does_not_clear_ledger_events(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    post_journal_entry(connection, journal_entry=_owner_contribution_entry())
    event_count_before = _table_count(connection, "ledger_events")

    clear_projections(connection)

    assert _table_count(connection, "ledger_events") == event_count_before


def test_clear_projections_can_run_when_tables_are_already_empty(
    tmp_path: Path,
) -> None:
    connection = _connection(tmp_path)

    clear_projections(connection)
    clear_projections(connection)

    assert _table_count(connection, "accounts") == 0
    assert _table_count(connection, "journal_entries") == 0
    assert _table_count(connection, "journal_entry_lines") == 0
    assert _table_count(connection, "account_balances") == 0


def test_rebuild_projections_rebuilds_account_rows_from_events(
    tmp_path: Path,
) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    expected_accounts = _account_snapshot(connection)

    clear_projections(connection)
    rebuild_projections(connection)

    assert _account_snapshot(connection) == expected_accounts


def test_rebuild_projections_rebuilds_journal_entry_rows_from_events(
    tmp_path: Path,
) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)
    expected_entries = _journal_entry_snapshot(connection)

    clear_projections(connection)
    rebuild_projections(connection)

    assert _journal_entry_snapshot(connection) == expected_entries


def test_rebuild_projections_rebuilds_journal_line_rows_from_events(
    tmp_path: Path,
) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)
    expected_lines = _journal_line_snapshot(connection)

    clear_projections(connection)
    rebuild_projections(connection)

    assert _journal_line_snapshot(connection) == expected_lines


def test_rebuild_projections_rebuilds_account_balance_rows_from_events(
    tmp_path: Path,
) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)
    expected_balances = _balance_snapshot(connection)

    clear_projections(connection)
    rebuild_projections(connection)

    assert _balance_snapshot(connection) == expected_balances


def test_rebuilt_balances_match_incremental_balances(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)
    incremental_balances = _balance_snapshot(connection)

    rebuild_projections(connection)

    assert _balance_snapshot(connection) == incremental_balances


def test_rebuilt_debit_totals_match_incremental_debit_totals(
    tmp_path: Path,
) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)
    expected_cash = get_account_balance(connection, "acct-cash")

    rebuild_projections(connection)

    rebuilt_cash = get_account_balance(connection, "acct-cash")
    assert rebuilt_cash["debit_total_cents"] == expected_cash["debit_total_cents"]


def test_rebuilt_credit_totals_match_incremental_credit_totals(
    tmp_path: Path,
) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)
    expected_cash = get_account_balance(connection, "acct-cash")

    rebuild_projections(connection)

    rebuilt_cash = get_account_balance(connection, "acct-cash")
    assert rebuilt_cash["credit_total_cents"] == expected_cash["credit_total_cents"]


def test_rebuilt_normal_balance_aware_balances_match_incremental_balances(
    tmp_path: Path,
) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)

    expected_cash = get_account_balance(connection, "acct-cash")["balance_cents"]
    expected_equity = get_account_balance(connection, "acct-equity")["balance_cents"]
    expected_revenue = get_account_balance(connection, "acct-revenue")["balance_cents"]
    expected_expense = get_account_balance(connection, "acct-expense")["balance_cents"]

    rebuild_projections(connection)

    assert (
    get_account_balance(connection, "acct-cash")["balance_cents"]
    == expected_cash
)
    assert (
        get_account_balance(connection, "acct-equity")["balance_cents"]
        == expected_equity
    )
    assert (
        get_account_balance(connection, "acct-revenue")["balance_cents"]
        == expected_revenue
    )
    assert (
        get_account_balance(connection, "acct-expense")["balance_cents"]
        == expected_expense
    )


def test_rebuild_preserves_event_count(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)
    event_count_before = _table_count(connection, "ledger_events")

    rebuild_projections(connection)

    assert _table_count(connection, "ledger_events") == event_count_before


def test_rebuild_preserves_event_ids(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)
    event_ids_before = _event_ids(connection)

    rebuild_projections(connection)

    assert _event_ids(connection) == event_ids_before


def test_rebuild_preserves_event_sequences(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)
    event_sequences_before = _event_sequences(connection)

    rebuild_projections(connection)

    assert _event_sequences(connection) == event_sequences_before


def test_running_rebuild_twice_is_safe_and_deterministic(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)

    rebuild_projections(connection)
    first_account_snapshot = _account_snapshot(connection)
    first_entry_snapshot = _journal_entry_snapshot(connection)
    first_line_snapshot = _journal_line_snapshot(connection)
    first_balance_snapshot = _balance_snapshot(connection)

    rebuild_projections(connection)

    assert _account_snapshot(connection) == first_account_snapshot
    assert _journal_entry_snapshot(connection) == first_entry_snapshot
    assert _journal_line_snapshot(connection) == first_line_snapshot
    assert _balance_snapshot(connection) == first_balance_snapshot


def test_rebuild_does_not_append_new_events(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)
    events_before = load_events(connection)

    rebuild_projections(connection)

    events_after = load_events(connection)
    assert len(events_after) == len(events_before)
    assert [event.event_id for event in events_after] == [
        event.event_id for event in events_before
    ]


def test_rebuild_does_not_duplicate_journal_lines(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)

    rebuild_projections(connection)
    rebuild_projections(connection)

    assert _table_count(connection, "journal_entry_lines") == 6


def test_rebuild_handles_empty_event_log_by_leaving_projection_tables_empty(
    tmp_path: Path,
) -> None:
    connection = _connection(tmp_path)

    rebuild_projections(connection)

    assert _table_count(connection, "accounts") == 0
    assert _table_count(connection, "journal_entries") == 0
    assert _table_count(connection, "journal_entry_lines") == 0
    assert _table_count(connection, "account_balances") == 0


def test_rebuild_replays_events_in_event_sequence_order(tmp_path: Path) -> None:
    connection = _connection(tmp_path)

    account_opened_event = LedgerEvent(
        event_id="event-open-cash",
        event_type="AccountOpened",
        event_version=1,
        event_timestamp="2026-01-01T00:00:00",
        effective_date="2026-01-01",
        source="manual",
        actor=None,
        correlation_id=None,
        causation_id=None,
        payload={
            "account_id": "acct-cash",
            "code": "1000",
            "name": "Cash",
            "account_type": "asset",
            "normal_balance": "debit",
            "is_active": True,
            "opened_at": "2026-01-01T00:00:00",
            "closed_at": None,
        },
        created_at="2026-01-01T00:00:00",
    )
    journal_entry_event = LedgerEvent(
        event_id="event-post-entry",
        event_type="JournalEntryPosted",
        event_version=1,
        event_timestamp="2026-01-02T00:00:00",
        effective_date="2026-01-02",
        source="manual",
        actor=None,
        correlation_id=None,
        causation_id=None,
        payload={
            "journal_entry_id": "je-1",
            "entry_date": "2026-01-02",
            "description": "Self-balancing cash entry",
            "source": "manual",
            "external_reference": None,
            "lines": [
                {
                    "line_id": "line-1",
                    "journal_entry_id": "je-1",
                    "account_id": "acct-cash",
                    "side": "debit",
                    "amount_cents": 100,
                    "description": None,
                    "line_number": 1,
                },
                {
                    "line_id": "line-2",
                    "journal_entry_id": "je-1",
                    "account_id": "acct-cash",
                    "side": "credit",
                    "amount_cents": 100,
                    "description": None,
                    "line_number": 2,
                },
            ],
        },
        created_at="2026-01-02T00:00:00",
    )

    append_event(connection, account_opened_event)
    append_event(connection, journal_entry_event)

    rebuild_projections(connection)

    assert _table_count(connection, "accounts") == 1
    assert _table_count(connection, "journal_entries") == 1
    assert _table_count(connection, "journal_entry_lines") == 2
    assert get_account_balance(connection, "acct-cash")["balance_cents"] == 0


def test_unsupported_future_event_behavior_remains_consistent(
    tmp_path: Path,
) -> None:
    connection = _connection(tmp_path)
    unsupported_event = LedgerEvent(
        event_id="event-unsupported",
        event_type="JournalEntryReversed",
        event_version=1,
        event_timestamp="2026-01-01T00:00:00",
        effective_date="2026-01-01",
        source="manual",
        actor=None,
        correlation_id=None,
        causation_id=None,
        payload={"journal_entry_id": "je-1"},
        created_at="2026-01-01T00:00:00",
    )
    append_event(connection, unsupported_event)

    with pytest.raises(ValidationError, match="unsupported event type"):
        rebuild_projections(connection)

    assert _table_count(connection, "ledger_events") == 1


def test_projection_row_counts_returns_expected_counts(tmp_path: Path) -> None:
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_standard_entries(connection)

    counts = projection_row_counts(connection)

    assert counts["accounts"] == 4
    assert counts["journal_entries"] == 3
    assert counts["journal_entry_lines"] == 6
    assert counts["account_balances"] == 4
    assert counts["bank_statement_imports"] == 0
    assert counts["bank_transactions"] == 0
    assert counts["reconciliation_runs"] == 0
    assert counts["reconciliation_matches"] == 0
    assert counts["reconciliation_match_ledger_links"] == 0


def test_rebuild_script_exists_and_accepts_db_path_argument(tmp_path: Path) -> None:
    db_path = tmp_path / "script-smoke.db"
    script_path = Path("scripts/rebuild_projections.py")

    assert script_path.exists()

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--db-path",
            str(db_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Projection rebuild complete" in result.stdout
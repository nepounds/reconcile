from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

import pytest

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.events.store import load_events
from reconcile.exceptions import ValidationError
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import post_journal_entry, reverse_journal_entry
from reconcile.reconciliation.cash_movements import (
    extract_ledger_cash_movements,
    get_cash_account,
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
    *,
    is_active: bool = True,
) -> Account:
    return Account(
        account_id=account_id,
        code=code,
        name=name,
        account_type=account_type,
        normal_balance=normal_balance,
        is_active=is_active,
        opened_at="2026-01-01T00:00:00",
    )


def _open_standard_accounts(connection: sqlite3.Connection) -> None:
    open_account(
        connection,
        account=_account("acct-cash", "1000", "Cash", "asset", "debit"),
    )
    open_account(
        connection,
        account=_account("acct-ar", "1100", "Accounts Receivable", "asset", "debit"),
    )
    open_account(
        connection,
        account=_account("acct-ap", "2000", "Accounts Payable", "liability", "credit"),
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


def _post_entry(
    connection: sqlite3.Connection,
    *,
    journal_entry_id: str,
    entry_date: date,
    description: str,
    lines: list[JournalLine],
) -> None:
    post_journal_entry(
        connection,
        journal_entry=JournalEntry(
            journal_entry_id=journal_entry_id,
            entry_date=entry_date,
            description=description,
            lines=lines,
            source="test",
            external_reference=f"EXT-{journal_entry_id}",
        ),
    )


def _line(
    line_id: str,
    journal_entry_id: str,
    account_id: str,
    side: str,
    amount_cents: int,
    line_number: int,
    *,
    description: str | None = None,
) -> JournalLine:
    return JournalLine(
        line_id=line_id,
        journal_entry_id=journal_entry_id,
        account_id=account_id,
        side=side,
        amount_cents=amount_cents,
        description=description,
        line_number=line_number,
    )


def test_empty_database_with_valid_cash_account_returns_empty_list(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account("acct-cash", "1000", "Cash", "asset", "debit"),
    )

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
    )

    assert movements == []


def test_debit_to_cash_becomes_positive_movement(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        journal_entry_id="JE-001",
        entry_date=date(2026, 1, 1),
        description="Owner contribution",
        lines=[
            _line(
                "JE-001-L1",
                "JE-001",
                "acct-cash",
                "debit",
                500000,
                1,
                description="Cash received",
            ),
            _line("JE-001-L2", "JE-001", "acct-equity", "credit", 500000, 2),
        ],
    )

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
    )

    assert len(movements) == 1
    assert movements[0]["amount_cents"] == 500000
    assert movements[0]["side"] == "debit"


def test_credit_to_cash_becomes_negative_movement(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        journal_entry_id="JE-002",
        entry_date=date(2026, 1, 2),
        description="Software payment",
        lines=[
            _line("JE-002-L1", "JE-002", "acct-expense", "debit", 5000, 1),
            _line(
                "JE-002-L2",
                "JE-002",
                "acct-cash",
                "credit",
                5000,
                2,
                description="Cash paid",
            ),
        ],
    )

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
    )

    assert len(movements) == 1
    assert movements[0]["amount_cents"] == -5000
    assert movements[0]["side"] == "credit"


def test_non_cash_journal_lines_are_ignored(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        journal_entry_id="JE-003",
        entry_date=date(2026, 1, 3),
        description="Accrued revenue",
        lines=[
            _line("JE-003-L1", "JE-003", "acct-ar", "debit", 12000, 1),
            _line("JE-003-L2", "JE-003", "acct-revenue", "credit", 12000, 2),
        ],
    )

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
    )

    assert movements == []


def test_multiple_cash_movements_are_deterministically_ordered(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        journal_entry_id="JE-020",
        entry_date=date(2026, 1, 2),
        description="Second date",
        lines=[
            _line("JE-020-L1", "JE-020", "acct-cash", "debit", 2000, 1),
            _line("JE-020-L2", "JE-020", "acct-equity", "credit", 2000, 2),
        ],
    )
    _post_entry(
        connection,
        journal_entry_id="JE-010",
        entry_date=date(2026, 1, 1),
        description="First date",
        lines=[
            _line("JE-010-L1", "JE-010", "acct-cash", "debit", 1000, 1),
            _line("JE-010-L2", "JE-010", "acct-equity", "credit", 1000, 2),
        ],
    )
    _post_entry(
        connection,
        journal_entry_id="JE-011",
        entry_date=date(2026, 1, 1),
        description="Same date later ID",
        lines=[
            _line("JE-011-L2", "JE-011", "acct-cash", "debit", 1100, 2),
            _line("JE-011-L1", "JE-011", "acct-equity", "credit", 1100, 1),
        ],
    )

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
    )

    assert [
        movement["journal_entry_line_id"] for movement in movements
    ] == [
        "JE-010-L1",
        "JE-011-L2",
        "JE-020-L1",
    ]


def test_returned_movement_includes_required_metadata(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        journal_entry_id="JE-004",
        entry_date=date(2026, 1, 4),
        description="Owner contribution",
        lines=[
            _line(
                "JE-004-L1",
                "JE-004",
                "acct-cash",
                "debit",
                500000,
                1,
                description="Cash received",
            ),
            _line("JE-004-L2", "JE-004", "acct-equity", "credit", 500000, 2),
        ],
    )

    movement = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
    )[0]

    assert movement == {
        "ledger_cash_movement_id": "cashmov-JE-004-L1",
        "journal_entry_id": "JE-004",
        "journal_entry_line_id": "JE-004-L1",
        "entry_date": "2026-01-04",
        "description": "Owner contribution",
        "line_description": "Cash received",
        "cash_account_id": "acct-cash",
        "cash_account_code": "1000",
        "cash_account_name": "Cash",
        "side": "debit",
        "amount_cents": 500000,
        "source": None,
        "external_reference": None,
        "is_reversal": False,
        "reversal_of_entry_id": None,
        "reversed_by_entry_id": None,
    }


def test_start_date_excludes_earlier_entries(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)
    _post_cash_deposit(connection, "JE-002", date(2026, 1, 2), 2000)

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
        start_date=date(2026, 1, 2),
    )

    assert [movement["journal_entry_id"] for movement in movements] == ["JE-002"]


def test_end_date_excludes_later_entries(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)
    _post_cash_deposit(connection, "JE-002", date(2026, 1, 2), 2000)

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
        end_date=date(2026, 1, 1),
    )

    assert [movement["journal_entry_id"] for movement in movements] == ["JE-001"]


def test_inclusive_range_includes_same_day_start_and_end_entries(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)
    _post_cash_deposit(connection, "JE-002", date(2026, 1, 2), 2000)
    _post_cash_deposit(connection, "JE-003", date(2026, 1, 3), 3000)

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
    )

    assert [movement["journal_entry_id"] for movement in movements] == [
        "JE-001",
        "JE-002",
    ]


def test_start_date_equal_to_end_date_works(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)
    _post_cash_deposit(connection, "JE-002", date(2026, 1, 2), 2000)

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 2),
    )

    assert [movement["journal_entry_id"] for movement in movements] == ["JE-002"]


def test_start_date_after_end_date_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    with pytest.raises(ValidationError, match="start_date"):
        extract_ledger_cash_movements(
            connection,
            cash_account_id="acct-cash",
            start_date=date(2026, 1, 3),
            end_date=date(2026, 1, 2),
        )


def test_string_date_arguments_raise_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    with pytest.raises(ValidationError, match="start_date"):
        extract_ledger_cash_movements(
            connection,
            cash_account_id="acct-cash",
            start_date="2026-01-01",  # type: ignore[arg-type]
        )


def test_datetime_arguments_raise_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    with pytest.raises(ValidationError, match="start_date"):
        extract_ledger_cash_movements(
            connection,
            cash_account_id="acct-cash",
            start_date=datetime(2026, 1, 1, 12, 0),
        )


def test_blank_cash_account_id_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)

    with pytest.raises(ValidationError, match="cash_account_id"):
        extract_ledger_cash_movements(connection, cash_account_id=" ")


def test_missing_cash_account_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)

    with pytest.raises(ValidationError, match="does not exist"):
        extract_ledger_cash_movements(connection, cash_account_id="missing")


def test_non_asset_selected_account_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account("acct-liability", "2000", "Payable", "liability", "credit"),
    )

    with pytest.raises(ValidationError, match="account_type='asset'"):
        extract_ledger_cash_movements(
            connection,
            cash_account_id="acct-liability",
        )


def test_credit_normal_selected_account_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
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
            "acct-bad-cash",
            "1999",
            "Bad Cash",
            "asset",
            "credit",
            1,
            "2026-01-01T00:00:00",
            None,
        ),
    )
    connection.commit()

    with pytest.raises(ValidationError, match="normal_balance='debit'"):
        get_cash_account(connection, "acct-bad-cash")


def test_inactive_asset_debit_cash_account_can_still_be_read(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account(
            "acct-old-cash",
            "1000",
            "Old Cash",
            "asset",
            "debit",
            is_active=False,
        ),
    )

    account = get_cash_account(connection, "acct-old-cash")

    assert account["account_id"] == "acct-old-cash"


def test_reversed_original_and_reversal_are_excluded_by_default(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)

    reverse_journal_entry(
        connection,
        journal_entry_id="JE-001",
        reversal_entry_id="JE-001-REV",
    )

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
    )

    assert movements == []


def test_include_reversed_returns_original_and_reversal_rows(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)

    reverse_journal_entry(
        connection,
        journal_entry_id="JE-001",
        reversal_entry_id="JE-001-REV",
    )

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
        include_reversed=True,
    )

    assert [movement["journal_entry_id"] for movement in movements] == [
        "JE-001",
        "JE-001-REV",
    ]
    assert [movement["amount_cents"] for movement in movements] == [1000, -1000]


def test_reversal_rows_are_marked_and_linked(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)

    reverse_journal_entry(
        connection,
        journal_entry_id="JE-001",
        reversal_entry_id="JE-001-REV",
    )

    original, reversal = extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
        include_reversed=True,
    )

    assert original["is_reversal"] is False
    assert original["reversed_by_entry_id"] == "JE-001-REV"
    assert original["reversal_of_entry_id"] is None

    assert reversal["is_reversal"] is True
    assert reversal["reversal_of_entry_id"] == "JE-001"
    assert reversal["reversed_by_entry_id"] is None


def test_extraction_does_not_append_ledger_events(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)
    before = len(load_events(connection))

    extract_ledger_cash_movements(connection, cash_account_id="acct-cash")

    after = len(load_events(connection))
    assert after == before


def test_extraction_does_not_modify_accounting_projection_tables(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)

    before = _table_counts(
        connection,
        [
            "accounts",
            "journal_entries",
            "journal_entry_lines",
            "account_balances",
        ],
    )

    extract_ledger_cash_movements(connection, cash_account_id="acct-cash")

    after = _table_counts(
        connection,
        [
            "accounts",
            "journal_entries",
            "journal_entry_lines",
            "account_balances",
        ],
    )

    assert after == before


def test_extraction_does_not_modify_bank_transaction_tables(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)

    connection.execute(
        """
        INSERT INTO bank_statement_imports (
            import_id,
            source_name,
            file_name,
            file_hash,
            imported_at,
            row_count
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("import-1", "test", "bank.csv", "hash", "2026-01-01T00:00:00", 1),
    )
    connection.execute(
        """
        INSERT INTO bank_transactions (
            bank_transaction_id,
            import_id,
            transaction_date,
            posted_date,
            description_raw,
            description_normalized,
            amount_cents,
            external_id,
            check_number,
            row_hash,
            duplicate_group_id,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "bank-1",
            "import-1",
            "2026-01-01",
            "2026-01-01",
            "DEPOSIT",
            "deposit",
            1000,
            "EXT-1",
            None,
            "row-hash",
            None,
            "2026-01-01T00:00:00",
        ),
    )
    connection.commit()

    before = _table_counts(
        connection,
        ["bank_statement_imports", "bank_transactions"],
    )

    extract_ledger_cash_movements(connection, cash_account_id="acct-cash")

    after = _table_counts(
        connection,
        ["bank_statement_imports", "bank_transactions"],
    )

    assert after == before


def test_invalid_stored_line_side_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)

    connection.execute("PRAGMA ignore_check_constraints = ON")
    connection.execute(
        "UPDATE journal_entry_lines SET side = ? WHERE line_id = ?",
        ("bad-side", "JE-001-L1"),
    )
    connection.commit()
    connection.execute("PRAGMA ignore_check_constraints = OFF")

    with pytest.raises(ValidationError, match="invalid journal line side"):
        extract_ledger_cash_movements(connection, cash_account_id="acct-cash")


def test_invalid_stored_amount_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, "JE-001", date(2026, 1, 1), 1000)

    connection.execute("PRAGMA ignore_check_constraints = ON")
    connection.execute(
        "UPDATE journal_entry_lines SET amount_cents = ? WHERE line_id = ?",
        ("not-an-int", "JE-001-L1"),
    )
    connection.commit()
    connection.execute("PRAGMA ignore_check_constraints = OFF")

    with pytest.raises(ValidationError, match="amount_cents"):
        extract_ledger_cash_movements(connection, cash_account_id="acct-cash")


def _post_cash_deposit(
    connection: sqlite3.Connection,
    journal_entry_id: str,
    entry_date: date,
    amount_cents: int,
) -> None:
    _post_entry(
        connection,
        journal_entry_id=journal_entry_id,
        entry_date=entry_date,
        description=f"Cash deposit {journal_entry_id}",
        lines=[
            _line(
                f"{journal_entry_id}-L1",
                journal_entry_id,
                "acct-cash",
                "debit",
                amount_cents,
                1,
                description="Cash received",
            ),
            _line(
                f"{journal_entry_id}-L2",
                journal_entry_id,
                "acct-equity",
                "credit",
                amount_cents,
                2,
                description="Owner equity",
            ),
        ],
    )


def _table_counts(
    connection: sqlite3.Connection,
    table_names: list[str],
) -> dict[str, int]:
    return {
        table_name: connection.execute(
            f"SELECT COUNT(*) FROM {table_name}",
        ).fetchone()[0]
        for table_name in table_names
    }
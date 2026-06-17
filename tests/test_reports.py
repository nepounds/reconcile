from __future__ import annotations

from datetime import date, datetime

import pytest

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.events.store import load_events
from reconcile.exceptions import ValidationError
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import post_journal_entry
from reconcile.projections.rebuild import rebuild_projections
from reconcile.reports.balance_sheet import generate_balance_sheet
from reconcile.reports.income_statement import generate_income_statement
from reconcile.reports.trial_balance import (
    generate_trial_balance,
    trial_balance_totals,
)


def _connection(tmp_path):
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
        closed_at=None,
    )


def _open_standard_accounts(connection):
    accounts = [
        _account("cash", "1000", "Cash", "asset", "debit"),
        _account("loan", "2000", "Loan Payable", "liability", "credit"),
        _account("equity", "3000", "Owner Equity", "equity", "credit"),
        _account("revenue", "4000", "Service Revenue", "revenue", "credit"),
        _account("expense", "5000", "Rent Expense", "expense", "debit"),
    ]
    for account in accounts:
        open_account(connection, account=account)
    return accounts


def _line(
    entry_id: str,
    line_number: int,
    account_id: str,
    side: str,
    amount_cents: int,
) -> JournalLine:
    return JournalLine(
        line_id=f"{entry_id}-line-{line_number}",
        journal_entry_id=entry_id,
        account_id=account_id,
        side=side,
        amount_cents=amount_cents,
        description=None,
        line_number=line_number,
    )


def _post_two_line_entry(
    connection,
    entry_id: str,
    debit_account_id: str,
    credit_account_id: str,
    amount_cents: int,
):
    entry = JournalEntry(
        journal_entry_id=entry_id,
        entry_date=date(2026, 1, 1),
        description=f"Entry {entry_id}",
        lines=[
            _line(entry_id, 1, debit_account_id, "debit", amount_cents),
            _line(entry_id, 2, credit_account_id, "credit", amount_cents),
        ],
        source="manual",
        external_reference=None,
    )
    post_journal_entry(connection, journal_entry=entry)


def _post_two_line_entry_on(
    connection,
    entry_id: str,
    entry_date: date,
    debit_account_id: str,
    credit_account_id: str,
    amount_cents: int,
):
    entry = JournalEntry(
        journal_entry_id=entry_id,
        entry_date=entry_date,
        description=f"Entry {entry_id}",
        lines=[
            _line(entry_id, 1, debit_account_id, "debit", amount_cents),
            _line(entry_id, 2, credit_account_id, "credit", amount_cents),
        ],
        source="manual",
        external_reference=None,
    )
    post_journal_entry(connection, journal_entry=entry)


def _row_by_account(rows, account_id: str):
    return next(row for row in rows if row["account_id"] == account_id)


def _balance_snapshot(connection):
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT
                account_id,
                debit_total_cents,
                credit_total_cents,
                balance_cents,
                updated_at,
                last_event_sequence
            FROM account_balances
            ORDER BY account_id
            """
        ).fetchall()
    ]


def test_empty_database_returns_empty_trial_balance_list(tmp_path):
    connection = _connection(tmp_path)

    assert generate_trial_balance(connection) == []


def test_account_with_no_balance_row_appears_with_zero_values(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account("cash", "1000", "Cash", "asset", "debit"),
    )

    rows = generate_trial_balance(connection)

    assert rows == [
        {
            "account_id": "cash",
            "account_code": "1000",
            "account_name": "Cash",
            "account_type": "asset",
            "normal_balance": "debit",
            "debit_total_cents": 0,
            "credit_total_cents": 0,
            "ending_debit_balance_cents": 0,
            "ending_credit_balance_cents": 0,
        }
    ]


def test_asset_debit_balance_appears_in_ending_debit_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 50_000)

    cash = _row_by_account(generate_trial_balance(connection), "cash")

    assert cash["ending_debit_balance_cents"] == 50_000
    assert cash["ending_credit_balance_cents"] == 0


def test_asset_credit_balance_appears_in_ending_credit_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "equity", "cash", 10_000)

    cash = _row_by_account(generate_trial_balance(connection), "cash")

    assert cash["ending_debit_balance_cents"] == 0
    assert cash["ending_credit_balance_cents"] == 10_000


def test_expense_debit_balance_appears_in_ending_debit_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "expense", "cash", 4_000)

    expense = _row_by_account(generate_trial_balance(connection), "expense")

    assert expense["ending_debit_balance_cents"] == 4_000
    assert expense["ending_credit_balance_cents"] == 0


def test_liability_credit_balance_appears_in_ending_credit_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "loan", 25_000)

    loan = _row_by_account(generate_trial_balance(connection), "loan")

    assert loan["ending_debit_balance_cents"] == 0
    assert loan["ending_credit_balance_cents"] == 25_000


def test_liability_debit_balance_appears_in_ending_debit_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "loan", "cash", 5_000)

    loan = _row_by_account(generate_trial_balance(connection), "loan")

    assert loan["ending_debit_balance_cents"] == 5_000
    assert loan["ending_credit_balance_cents"] == 0


def test_equity_credit_balance_appears_in_ending_credit_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 100_000)

    equity = _row_by_account(generate_trial_balance(connection), "equity")

    assert equity["ending_debit_balance_cents"] == 0
    assert equity["ending_credit_balance_cents"] == 100_000


def test_revenue_credit_balance_appears_in_ending_credit_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "revenue", 100_000)

    revenue = _row_by_account(generate_trial_balance(connection), "revenue")

    assert revenue["ending_debit_balance_cents"] == 0
    assert revenue["ending_credit_balance_cents"] == 100_000


def test_debit_totals_and_credit_totals_are_included(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 50_000)
    _post_two_line_entry(connection, "je-2", "expense", "cash", 5_000)

    cash = _row_by_account(generate_trial_balance(connection), "cash")

    assert cash["debit_total_cents"] == 50_000
    assert cash["credit_total_cents"] == 5_000
    assert cash["ending_debit_balance_cents"] == 45_000


def test_trial_balance_rows_are_sorted_by_account_code(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account("revenue", "4000", "Revenue", "revenue", "credit"),
    )
    open_account(
        connection,
        account=_account("cash", "1000", "Cash", "asset", "debit"),
    )
    open_account(
        connection,
        account=_account("expense", "5000", "Expense", "expense", "debit"),
    )

    rows = generate_trial_balance(connection)

    assert [row["account_code"] for row in rows] == ["1000", "4000", "5000"]


def test_trial_balance_includes_inactive_accounts(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account(
            "old-cash",
            "1099",
            "Old Cash",
            "asset",
            "debit",
            is_active=False,
        ),
    )

    rows = generate_trial_balance(connection)

    assert [row["account_id"] for row in rows] == ["old-cash"]


def test_trial_balance_totals_balance_for_valid_ledger(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 50_000)
    _post_two_line_entry(connection, "je-2", "expense", "cash", 5_000)
    _post_two_line_entry(connection, "je-3", "cash", "revenue", 20_000)

    totals = trial_balance_totals(generate_trial_balance(connection))

    assert totals["total_ending_debit_balance_cents"] == 70_000
    assert totals["total_ending_credit_balance_cents"] == 70_000
    assert totals["is_balanced"] is True


def test_trial_balance_totals_returns_expected_totals():
    rows = [
        {
            "account_id": "cash",
            "account_code": "1000",
            "account_name": "Cash",
            "account_type": "asset",
            "normal_balance": "debit",
            "debit_total_cents": 50_000,
            "credit_total_cents": 5_000,
            "ending_debit_balance_cents": 45_000,
            "ending_credit_balance_cents": 0,
        },
        {
            "account_id": "equity",
            "account_code": "3000",
            "account_name": "Owner Equity",
            "account_type": "equity",
            "normal_balance": "credit",
            "debit_total_cents": 0,
            "credit_total_cents": 50_000,
            "ending_debit_balance_cents": 0,
            "ending_credit_balance_cents": 50_000,
        },
    ]

    assert trial_balance_totals(rows) == {
        "total_debits_cents": 50_000,
        "total_credits_cents": 55_000,
        "total_ending_debit_balance_cents": 45_000,
        "total_ending_credit_balance_cents": 50_000,
        "is_balanced": False,
    }


def test_rebuilt_projections_produce_same_trial_balance_as_incremental(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 50_000)
    _post_two_line_entry(connection, "je-2", "expense", "cash", 5_000)
    incremental_rows = generate_trial_balance(connection)

    rebuild_projections(connection)

    assert generate_trial_balance(connection) == incremental_rows


def test_invalid_normal_balance_in_database_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account("cash", "1000", "Cash", "asset", "debit"),
    )
    connection.execute(
        "UPDATE accounts SET normal_balance = ? WHERE account_id = ?",
        ("sideways", "cash"),
    )
    connection.commit()

    with pytest.raises(ValidationError, match="invalid normal_balance"):
        generate_trial_balance(connection)


def test_invalid_account_type_in_database_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account("cash", "1000", "Cash", "asset", "debit"),
    )
    connection.execute(
        "UPDATE accounts SET account_type = ? WHERE account_id = ?",
        ("banana", "cash"),
    )
    connection.commit()

    with pytest.raises(ValidationError, match="invalid account_type"):
        generate_trial_balance(connection)


def test_invalid_balance_numeric_field_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 50_000)
    connection.execute(
        "UPDATE account_balances SET debit_total_cents = ? WHERE account_id = ?",
        ("bad", "cash"),
    )
    connection.commit()

    with pytest.raises(ValidationError, match="invalid debit_total_cents"):
        generate_trial_balance(connection)


def test_trial_balance_generation_does_not_append_events(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 50_000)
    before_event_count = len(load_events(connection))

    generate_trial_balance(connection)

    assert len(load_events(connection)) == before_event_count


def test_trial_balance_generation_does_not_mutate_account_balances(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 50_000)
    before_balances = _balance_snapshot(connection)

    generate_trial_balance(connection)

    assert _balance_snapshot(connection) == before_balances


def test_empty_database_returns_zero_income_statement_totals(tmp_path):
    connection = _connection(tmp_path)

    report = generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert report == {
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "revenue_accounts": [],
        "expense_accounts": [],
        "total_revenue_cents": 0,
        "total_expenses_cents": 0,
        "net_income_cents": 0,
    }


def test_income_statement_calculates_revenue_expense_and_net_income(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "revenue", 100_000)
    _post_two_line_entry(connection, "je-2", "expense", "cash", 25_000)

    report = generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert report["total_revenue_cents"] == 100_000
    assert report["total_expenses_cents"] == 25_000
    assert report["net_income_cents"] == 75_000
    assert report["revenue_accounts"] == [
        {
            "account_id": "revenue",
            "account_code": "4000",
            "account_name": "Service Revenue",
            "account_type": "revenue",
            "amount_cents": 100_000,
        }
    ]
    assert report["expense_accounts"] == [
        {
            "account_id": "expense",
            "account_code": "5000",
            "account_name": "Rent Expense",
            "account_type": "expense",
            "amount_cents": 25_000,
        }
    ]


def test_income_statement_revenue_debits_reduce_revenue(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "revenue", 100_000)
    _post_two_line_entry(connection, "je-2", "revenue", "cash", 15_000)

    report = generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert report["total_revenue_cents"] == 85_000
    assert report["net_income_cents"] == 85_000


def test_income_statement_expense_credits_reduce_expenses(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "expense", "cash", 40_000)
    _post_two_line_entry(connection, "je-2", "cash", "expense", 5_000)

    report = generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert report["total_expenses_cents"] == 35_000
    assert report["net_income_cents"] == -35_000


def test_income_statement_only_includes_revenue_and_expense_accounts(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 100_000)
    _post_two_line_entry(connection, "je-2", "cash", "revenue", 20_000)
    _post_two_line_entry(connection, "je-3", "expense", "cash", 5_000)

    report = generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    account_ids = {
        row["account_id"]
        for row in report["revenue_accounts"] + report["expense_accounts"]
    }

    assert account_ids == {"revenue", "expense"}


def test_income_statement_date_range_is_inclusive(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry_on(
        connection,
        "before",
        date(2025, 12, 31),
        "cash",
        "revenue",
        10_000,
    )
    _post_two_line_entry_on(
        connection,
        "start",
        date(2026, 1, 1),
        "cash",
        "revenue",
        20_000,
    )
    _post_two_line_entry_on(
        connection,
        "end",
        date(2026, 1, 31),
        "cash",
        "revenue",
        30_000,
    )
    _post_two_line_entry_on(
        connection,
        "after",
        date(2026, 2, 1),
        "cash",
        "revenue",
        40_000,
    )

    report = generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert report["total_revenue_cents"] == 50_000


def test_income_statement_start_date_equal_to_end_date_works(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry_on(
        connection,
        "same-day",
        date(2026, 1, 15),
        "cash",
        "revenue",
        12_000,
    )

    report = generate_income_statement(
        connection,
        start_date=date(2026, 1, 15),
        end_date=date(2026, 1, 15),
    )

    assert report["total_revenue_cents"] == 12_000


def test_income_statement_rejects_invalid_dates(tmp_path):
    connection = _connection(tmp_path)

    with pytest.raises(ValidationError, match="start_date"):
        generate_income_statement(
            connection,
            start_date="2026-01-01",
            end_date=date(2026, 1, 31),
        )

    with pytest.raises(ValidationError, match="end_date"):
        generate_income_statement(
            connection,
            start_date=date(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )

    with pytest.raises(ValidationError, match="start_date"):
        generate_income_statement(
            connection,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 31),
        )


def test_income_statement_rows_are_sorted_by_account_code(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    open_account(
        connection,
        account=_account(
            "other-revenue",
            "4100",
            "Other Revenue",
            "revenue",
            "credit",
        ),
    )
    _post_two_line_entry(connection, "je-1", "cash", "other-revenue", 10_000)
    _post_two_line_entry(connection, "je-2", "cash", "revenue", 20_000)

    report = generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert [row["account_code"] for row in report["revenue_accounts"]] == [
        "4000",
        "4100",
    ]


def test_invalid_journal_line_side_raises_income_statement_error(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "revenue", 20_000)
    connection.execute("PRAGMA ignore_check_constraints = ON")
    connection.execute(
        "UPDATE journal_entry_lines SET side = ? WHERE account_id = ?",
        ("sideways", "revenue"),
    )
    connection.commit()

    with pytest.raises(ValidationError, match="journal line side"):
        generate_income_statement(
            connection,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )


def test_income_statement_generation_does_not_append_events(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "revenue", 20_000)
    before_event_count = len(load_events(connection))

    generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert len(load_events(connection)) == before_event_count


def test_income_statement_generation_does_not_mutate_account_balances(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "revenue", 20_000)
    before_balances = _balance_snapshot(connection)

    generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert _balance_snapshot(connection) == before_balances


def test_empty_database_returns_zero_balance_sheet(tmp_path):
    connection = _connection(tmp_path)

    report = generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    assert report == {
        "as_of_date": "2026-01-31",
        "asset_accounts": [],
        "liability_accounts": [],
        "equity_accounts": [],
        "current_period_net_income_cents": 0,
        "total_assets_cents": 0,
        "total_liabilities_cents": 0,
        "total_equity_cents": 0,
        "total_liabilities_and_equity_cents": 0,
        "is_balanced": True,
    }


def test_balance_sheet_calculates_assets_liabilities_equity_and_income(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 100_000)
    _post_two_line_entry(connection, "je-2", "cash", "loan", 25_000)
    _post_two_line_entry(connection, "je-3", "cash", "revenue", 20_000)
    _post_two_line_entry(connection, "je-4", "expense", "cash", 5_000)

    report = generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    assert report["total_assets_cents"] == 140_000
    assert report["total_liabilities_cents"] == 25_000
    assert report["current_period_net_income_cents"] == 15_000
    assert report["total_equity_cents"] == 115_000
    assert report["total_liabilities_and_equity_cents"] == 140_000
    assert report["is_balanced"] is True


def test_balance_sheet_asset_credit_decreases_total_assets(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 100_000)
    _post_two_line_entry(connection, "je-2", "equity", "cash", 10_000)

    report = generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    assert report["total_assets_cents"] == 90_000
    assert report["total_equity_cents"] == 90_000
    assert report["is_balanced"] is True


def test_balance_sheet_liability_debit_decreases_liabilities(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "loan", 50_000)
    _post_two_line_entry(connection, "je-2", "loan", "cash", 15_000)

    report = generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    assert report["total_assets_cents"] == 35_000
    assert report["total_liabilities_cents"] == 35_000
    assert report["is_balanced"] is True


def test_balance_sheet_equity_debit_decreases_equity(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 80_000)
    _post_two_line_entry(connection, "je-2", "equity", "cash", 30_000)

    report = generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    assert report["total_assets_cents"] == 50_000
    assert report["total_equity_cents"] == 50_000
    assert report["is_balanced"] is True


def test_balance_sheet_as_of_date_excludes_later_entries(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry_on(
        connection,
        "included",
        date(2026, 1, 31),
        "cash",
        "equity",
        50_000,
    )
    _post_two_line_entry_on(
        connection,
        "excluded",
        date(2026, 2, 1),
        "cash",
        "equity",
        25_000,
    )

    report = generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    assert report["total_assets_cents"] == 50_000
    assert report["total_equity_cents"] == 50_000


def test_balance_sheet_rejects_invalid_as_of_date(tmp_path):
    connection = _connection(tmp_path)

    with pytest.raises(ValidationError, match="as_of_date"):
        generate_balance_sheet(connection, as_of_date="2026-01-31")

    with pytest.raises(ValidationError, match="as_of_date"):
        generate_balance_sheet(connection, as_of_date=datetime(2026, 1, 31))


def test_balance_sheet_rows_are_sorted_by_account_code(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account("asset-2", "1200", "Second Asset", "asset", "debit"),
    )
    open_account(
        connection,
        account=_account("asset-1", "1000", "First Asset", "asset", "debit"),
    )

    report = generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    assert [row["account_code"] for row in report["asset_accounts"]] == [
        "1000",
        "1200",
    ]


def test_balance_sheet_includes_inactive_balance_sheet_accounts(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account(
            "old-cash",
            "1099",
            "Old Cash",
            "asset",
            "debit",
            is_active=False,
        ),
    )

    report = generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    assert report["asset_accounts"] == [
        {
            "account_id": "old-cash",
            "account_code": "1099",
            "account_name": "Old Cash",
            "account_type": "asset",
            "balance_cents": 0,
        }
    ]


def test_balance_sheet_excludes_revenue_and_expense_account_sections(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "revenue", 20_000)
    _post_two_line_entry(connection, "je-2", "expense", "cash", 5_000)

    report = generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    section_account_ids = {
        row["account_id"]
        for row in (
            report["asset_accounts"]
            + report["liability_accounts"]
            + report["equity_accounts"]
        )
    }

    assert "revenue" not in section_account_ids
    assert "expense" not in section_account_ids
    assert report["current_period_net_income_cents"] == 15_000


def test_invalid_normal_balance_raises_balance_sheet_error(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account("cash", "1000", "Cash", "asset", "debit"),
    )
    connection.execute(
        "UPDATE accounts SET normal_balance = ? WHERE account_id = ?",
        ("sideways", "cash"),
    )
    connection.commit()

    with pytest.raises(ValidationError, match="normal_balance must be one of"):
        generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))


def test_invalid_account_type_raises_balance_sheet_error(tmp_path):
    connection = _connection(tmp_path)
    open_account(
        connection,
        account=_account("cash", "1000", "Cash", "asset", "debit"),
    )
    connection.execute(
        "UPDATE accounts SET account_type = ? WHERE account_id = ?",
        ("banana", "cash"),
    )
    connection.commit()

    with pytest.raises(ValidationError, match="account_type must be one of"):
        generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))


def test_invalid_journal_line_side_raises_balance_sheet_error(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 20_000)
    connection.execute("PRAGMA ignore_check_constraints = ON")
    connection.execute(
        "UPDATE journal_entry_lines SET side = ? WHERE account_id = ?",
        ("sideways", "cash"),
    )
    connection.commit()

    with pytest.raises(ValidationError, match="journal line side"):
        generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))


def test_balance_sheet_generation_does_not_append_events(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 20_000)
    before_event_count = len(load_events(connection))

    generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    assert len(load_events(connection)) == before_event_count


def test_balance_sheet_generation_does_not_mutate_account_balances(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 20_000)
    before_balances = _balance_snapshot(connection)

    generate_balance_sheet(connection, as_of_date=date(2026, 1, 31))

    assert _balance_snapshot(connection) == before_balances


def test_rebuilt_projections_produce_same_step_12_reports_as_incremental(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    _post_two_line_entry(connection, "je-1", "cash", "equity", 100_000)
    _post_two_line_entry(connection, "je-2", "cash", "revenue", 20_000)
    _post_two_line_entry(connection, "je-3", "expense", "cash", 5_000)

    income_statement_before = generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    balance_sheet_before = generate_balance_sheet(
        connection,
        as_of_date=date(2026, 1, 31),
    )

    rebuild_projections(connection)

    assert generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    ) == income_statement_before
    assert generate_balance_sheet(
        connection,
        as_of_date=date(2026, 1, 31),
    ) == balance_sheet_before

from __future__ import annotations

import json
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
from reconcile.journal.service import post_journal_entry
from reconcile.reports.cash_flow import (
    cash_flow_totals,
    classify_cash_flow_section,
    generate_cash_flow_statement,
)

ACCOUNT_DEFINITIONS = [
    ("acct-cash", "1000", "Cash", "asset", "debit"),
    ("acct-checking", "1010", "Operating Checking", "asset", "debit"),
    ("acct-ar", "1100", "Accounts Receivable", "asset", "debit"),
    ("acct-equipment", "1500", "Equipment", "asset", "debit"),
    ("acct-ap", "2000", "Accounts Payable", "liability", "credit"),
    ("acct-loan", "2100", "Bank Loan", "liability", "credit"),
    ("acct-equity", "3000", "Owner Equity", "equity", "credit"),
    ("acct-revenue", "4000", "Service Revenue", "revenue", "credit"),
    ("acct-software", "5100", "Software Expense", "expense", "debit"),
]


def _connection(tmp_path: Path) -> sqlite3.Connection:
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)
    for account_id, code, name, account_type, normal_balance in ACCOUNT_DEFINITIONS:
        open_account(
            connection,
            account=Account(
                account_id=account_id,
                code=code,
                name=name,
                account_type=account_type,
                normal_balance=normal_balance,
                is_active=True,
                opened_at="2026-01-01T00:00:00+00:00",
                closed_at=None,
            ),
        )
    return connection


def _post(
    connection: sqlite3.Connection,
    entry_id: str,
    entry_date: date,
    description: str,
    lines: list[tuple[str, str, int]],
) -> None:
    journal_lines = [
        JournalLine(
            line_id=f"{entry_id}-line-{index}",
            journal_entry_id=entry_id,
            account_id=account_id,
            side=side,
            amount_cents=amount_cents,
            description=None,
            line_number=index,
        )
        for index, (account_id, side, amount_cents) in enumerate(lines, start=1)
    ]
    post_journal_entry(
        connection,
        journal_entry=JournalEntry(
            journal_entry_id=entry_id,
            entry_date=entry_date,
            description=description,
            lines=journal_lines,
            source="test",
            external_reference=None,
        ),
    )


def _statement(connection: sqlite3.Connection) -> dict[str, object]:
    return generate_cash_flow_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )


def _all_rows(statement: dict[str, object]) -> list[dict[str, object]]:
    sections = statement["sections"]
    assert isinstance(sections, dict)
    rows: list[dict[str, object]] = []
    for section in ("operating", "investing", "financing"):
        section_rows = sections[section]
        assert isinstance(section_rows, list)
        rows.extend(section_rows)
    return rows


def test_classifies_revenue_counterparty_as_operating() -> None:
    assert classify_cash_flow_section("revenue") == "operating"


def test_classifies_expense_counterparty_as_operating() -> None:
    assert classify_cash_flow_section("expense") == "operating"


def test_classifies_non_cash_asset_counterparty_as_investing() -> None:
    assert classify_cash_flow_section("asset") == "investing"


def test_classifies_accounts_receivable_counterparty_as_operating() -> None:
    assert (
        classify_cash_flow_section(
            "asset",
            counterparty_account_code="1100",
            counterparty_account_name="Accounts Receivable",
        )
        == "operating"
    )


def test_classifies_accounts_payable_counterparty_as_operating() -> None:
    assert (
        classify_cash_flow_section(
            "liability",
            counterparty_account_code="2000",
            counterparty_account_name="Accounts Payable",
        )
        == "operating"
    )


def test_classifies_liability_counterparty_as_financing() -> None:
    assert classify_cash_flow_section("liability") == "financing"


def test_classifies_equity_counterparty_as_financing() -> None:
    assert classify_cash_flow_section("equity") == "financing"


def test_invalid_account_type_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        classify_cash_flow_section("contra-income-whatever")


def test_empty_ledger_returns_zero_totals_and_ties(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["beginning_cash_cents"] == 0
    assert totals["ending_cash_cents"] == 0
    assert totals["net_cash_change_cents"] == 0
    assert totals["cash_balances_tie"] is True
    assert _all_rows(statement) == []


def test_owner_contribution_is_financing_inflow(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 1),
            "Owner contribution",
            [("acct-cash", "debit", 500_000), ("acct-equity", "credit", 500_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["financing_cash_flow_cents"] == 500_000
    assert totals["net_cash_change_cents"] == 500_000
    assert totals["ending_cash_cents"] == 500_000


def test_software_expense_paid_from_cash_is_operating_outflow(
    tmp_path: Path,
) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 5),
            "Software subscription",
            [("acct-software", "debit", 5_000), ("acct-cash", "credit", 5_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["operating_cash_flow_cents"] == -5_000
    assert totals["net_cash_change_cents"] == -5_000
    assert totals["ending_cash_cents"] == -5_000


def test_service_revenue_received_in_cash_is_operating_inflow(
    tmp_path: Path,
) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 10),
            "Cash service revenue",
            [("acct-cash", "debit", 20_000), ("acct-revenue", "credit", 20_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["operating_cash_flow_cents"] == 20_000
    assert totals["net_cash_change_cents"] == 20_000


def test_accounts_receivable_collection_is_operating_inflow(
    tmp_path: Path,
) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 10),
            "Collect customer receivable",
            [("acct-cash", "debit", 25_000), ("acct-ar", "credit", 25_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["operating_cash_flow_cents"] == 25_000
    assert totals["investing_cash_flow_cents"] == 0
    assert totals["net_cash_change_cents"] == 25_000


def test_accounts_payable_payment_is_operating_outflow(
    tmp_path: Path,
) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 12),
            "Pay vendor payable",
            [("acct-ap", "debit", 12_000), ("acct-cash", "credit", 12_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["operating_cash_flow_cents"] == -12_000
    assert totals["financing_cash_flow_cents"] == 0
    assert totals["net_cash_change_cents"] == -12_000


def test_equipment_purchase_with_cash_is_investing_outflow(
    tmp_path: Path,
) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 12),
            "Equipment purchase",
            [("acct-equipment", "debit", 120_000), ("acct-cash", "credit", 120_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["investing_cash_flow_cents"] == -120_000
    assert totals["net_cash_change_cents"] == -120_000


def test_loan_proceeds_received_in_cash_are_financing_inflow(
    tmp_path: Path,
) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 15),
            "Loan proceeds",
            [("acct-cash", "debit", 250_000), ("acct-loan", "credit", 250_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["financing_cash_flow_cents"] == 250_000


def test_loan_repayment_principal_is_financing_outflow(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 16),
            "Loan repayment",
            [("acct-loan", "debit", 10_000), ("acct-cash", "credit", 10_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["financing_cash_flow_cents"] == -10_000


def test_multiple_entries_total_correctly(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 1),
            "Owner contribution",
            [("acct-cash", "debit", 500_000), ("acct-equity", "credit", 500_000)],
        )
        _post(
            connection,
            "JE-002",
            date(2026, 1, 5),
            "Software",
            [("acct-software", "debit", 5_000), ("acct-cash", "credit", 5_000)],
        )
        _post(
            connection,
            "JE-003",
            date(2026, 1, 10),
            "Revenue",
            [("acct-cash", "debit", 20_000), ("acct-revenue", "credit", 20_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["operating_cash_flow_cents"] == 15_000
    assert totals["financing_cash_flow_cents"] == 500_000
    assert totals["net_cash_change_cents"] == 515_000
    assert totals["ending_cash_cents"] == 515_000
    assert totals["cash_balances_tie"] is True


def test_date_filtering_includes_start_date(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 1),
            "Start date contribution",
            [("acct-cash", "debit", 10_000), ("acct-equity", "credit", 10_000)],
        )
        statement = generate_cash_flow_statement(
            connection,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
        )

    assert cash_flow_totals(statement)["net_cash_change_cents"] == 10_000


def test_date_filtering_includes_end_date(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 31),
            "End date contribution",
            [("acct-cash", "debit", 10_000), ("acct-equity", "credit", 10_000)],
        )
        statement = generate_cash_flow_statement(
            connection,
            start_date=date(2026, 1, 31),
            end_date=date(2026, 1, 31),
        )

    assert cash_flow_totals(statement)["net_cash_change_cents"] == 10_000


def test_entries_before_start_affect_beginning_cash_only(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2025, 12, 31),
            "Prior contribution",
            [("acct-cash", "debit", 100_000), ("acct-equity", "credit", 100_000)],
        )
        _post(
            connection,
            "JE-002",
            date(2026, 1, 5),
            "Software",
            [("acct-software", "debit", 5_000), ("acct-cash", "credit", 5_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["beginning_cash_cents"] == 100_000
    assert totals["net_cash_change_cents"] == -5_000
    assert totals["ending_cash_cents"] == 95_000
    assert len(_all_rows(statement)) == 1


def test_entries_after_end_do_not_affect_period_or_ending_cash(
    tmp_path: Path,
) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 31),
            "January contribution",
            [("acct-cash", "debit", 100_000), ("acct-equity", "credit", 100_000)],
        )
        _post(
            connection,
            "JE-002",
            date(2026, 2, 1),
            "February contribution",
            [("acct-cash", "debit", 50_000), ("acct-equity", "credit", 50_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["net_cash_change_cents"] == 100_000
    assert totals["ending_cash_cents"] == 100_000
    assert len(_all_rows(statement)) == 1


def test_beginning_cash_plus_net_change_equals_ending_cash(
    tmp_path: Path,
) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2025, 12, 31),
            "Prior contribution",
            [("acct-cash", "debit", 100_000), ("acct-equity", "credit", 100_000)],
        )
        _post(
            connection,
            "JE-002",
            date(2026, 1, 5),
            "Revenue",
            [("acct-cash", "debit", 20_000), ("acct-revenue", "credit", 20_000)],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["beginning_cash_cents"] + totals["net_cash_change_cents"] == totals[
        "ending_cash_cents"
    ]
    assert totals["cash_balances_tie"] is True


def test_cash_transfer_between_cash_like_accounts_is_excluded(
    tmp_path: Path,
) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 8),
            "Cash transfer",
            [
                ("acct-checking", "debit", 20_000),
                ("acct-cash", "credit", 20_000),
            ],
        )
        statement = _statement(connection)

    totals = cash_flow_totals(statement)
    assert totals["net_cash_change_cents"] == 0
    assert totals["ending_cash_cents"] == 0
    assert _all_rows(statement) == []


def test_selected_cash_account_filters_to_one_cash_account(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 8),
            "Cash transfer",
            [
                ("acct-checking", "debit", 20_000),
                ("acct-cash", "credit", 20_000),
            ],
        )
        statement = generate_cash_flow_statement(
            connection,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            cash_account_id="acct-cash",
        )

    totals = cash_flow_totals(statement)
    assert statement["cash_account_ids"] == ["acct-cash"]
    assert totals["net_cash_change_cents"] == 0
    assert totals["ending_cash_cents"] == -20_000


def test_invalid_cash_account_id_raises_validation_error(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        with pytest.raises(ValidationError):
            generate_cash_flow_statement(
                connection,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                cash_account_id="missing-cash",
            )


def test_non_cash_selected_account_raises_validation_error(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        with pytest.raises(ValidationError):
            generate_cash_flow_statement(
                connection,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                cash_account_id="acct-equipment",
            )


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        ("2026-01-01", date(2026, 1, 31)),
        (date(2026, 1, 1), "2026-01-31"),
    ],
)
def test_invalid_date_arguments_raise_validation_error(
    tmp_path: Path,
    start_date: object,
    end_date: object,
) -> None:
    with _connection(tmp_path) as connection:
        with pytest.raises(ValidationError):
            generate_cash_flow_statement(
                connection,
                start_date=start_date,  # type: ignore[arg-type]
                end_date=end_date,  # type: ignore[arg-type]
            )


def test_datetime_date_arguments_raise_validation_error(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        with pytest.raises(ValidationError):
            generate_cash_flow_statement(
                connection,
                start_date=datetime(2026, 1, 1),
                end_date=date(2026, 1, 31),
            )


def test_start_date_after_end_date_raises_validation_error(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        with pytest.raises(ValidationError):
            generate_cash_flow_statement(
                connection,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 1, 31),
            )


def test_generation_does_not_append_events(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 1),
            "Owner contribution",
            [("acct-cash", "debit", 10_000), ("acct-equity", "credit", 10_000)],
        )
        before = len(load_events(connection))
        _statement(connection)
        after = len(load_events(connection))

    assert before == after


def test_generation_does_not_mutate_account_balances(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 1),
            "Owner contribution",
            [("acct-cash", "debit", 10_000), ("acct-equity", "credit", 10_000)],
        )
        before = connection.execute(
            "SELECT * FROM account_balances ORDER BY account_id"
        ).fetchall()
        _statement(connection)
        after = connection.execute(
            "SELECT * FROM account_balances ORDER BY account_id"
        ).fetchall()

    assert [tuple(row) for row in before] == [tuple(row) for row in after]


def test_generation_does_not_mutate_journal_entries_or_lines(
    tmp_path: Path,
) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 1),
            "Owner contribution",
            [("acct-cash", "debit", 10_000), ("acct-equity", "credit", 10_000)],
        )
        before_entries = connection.execute(
            "SELECT * FROM journal_entries ORDER BY journal_entry_id"
        ).fetchall()
        before_lines = connection.execute(
            "SELECT * FROM journal_entry_lines ORDER BY line_id"
        ).fetchall()
        _statement(connection)
        after_entries = connection.execute(
            "SELECT * FROM journal_entries ORDER BY journal_entry_id"
        ).fetchall()
        after_lines = connection.execute(
            "SELECT * FROM journal_entry_lines ORDER BY line_id"
        ).fetchall()

    before_entry_tuples = [tuple(row) for row in before_entries]
    after_entry_tuples = [tuple(row) for row in after_entries]
    before_line_tuples = [tuple(row) for row in before_lines]
    after_line_tuples = [tuple(row) for row in after_lines]

    assert before_entry_tuples == after_entry_tuples
    assert before_line_tuples == after_line_tuples


def test_generation_does_not_mutate_bank_transactions(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
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
            ("import-1", "test", "bank.csv", None, "2026-01-01T00:00:00", 1),
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
                "Deposit",
                "deposit",
                10_000,
                None,
                None,
                "hash-1",
                None,
                "2026-01-01T00:00:00",
            ),
        )
        before = connection.execute(
            "SELECT * FROM bank_transactions ORDER BY bank_transaction_id"
        ).fetchall()
        _statement(connection)
        after = connection.execute(
            "SELECT * FROM bank_transactions ORDER BY bank_transaction_id"
        ).fetchall()

    assert [tuple(row) for row in before] == [tuple(row) for row in after]


def test_report_output_is_json_serializable(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 1),
            "Owner contribution",
            [("acct-cash", "debit", 10_000), ("acct-equity", "credit", 10_000)],
        )
        statement = _statement(connection)

    json.dumps(statement)


def test_cash_flow_totals_returns_expected_totals(tmp_path: Path) -> None:
    with _connection(tmp_path) as connection:
        _post(
            connection,
            "JE-001",
            date(2026, 1, 1),
            "Owner contribution",
            [("acct-cash", "debit", 10_000), ("acct-equity", "credit", 10_000)],
        )
        statement = _statement(connection)

    assert cash_flow_totals(statement) == statement["totals"]


def test_cash_flow_totals_malformed_statement_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        cash_flow_totals({"sections": [], "totals": {}})

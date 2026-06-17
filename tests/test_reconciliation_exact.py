"""Tests for exact amount/date reconciliation matching."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime

import pytest

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.exceptions import ValidationError
from reconcile.imports.bank_csv import import_bank_statement_csv
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import post_journal_entry
from reconcile.reconciliation.cash_movements import extract_ledger_cash_movements
from reconcile.reconciliation.matcher import (
    get_reconciliation_run,
    list_reconciliation_matches,
    run_exact_reconciliation,
)


def _connection(tmp_path):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)
    return connection


def _account(account_id, code, name, account_type, normal_balance):
    return Account(
        account_id=account_id,
        code=code,
        name=name,
        account_type=account_type,
        normal_balance=normal_balance,
        is_active=True,
        opened_at="2026-01-01T00:00:00+00:00",
    )


def _seed_accounts(connection):
    open_account(
        connection,
        account=_account("cash", "1000", "Cash", "asset", "debit"),
    )
    open_account(
        connection,
        account=_account("equity", "3000", "Owner Equity", "equity", "credit"),
    )
    open_account(
        connection,
        account=_account("expense", "5000", "Expense", "expense", "debit"),
    )
    return "cash"


def _post_deposit(
    connection,
    *,
    entry_id="je-deposit",
    entry_date=date(2026, 1, 3),
    amount=10000,
):
    post_journal_entry(
        connection,
        journal_entry=JournalEntry(
            journal_entry_id=entry_id,
            entry_date=entry_date,
            description="Owner contribution",
            source="test",
            lines=[
                JournalLine(
                    line_id=f"{entry_id}-line-1",
                    journal_entry_id=entry_id,
                    account_id="cash",
                    side="debit",
                    amount_cents=amount,
                    line_number=1,
                    description="Cash received",
                ),
                JournalLine(
                    line_id=f"{entry_id}-line-2",
                    journal_entry_id=entry_id,
                    account_id="equity",
                    side="credit",
                    amount_cents=amount,
                    line_number=2,
                    description="Owner equity",
                ),
            ],
        ),
    )


def _post_withdrawal(
    connection,
    *,
    entry_id="je-withdrawal",
    entry_date=date(2026, 1, 4),
    amount=2500,
):
    post_journal_entry(
        connection,
        journal_entry=JournalEntry(
            journal_entry_id=entry_id,
            entry_date=entry_date,
            description="Cash payment",
            source="test",
            lines=[
                JournalLine(
                    line_id=f"{entry_id}-line-1",
                    journal_entry_id=entry_id,
                    account_id="expense",
                    side="debit",
                    amount_cents=amount,
                    line_number=1,
                    description="Expense",
                ),
                JournalLine(
                    line_id=f"{entry_id}-line-2",
                    journal_entry_id=entry_id,
                    account_id="cash",
                    side="credit",
                    amount_cents=amount,
                    line_number=2,
                    description="Cash paid",
                ),
            ],
        ),
    )


def _import_bank_rows(tmp_path, connection, rows, *, import_id="import-1"):
    path = tmp_path / f"{import_id}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "transaction_date",
                "posted_date",
                "description",
                "amount",
                "external_id",
                "check_number",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return import_bank_statement_csv(
        connection,
        path,
        source_name="test-bank",
        import_id=import_id,
    )


def _ledger_link_count(connection):
    return connection.execute(
        "SELECT COUNT(*) AS count FROM reconciliation_match_ledger_links"
    ).fetchone()["count"]


def test_exact_reconciliation_creates_run_summary_and_config(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    _post_deposit(connection)
    _import_bank_rows(
        tmp_path,
        connection,
        [
            {
                "transaction_date": "2026-01-03",
                "posted_date": "2026-01-03",
                "description": "DEPOSIT",
                "amount": "100.00",
                "external_id": "bank-1",
                "check_number": "",
            }
        ],
    )

    summary = run_exact_reconciliation(
        connection,
        cash_account_id=cash_account_id,
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="run-1",
        started_at="2026-02-01T00:00:00+00:00",
    )

    run = get_reconciliation_run(connection, "run-1")
    assert summary["reconciliation_run_id"] == "run-1"
    assert summary["status"] == "completed"
    assert summary["auto_matched_count"] == 1
    assert summary["candidate_count"] == 0
    assert summary["unmatched_count"] == 0
    assert summary["total_bank_transactions"] == 1
    assert summary["total_matches"] == 1
    assert run["cash_account_id"] == cash_account_id
    assert run["statement_start_date"] == "2026-01-01"
    assert run["statement_end_date"] == "2026-01-31"
    assert run["status"] == "completed"
    assert json.loads(run["config_json"])["algorithm"] == "exact_amount_date"


def test_generated_reconciliation_run_id_is_nonblank(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    summary = run_exact_reconciliation(
        connection,
        cash_account_id=cash_account_id,
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
    )
    assert summary["reconciliation_run_id"].startswith("recon-run-")


def test_duplicate_reconciliation_run_id_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    kwargs = {
        "cash_account_id": cash_account_id,
        "statement_start_date": date(2026, 1, 1),
        "statement_end_date": date(2026, 1, 31),
        "reconciliation_run_id": "run-1",
    }
    run_exact_reconciliation(connection, **kwargs)
    with pytest.raises(ValidationError, match="reconciliation_run_id"):
        run_exact_reconciliation(connection, **kwargs)


def test_positive_deposit_and_negative_withdrawal_exact_match(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    _post_deposit(
        connection,
        entry_id="je-dep",
        entry_date=date(2026, 1, 3),
        amount=10000,
    )
    _post_withdrawal(
        connection,
        entry_id="je-wd",
        entry_date=date(2026, 1, 4),
        amount=2500,
    )
    _import_bank_rows(
        tmp_path,
        connection,
        [
            {
                "transaction_date": "2026-01-03",
                "posted_date": "2026-01-03",
                "description": "DEPOSIT",
                "amount": "100.00",
                "external_id": "bank-1",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-04",
                "posted_date": "2026-01-04",
                "description": "PAYMENT",
                "amount": "-25.00",
                "external_id": "bank-2",
                "check_number": "",
            },
        ],
    )

    summary = run_exact_reconciliation(
        connection,
        cash_account_id=cash_account_id,
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="run-1",
    )
    matches = list_reconciliation_matches(connection, "run-1")

    assert summary["auto_matched_count"] == 2
    assert {match["match_type"] for match in matches} == {"exact"}
    assert {match["status"] for match in matches} == {"auto_matched"}
    assert {match["score"] for match in matches} == {100.0}
    assert {match["amount_delta_cents"] for match in matches} == {0}
    assert {match["date_delta_days"] for match in matches} == {0}
    assert _ledger_link_count(connection) == 2


def test_exact_match_explanation_and_ledger_link_are_stored(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    _post_deposit(
        connection,
        entry_id="je-dep",
        entry_date=date(2026, 1, 3),
        amount=10000,
    )
    _import_bank_rows(
        tmp_path,
        connection,
        [
            {
                "transaction_date": "2026-01-03",
                "posted_date": "2026-01-03",
                "description": "DEPOSIT",
                "amount": "100.00",
                "external_id": "bank-1",
                "check_number": "",
            }
        ],
    )

    movements = extract_ledger_cash_movements(
        connection,
        cash_account_id=cash_account_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    run_exact_reconciliation(
        connection,
        cash_account_id=cash_account_id,
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="run-1",
    )
    match = list_reconciliation_matches(connection, "run-1")[0]
    explanation = json.loads(match["explanation_json"])
    link = connection.execute(
        "SELECT * FROM reconciliation_match_ledger_links"
    ).fetchone()

    assert explanation["reason"] == "amount_and_date_matched_exactly"
    assert explanation["amount_cents"] == 10000
    assert explanation["transaction_date"] == "2026-01-03"
    assert explanation["entry_date"] == "2026-01-03"
    assert link["journal_entry_id"] == movements[0]["journal_entry_id"]
    assert link["amount_cents"] == 10000


def test_amount_or_date_mismatch_is_unmatched(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    _post_deposit(
        connection,
        entry_id="je-dep",
        entry_date=date(2026, 1, 3),
        amount=10000,
    )
    _import_bank_rows(
        tmp_path,
        connection,
        [
            {
                "transaction_date": "2026-01-03",
                "posted_date": "2026-01-03",
                "description": "WRONG AMOUNT",
                "amount": "101.00",
                "external_id": "bank-1",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-04",
                "posted_date": "2026-01-04",
                "description": "WRONG DATE",
                "amount": "100.00",
                "external_id": "bank-2",
                "check_number": "",
            },
        ],
    )

    summary = run_exact_reconciliation(
        connection,
        cash_account_id=cash_account_id,
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="run-1",
    )
    matches = list_reconciliation_matches(connection, "run-1")

    assert summary["auto_matched_count"] == 0
    assert summary["unmatched_count"] == 2
    assert {match["match_type"] for match in matches} == {"unmatched"}
    assert {match["status"] for match in matches} == {"unmatched"}
    assert {match["score"] for match in matches} == {0.0}
    assert _ledger_link_count(connection) == 0
    assert all(
        json.loads(match["explanation_json"])["reason"]
        == "no_exact_ledger_cash_movement_matched"
        for match in matches
    )


def test_ledger_movement_is_not_reused_across_auto_matches(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    _post_deposit(
        connection,
        entry_id="je-dep",
        entry_date=date(2026, 1, 3),
        amount=10000,
    )
    _import_bank_rows(
        tmp_path,
        connection,
        [
            {
                "transaction_date": "2026-01-03",
                "posted_date": "2026-01-03",
                "description": "DEPOSIT A",
                "amount": "100.00",
                "external_id": "bank-1",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-03",
                "posted_date": "2026-01-03",
                "description": "DEPOSIT B",
                "amount": "100.00",
                "external_id": "bank-2",
                "check_number": "",
            },
        ],
    )

    summary = run_exact_reconciliation(
        connection,
        cash_account_id=cash_account_id,
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="run-1",
    )

    assert summary["auto_matched_count"] == 1
    assert summary["candidate_count"] == 1
    assert _ledger_link_count(connection) == 1


def test_multiple_exact_ledger_candidates_are_not_auto_matched(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    _post_deposit(
        connection,
        entry_id="je-dep-1",
        entry_date=date(2026, 1, 3),
        amount=10000,
    )
    _post_deposit(
        connection,
        entry_id="je-dep-2",
        entry_date=date(2026, 1, 3),
        amount=10000,
    )
    _import_bank_rows(
        tmp_path,
        connection,
        [
            {
                "transaction_date": "2026-01-03",
                "posted_date": "2026-01-03",
                "description": "DEPOSIT",
                "amount": "100.00",
                "external_id": "bank-1",
                "check_number": "",
            }
        ],
    )

    summary = run_exact_reconciliation(
        connection,
        cash_account_id=cash_account_id,
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="run-1",
    )
    match = list_reconciliation_matches(connection, "run-1")[0]

    assert summary["auto_matched_count"] == 0
    assert summary["candidate_count"] == 1
    assert match["status"] == "candidate"
    assert json.loads(match["explanation_json"])["reason"] == (
        "multiple_exact_ledger_cash_movements_matched"
    )
    assert _ledger_link_count(connection) == 0


def test_duplicate_flagged_bank_transactions_are_not_auto_matched(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    _post_deposit(
        connection,
        entry_id="je-dep",
        entry_date=date(2026, 1, 3),
        amount=10000,
    )
    _import_bank_rows(
        tmp_path,
        connection,
        [
            {
                "transaction_date": "2026-01-03",
                "posted_date": "2026-01-03",
                "description": "DEPOSIT",
                "amount": "100.00",
                "external_id": "same-id",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-03",
                "posted_date": "2026-01-03",
                "description": "DEPOSIT",
                "amount": "100.00",
                "external_id": "same-id",
                "check_number": "",
            },
        ],
    )

    summary = run_exact_reconciliation(
        connection,
        cash_account_id=cash_account_id,
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="run-1",
    )

    assert summary["auto_matched_count"] == 0
    assert summary["candidate_count"] == 2
    assert _ledger_link_count(connection) == 0


def test_statement_date_range_filters_bank_and_ledger_rows(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    _post_deposit(
        connection,
        entry_id="before",
        entry_date=date(2025, 12, 31),
        amount=1000,
    )
    _post_deposit(
        connection,
        entry_id="start",
        entry_date=date(2026, 1, 1),
        amount=2000,
    )
    _post_deposit(
        connection,
        entry_id="end",
        entry_date=date(2026, 1, 31),
        amount=3000,
    )
    _post_deposit(
        connection,
        entry_id="after",
        entry_date=date(2026, 2, 1),
        amount=4000,
    )
    _import_bank_rows(
        tmp_path,
        connection,
        [
            {
                "transaction_date": "2025-12-31",
                "posted_date": "2025-12-31",
                "description": "BEFORE",
                "amount": "10.00",
                "external_id": "b",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-01",
                "posted_date": "2026-01-01",
                "description": "START",
                "amount": "20.00",
                "external_id": "s",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-31",
                "posted_date": "2026-01-31",
                "description": "END",
                "amount": "30.00",
                "external_id": "e",
                "check_number": "",
            },
            {
                "transaction_date": "2026-02-01",
                "posted_date": "2026-02-01",
                "description": "AFTER",
                "amount": "40.00",
                "external_id": "a",
                "check_number": "",
            },
        ],
    )

    summary = run_exact_reconciliation(
        connection,
        cash_account_id=cash_account_id,
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="run-1",
    )

    assert summary["total_bank_transactions"] == 2
    assert summary["auto_matched_count"] == 2


def test_invalid_date_inputs_raise_validation_error(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)

    with pytest.raises(ValidationError):
        run_exact_reconciliation(
            connection,
            cash_account_id=cash_account_id,
            statement_start_date=date(2026, 2, 1),
            statement_end_date=date(2026, 1, 1),
        )
    with pytest.raises(ValidationError):
        run_exact_reconciliation(
            connection,
            cash_account_id=cash_account_id,
            statement_start_date="2026-01-01",
            statement_end_date=date(2026, 1, 31),
        )
    with pytest.raises(ValidationError):
        run_exact_reconciliation(
            connection,
            cash_account_id=cash_account_id,
            statement_start_date=datetime(2026, 1, 1),
            statement_end_date=date(2026, 1, 31),
        )


def test_reconciliation_does_not_mutate_non_reconciliation_tables(tmp_path):
    connection = _connection(tmp_path)
    cash_account_id = _seed_accounts(connection)
    _post_deposit(
        connection,
        entry_id="je-dep",
        entry_date=date(2026, 1, 3),
        amount=10000,
    )
    _import_bank_rows(
        tmp_path,
        connection,
        [
            {
                "transaction_date": "2026-01-03",
                "posted_date": "2026-01-03",
                "description": "DEPOSIT",
                "amount": "100.00",
                "external_id": "bank-1",
                "check_number": "",
            }
        ],
    )
    before = {
        table: connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()[
            "count"
        ]
        for table in (
            "ledger_events",
            "accounts",
            "journal_entries",
            "journal_entry_lines",
            "account_balances",
            "bank_transactions",
        )
    }

    run_exact_reconciliation(
        connection,
        cash_account_id=cash_account_id,
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="run-1",
    )

    after = {
        table: connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()[
            "count"
        ]
        for table in before
    }
    assert after == before
    run_count = connection.execute(
        "SELECT COUNT(*) AS count FROM reconciliation_runs"
    ).fetchone()["count"]
    assert run_count == 1
    assert connection.execute(
        "SELECT COUNT(*) AS count FROM reconciliation_matches"
    ).fetchone()["count"] == 1
    assert connection.execute(
        "SELECT COUNT(*) AS count FROM reconciliation_match_ledger_links"
    ).fetchone()["count"] == 1

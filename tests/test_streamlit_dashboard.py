"""Tests for the Streamlit dashboard foundation helpers."""

from __future__ import annotations

import importlib
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from dashboard.streamlit_app import (
    DASHBOARD_PAGES,
    DEFAULT_AS_OF_DATE,
    DEFAULT_END_DATE,
    DEFAULT_START_DATE,
    PAGE_BALANCE_SHEET,
    PAGE_CASH_FLOW,
    PAGE_EVENT_TIMELINE,
    PAGE_INCOME_STATEMENT,
    PAGE_OVERVIEW,
    PAGE_TRIAL_BALANCE,
    TABLE_NAMES,
    database_exists,
    format_bool_status,
    format_cents_for_dashboard,
    load_balance_sheet_report,
    load_cash_flow_report,
    load_dashboard_summary,
    load_database_counts,
    load_event_timeline,
    load_income_statement_report,
    load_trial_balance_preview,
    load_trial_balance_report,
    render_balance_sheet_page,
    render_cash_flow_page,
    render_event_timeline_page,
    render_income_statement_page,
    render_overview,
    render_trial_balance_page,
    rows_to_display_rows,
    validate_as_of_date,
    validate_date_range,
)

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.exceptions import ValidationError
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import post_journal_entry


def _initialize_test_database(db_path: Path) -> sqlite3.Connection:
    connection = connect(db_path)
    initialize_schema(connection)
    return connection


def _open_demo_accounts(connection: sqlite3.Connection) -> None:
    opened_at = "2026-01-01T00:00:00+00:00"
    accounts = [
        Account(
            account_id="acct-cash",
            code="1000",
            name="Cash",
            account_type="asset",
            normal_balance="debit",
            is_active=True,
            opened_at=opened_at,
        ),
        Account(
            account_id="acct-equity",
            code="3000",
            name="Owner Equity",
            account_type="equity",
            normal_balance="credit",
            is_active=True,
            opened_at=opened_at,
        ),
        Account(
            account_id="acct-revenue",
            code="4000",
            name="Service Revenue",
            account_type="revenue",
            normal_balance="credit",
            is_active=True,
            opened_at=opened_at,
        ),
        Account(
            account_id="acct-software",
            code="5100",
            name="Software Expense",
            account_type="expense",
            normal_balance="debit",
            is_active=True,
            opened_at=opened_at,
        ),
    ]

    for account in accounts:
        open_account(connection, account=account)


def _post_demo_entries(connection: sqlite3.Connection) -> None:
    post_journal_entry(
        connection,
        journal_entry=JournalEntry(
            journal_entry_id="je-owner-contribution",
            entry_date=date(2026, 1, 1),
            description="Owner contribution",
            source="demo",
            external_reference="DEMO",
            lines=[
                JournalLine(
                    line_id="line-owner-contribution-cash",
                    journal_entry_id="je-owner-contribution",
                    account_id="acct-cash",
                    side="debit",
                    amount_cents=500_000,
                    description="Cash received",
                    line_number=1,
                ),
                JournalLine(
                    line_id="line-owner-contribution-equity",
                    journal_entry_id="je-owner-contribution",
                    account_id="acct-equity",
                    side="credit",
                    amount_cents=500_000,
                    description="Owner equity",
                    line_number=2,
                ),
            ],
        ),
    )
    post_journal_entry(
        connection,
        journal_entry=JournalEntry(
            journal_entry_id="je-customer-payment",
            entry_date=date(2026, 1, 3),
            description="Customer payment",
            source="demo",
            external_reference="DEMO",
            lines=[
                JournalLine(
                    line_id="line-customer-payment-cash",
                    journal_entry_id="je-customer-payment",
                    account_id="acct-cash",
                    side="debit",
                    amount_cents=120_000,
                    description="Cash received",
                    line_number=1,
                ),
                JournalLine(
                    line_id="line-customer-payment-revenue",
                    journal_entry_id="je-customer-payment",
                    account_id="acct-revenue",
                    side="credit",
                    amount_cents=120_000,
                    description="Service revenue",
                    line_number=2,
                ),
            ],
        ),
    )
    post_journal_entry(
        connection,
        journal_entry=JournalEntry(
            journal_entry_id="je-software",
            entry_date=date(2026, 1, 5),
            description="Software subscription",
            source="demo",
            external_reference="DEMO",
            lines=[
                JournalLine(
                    line_id="line-software-expense",
                    journal_entry_id="je-software",
                    account_id="acct-software",
                    side="debit",
                    amount_cents=5_000,
                    description="Accounting software",
                    line_number=1,
                ),
                JournalLine(
                    line_id="line-software-cash",
                    journal_entry_id="je-software",
                    account_id="acct-cash",
                    side="credit",
                    amount_cents=5_000,
                    description="Cash payment",
                    line_number=2,
                ),
            ],
        ),
    )


def _insert_demo_bank_and_reconciliation_data(
    connection: sqlite3.Connection,
) -> None:
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
        (
            "import-demo",
            "demo",
            "bank_statement.csv",
            "hash-demo",
            "2026-01-01T00:00:00+00:00",
            1,
        ),
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
            "bank-demo",
            "import-demo",
            "2026-01-01",
            "2026-01-01",
            "DEPOSIT OWNER CONTRIBUTION",
            "deposit owner contribution",
            500_000,
            "BANK-001",
            None,
            "row-hash-demo",
            None,
            "2026-01-01T00:00:00+00:00",
        ),
    )
    connection.execute(
        """
        INSERT INTO reconciliation_runs (
            reconciliation_run_id,
            cash_account_id,
            statement_start_date,
            statement_end_date,
            started_at,
            completed_at,
            status,
            config_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "recon-demo",
            "acct-cash",
            "2026-01-01",
            "2026-01-31",
            "2026-01-31T00:00:00+00:00",
            "2026-01-31T00:00:01+00:00",
            "completed",
            "{}",
        ),
    )
    connection.execute(
        """
        INSERT INTO reconciliation_matches (
            reconciliation_match_id,
            reconciliation_run_id,
            bank_transaction_id,
            match_type,
            score,
            amount_delta_cents,
            date_delta_days,
            status,
            explanation_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "match-demo",
            "recon-demo",
            "bank-demo",
            "exact",
            100.0,
            0,
            0,
            "auto_matched",
            "{}",
            "2026-01-31T00:00:01+00:00",
        ),
    )
    connection.commit()


def _create_demo_database(db_path: Path) -> None:
    connection = _initialize_test_database(db_path)
    _open_demo_accounts(connection)
    _post_demo_entries(connection)
    _insert_demo_bank_and_reconciliation_data(connection)
    connection.close()


def test_database_exists_returns_false_for_missing_path(tmp_path: Path) -> None:
    assert database_exists(tmp_path / "missing.db") is False


def test_database_exists_returns_true_for_existing_sqlite_file(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "existing.db"
    sqlite3.connect(db_path).close()

    assert database_exists(db_path) is True


def test_dashboard_navigation_and_page_helpers_exist() -> None:
    assert DASHBOARD_PAGES == (
        PAGE_OVERVIEW,
        PAGE_TRIAL_BALANCE,
        PAGE_INCOME_STATEMENT,
        PAGE_BALANCE_SHEET,
        PAGE_CASH_FLOW,
        PAGE_EVENT_TIMELINE,
    )
    assert callable(render_overview)
    assert callable(render_trial_balance_page)
    assert callable(render_income_statement_page)
    assert callable(render_balance_sheet_page)
    assert callable(render_cash_flow_page)
    assert callable(render_event_timeline_page)


def test_default_report_dates_are_available() -> None:
    assert DEFAULT_START_DATE == date(2026, 1, 1)
    assert DEFAULT_END_DATE == date(2026, 1, 31)
    assert DEFAULT_AS_OF_DATE == date(2026, 1, 31)


def test_date_validation_accepts_valid_report_dates() -> None:
    validate_date_range(date(2026, 1, 1), date(2026, 1, 31))
    validate_as_of_date(date(2026, 1, 31))


def test_date_validation_rejects_invalid_report_dates() -> None:
    try:
        validate_date_range(date(2026, 2, 1), date(2026, 1, 31))
    except ValidationError as error:
        assert "start_date" in str(error)
    else:
        raise AssertionError("Expected invalid date range to fail")

    try:
        validate_as_of_date(datetime(2026, 1, 31, 12, 0))
    except ValidationError as error:
        assert "as_of_date" in str(error)
    else:
        raise AssertionError("Expected datetime as-of value to fail")


def test_table_count_helper_handles_missing_database_gracefully(
    tmp_path: Path,
) -> None:
    counts = load_database_counts(tmp_path / "missing.db")

    assert counts == {table_name: 0 for table_name in TABLE_NAMES}


def test_table_count_helper_returns_counts_for_initialized_empty_schema(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "empty.db"
    connection = _initialize_test_database(db_path)
    connection.close()

    counts = load_database_counts(db_path)

    assert counts["ledger_events"] == 0
    assert counts["accounts"] == 0
    assert counts["journal_entries"] == 0
    assert counts["account_balances"] == 0


def test_table_count_helper_returns_counts_after_demo_like_setup(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    counts = load_database_counts(db_path)

    assert counts["ledger_events"] == 7
    assert counts["accounts"] == 4
    assert counts["journal_entries"] == 3
    assert counts["journal_entry_lines"] == 6
    assert counts["account_balances"] == 4
    assert counts["bank_statement_imports"] == 1
    assert counts["bank_transactions"] == 1
    assert counts["reconciliation_runs"] == 1
    assert counts["reconciliation_matches"] == 1


def test_trial_balance_report_loads_rows_and_totals(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    report = load_trial_balance_report(db_path)

    assert report["available"] is True
    assert len(report["rows"]) == 4
    assert report["totals"]["is_balanced"] is True


def test_trial_balance_preview_returns_rows_after_demo_like_setup(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    rows = load_trial_balance_preview(db_path)

    assert rows
    assert rows[0]["code"] == "1000"
    assert rows[0]["name"] == "Cash"
    assert rows[0]["ending_debit"] == "$6,150.00"


def test_income_statement_report_loads_rows_for_date_range(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    report = load_income_statement_report(
        db_path,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert report["available"] is True
    assert report["start_date"] == "2026-01-01"
    assert report["end_date"] == "2026-01-31"
    assert report["rows"]
    assert report["totals"]["net_income_cents"] == 115_000


def test_income_statement_invalid_date_range_is_friendly(
    tmp_path: Path,
) -> None:
    report = load_income_statement_report(
        tmp_path / "missing.db",
        date(2026, 2, 1),
        date(2026, 1, 31),
    )

    assert report["available"] is False
    assert report["rows"] == []
    assert "start_date" in str(report["error"])


def test_balance_sheet_report_loads_rows_for_as_of_date(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    report = load_balance_sheet_report(db_path, date(2026, 1, 31))

    assert report["available"] is True
    assert report["as_of_date"] == "2026-01-31"
    assert report["rows"]
    assert report["totals"]["is_balanced"] is True


def test_balance_sheet_invalid_as_of_date_is_friendly(
    tmp_path: Path,
) -> None:
    report = load_balance_sheet_report(
        tmp_path / "missing.db",
        datetime(2026, 1, 31, 12, 0),
    )

    assert report["available"] is False
    assert report["rows"] == []
    assert "as_of_date" in str(report["error"])


def test_cash_flow_report_loads_statement_and_totals(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    report = load_cash_flow_report(
        db_path,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert report["available"] is True
    assert report["start_date"] == "2026-01-01"
    assert report["end_date"] == "2026-01-31"
    assert report["rows"]
    assert report["totals"]["cash_balances_tie"] is True
    assert report["totals"]["ending_cash_cents"] == 615_000


def test_cash_flow_invalid_date_range_is_friendly(
    tmp_path: Path,
) -> None:
    report = load_cash_flow_report(
        tmp_path / "missing.db",
        date(2026, 2, 1),
        date(2026, 1, 31),
    )

    assert report["available"] is False
    assert report["rows"] == []
    assert "start_date" in str(report["error"])


def test_event_timeline_returns_events_in_sequence_order(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    events = load_event_timeline(db_path)

    event_sequences = [event["event_sequence"] for event in events]
    assert event_sequences == sorted(event_sequences)
    assert len(events) == 7


def test_event_timeline_returns_expected_event_fields(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    event = load_event_timeline(db_path)[0]

    assert event["event_sequence"] == 1
    assert event["event_type"] == "AccountOpened"
    assert event["effective_date"] == "2026-01-01"
    assert event["event_timestamp"]
    assert event["source"]
    assert "payload_json" in event


def test_event_timeline_handles_empty_event_log(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.db"
    connection = _initialize_test_database(db_path)
    connection.close()

    assert load_event_timeline(db_path) == []


def test_missing_database_report_helpers_return_unavailable(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "missing.db"

    assert load_trial_balance_report(db_path)["available"] is False
    assert load_balance_sheet_report(db_path, date(2026, 1, 31))[
        "available"
    ] is False
    assert load_cash_flow_report(
        db_path,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )["available"] is False
    assert load_event_timeline(db_path) == []


def test_summary_helper_returns_json_serializable_data(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    summary = load_dashboard_summary(db_path)

    json.dumps(summary)
    assert summary["database_exists"] is True
    assert summary["ledger_events"] == 7
    assert summary["accounts"] == 4
    assert summary["posted_journal_entries"] == 3
    assert summary["trial_balance_balanced"] is True
    assert summary["cash_ending_balance"] == "$6,150.00"


def test_summary_helper_handles_empty_database(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.db"
    connection = _initialize_test_database(db_path)
    connection.close()

    summary = load_dashboard_summary(db_path)

    assert summary["database_exists"] is True
    assert summary["ledger_events"] == 0
    assert summary["accounts"] == 0
    assert summary["trial_balance_balanced"] is None
    assert summary["cash_ending_balance"] == "N/A"


def test_missing_optional_tables_do_not_crash_helpers(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "partial.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE ledger_events (
            event_sequence INTEGER PRIMARY KEY AUTOINCREMENT
        )
        """
    )
    connection.commit()
    connection.close()

    counts = load_database_counts(db_path)
    summary = load_dashboard_summary(db_path)
    preview = load_trial_balance_preview(db_path)

    assert counts["ledger_events"] == 0
    assert counts["category_corrections"] == 0
    assert summary["database_exists"] is True
    assert summary["accounts"] == 0
    assert preview == []


def test_format_cents_for_dashboard_handles_expected_values() -> None:
    assert format_cents_for_dashboard(123_456) == "$1,234.56"
    assert format_cents_for_dashboard(-123_456) == "-$1,234.56"
    assert format_cents_for_dashboard(0) == "$0.00"
    assert format_cents_for_dashboard(None) == "N/A"


def test_format_bool_status_handles_expected_values() -> None:
    assert format_bool_status(True) == "Yes"
    assert format_bool_status(False) == "No"
    assert format_bool_status(None) == "N/A"


def test_rows_to_display_rows_converts_cent_fields() -> None:
    rows = [
        {
            "account_name": "Cash",
            "ending_debit_balance_cents": 12_345,
            "ending_credit_balance_cents": 0,
        }
    ]

    display_rows = rows_to_display_rows(rows)

    assert display_rows == [
        {
            "account_name": "Cash",
            "ending_debit_balance": "$123.45",
            "ending_credit_balance": "$0.00",
        }
    ]


def test_dashboard_helpers_return_json_serializable_data(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    payload = {
        "summary": load_dashboard_summary(db_path),
        "trial_balance": load_trial_balance_report(db_path),
        "income_statement": load_income_statement_report(
            db_path,
            date(2026, 1, 1),
            date(2026, 1, 31),
        ),
        "balance_sheet": load_balance_sheet_report(
            db_path,
            date(2026, 1, 31),
        ),
        "cash_flow": load_cash_flow_report(
            db_path,
            date(2026, 1, 1),
            date(2026, 1, 31),
        ),
        "events": load_event_timeline(db_path),
    }

    json.dumps(payload)


def test_importing_streamlit_app_does_not_launch_the_app() -> None:
    module = importlib.import_module("dashboard.streamlit_app")
    reloaded = importlib.reload(module)

    assert callable(reloaded.main)


def test_report_helpers_do_not_append_ledger_events(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)
    connection = connect(db_path)
    before = connection.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]

    load_database_counts(db_path)
    load_dashboard_summary(db_path)
    load_trial_balance_preview(db_path)
    load_trial_balance_report(db_path)
    load_income_statement_report(db_path, date(2026, 1, 1), date(2026, 1, 31))
    load_balance_sheet_report(db_path, date(2026, 1, 31))
    load_cash_flow_report(db_path, date(2026, 1, 1), date(2026, 1, 31))
    load_event_timeline(db_path)

    after = connection.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]
    connection.close()

    assert after == before


def test_report_helpers_do_not_mutate_account_balances(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)
    connection = connect(db_path)
    before = connection.execute(
        """
        SELECT account_id, debit_total_cents, credit_total_cents, balance_cents
        FROM account_balances
        ORDER BY account_id
        """
    ).fetchall()

    load_database_counts(db_path)
    load_dashboard_summary(db_path)
    load_trial_balance_preview(db_path)
    load_trial_balance_report(db_path)
    load_income_statement_report(db_path, date(2026, 1, 1), date(2026, 1, 31))
    load_balance_sheet_report(db_path, date(2026, 1, 31))
    load_cash_flow_report(db_path, date(2026, 1, 1), date(2026, 1, 31))
    load_event_timeline(db_path)

    after = connection.execute(
        """
        SELECT account_id, debit_total_cents, credit_total_cents, balance_cents
        FROM account_balances
        ORDER BY account_id
        """
    ).fetchall()
    connection.close()

    assert [tuple(row) for row in after] == [tuple(row) for row in before]


def test_event_timeline_helper_does_not_mutate_ledger_events(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)
    connection = connect(db_path)
    before = connection.execute(
        """
        SELECT event_sequence, event_id, event_type, payload_json
        FROM ledger_events
        ORDER BY event_sequence
        """
    ).fetchall()

    load_event_timeline(db_path)

    after = connection.execute(
        """
        SELECT event_sequence, event_id, event_type, payload_json
        FROM ledger_events
        ORDER BY event_sequence
        """
    ).fetchall()
    connection.close()

    assert [tuple(row) for row in after] == [tuple(row) for row in before]


def test_helper_functions_do_not_import_bank_files(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.db"
    connection = _initialize_test_database(db_path)

    load_database_counts(db_path)
    load_dashboard_summary(db_path)
    load_trial_balance_preview(db_path)
    load_trial_balance_report(db_path)
    load_income_statement_report(db_path, date(2026, 1, 1), date(2026, 1, 31))
    load_balance_sheet_report(db_path, date(2026, 1, 31))
    load_cash_flow_report(db_path, date(2026, 1, 1), date(2026, 1, 31))
    load_event_timeline(db_path)

    bank_imports = connection.execute(
        "SELECT COUNT(*) FROM bank_statement_imports"
    ).fetchone()[0]
    bank_transactions = connection.execute(
        "SELECT COUNT(*) FROM bank_transactions"
    ).fetchone()[0]
    connection.close()

    assert bank_imports == 0
    assert bank_transactions == 0


def test_helper_functions_do_not_run_reconciliation(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.db"
    connection = _initialize_test_database(db_path)
    _open_demo_accounts(connection)
    _post_demo_entries(connection)

    load_database_counts(db_path)
    load_dashboard_summary(db_path)
    load_trial_balance_preview(db_path)
    load_trial_balance_report(db_path)
    load_income_statement_report(db_path, date(2026, 1, 1), date(2026, 1, 31))
    load_balance_sheet_report(db_path, date(2026, 1, 31))
    load_cash_flow_report(db_path, date(2026, 1, 1), date(2026, 1, 31))
    load_event_timeline(db_path)

    runs = connection.execute("SELECT COUNT(*) FROM reconciliation_runs").fetchone()[0]
    matches = connection.execute(
        "SELECT COUNT(*) FROM reconciliation_matches"
    ).fetchone()[0]
    connection.close()

    assert runs == 0
    assert matches == 0


def test_helper_functions_do_not_write_exports(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.db"
    exports_path = tmp_path / "exports"
    _create_demo_database(db_path)

    load_database_counts(db_path)
    load_dashboard_summary(db_path)
    load_trial_balance_preview(db_path)
    load_trial_balance_report(db_path)
    load_income_statement_report(db_path, date(2026, 1, 1), date(2026, 1, 31))
    load_balance_sheet_report(db_path, date(2026, 1, 31))
    load_cash_flow_report(db_path, date(2026, 1, 1), date(2026, 1, 31))
    load_event_timeline(db_path)

    assert not exports_path.exists()

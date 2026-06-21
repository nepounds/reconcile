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
    PAGE_BANK_RECONCILIATION,
    PAGE_CASH_FLOW,
    PAGE_CATEGORIZATION_REVIEW,
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
    load_categorization_review,
    load_categorization_review_rows,
    load_category_correction_summary,
    load_dashboard_summary,
    load_database_counts,
    load_event_timeline,
    load_income_statement_report,
    load_reconciliation_match_details,
    load_reconciliation_review,
    load_reconciliation_runs,
    load_trial_balance_preview,
    load_trial_balance_report,
    parse_explanation_json,
    render_balance_sheet_page,
    render_bank_reconciliation_page,
    render_cash_flow_page,
    render_categorization_review_page,
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
    connection.execute(
        """
        INSERT INTO reconciliation_match_ledger_links (
            reconciliation_match_id,
            journal_entry_id,
            journal_entry_line_id,
            amount_cents
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            "match-demo",
            "je-owner-contribution",
            "line-owner-contribution-cash",
            500_000,
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
        PAGE_BANK_RECONCILIATION,
        PAGE_CATEGORIZATION_REVIEW,
    )
    assert callable(render_overview)
    assert callable(render_trial_balance_page)
    assert callable(render_income_statement_page)
    assert callable(render_balance_sheet_page)
    assert callable(render_cash_flow_page)
    assert callable(render_event_timeline_page)
    assert callable(render_bank_reconciliation_page)
    assert callable(render_categorization_review_page)


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



def _insert_category_corrections_table(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS category_corrections (
            correction_id TEXT PRIMARY KEY,
            bank_transaction_id TEXT NOT NULL,
            corrected_category TEXT NOT NULL,
            corrected_by TEXT,
            reason TEXT,
            corrected_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(bank_transaction_id)
                REFERENCES bank_transactions(bank_transaction_id)
        )
        """
    )


def _insert_categorization_review_bank_rows(
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
            "import-categorization",
            "demo",
            "categorization.csv",
            "hash-categorization",
            "2026-01-01T00:00:00+00:00",
            3,
        ),
    )
    rows = [
        (
            "bank-software",
            "2026-01-05",
            "POS SOFTWARE SUBSCRIPTION",
            "pos software subscription",
            -5_000,
            None,
        ),
        (
            "bank-uncategorized",
            "2026-01-06",
            "MYSTERY PAYMENT",
            "mystery payment",
            -1_234,
            "dup-fingerprint-demo",
        ),
        (
            "bank-correction",
            "2026-01-07",
            "POS SOFTWARE SUBSCRIPTION",
            "pos software subscription",
            -7_500,
            None,
        ),
    ]
    for index, row in enumerate(rows, start=1):
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
                row[0],
                "import-categorization",
                row[1],
                row[1],
                row[2],
                row[3],
                row[4],
                f"CAT-{index}",
                None,
                f"row-hash-cat-{index}",
                row[5],
                "2026-01-01T00:00:00+00:00",
            ),
        )
    connection.commit()


def _insert_demo_category_correction(
    connection: sqlite3.Connection,
) -> None:
    _insert_category_corrections_table(connection)
    connection.execute(
        """
        INSERT INTO category_corrections (
            correction_id,
            bank_transaction_id,
            corrected_category,
            corrected_by,
            reason,
            corrected_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "corr-demo",
            "bank-correction",
            "Office Supplies",
            "tester",
            "Manual review correction",
            "2026-01-08T00:00:00+00:00",
            "2026-01-08T00:00:00+00:00",
        ),
    )
    connection.commit()


def test_parse_explanation_json_handles_valid_and_invalid_json() -> None:
    exact = parse_explanation_json(
        json.dumps(
            {
                "match_type": "exact",
                "status": "auto_matched",
                "reason": "Exact amount and date match",
            }
        )
    )
    malformed = parse_explanation_json("{not-json")
    blank = parse_explanation_json(None)

    assert exact["valid"] is True
    assert exact["summary"] == "Exact amount and date match"
    assert malformed["valid"] is False
    assert malformed["summary"] == "Invalid explanation JSON"
    assert blank["summary"] == "No explanation JSON"


def test_parse_explanation_json_tolerates_score_and_split_shapes() -> None:
    payload = {
        "score_components": {
            "amount_score": 100.0,
            "date_score": 95.0,
            "description_score": 80.0,
            "duplicate_penalty": 0.0,
            "split_penalty": 5.0,
        },
        "component_details": [
            {"journal_entry_id": "je-1", "amount_cents": 1_000},
        ],
        "decision_reason": "Split candidate accepted",
    }

    parsed = parse_explanation_json(json.dumps(payload))

    assert parsed["valid"] is True
    assert parsed["score_components"]["amount_score"] == 100.0
    assert parsed["split_components"] == payload["component_details"]
    assert parsed["decision_reason"] == "Split candidate accepted"


def test_reconciliation_missing_database_returns_friendly_empty_data(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "missing.db"

    review = load_reconciliation_review(db_path)

    assert load_reconciliation_runs(db_path) == []
    assert review["available"] is False
    assert review["matches"] == []
    assert load_reconciliation_match_details(db_path, "match-missing") is None


def test_reconciliation_empty_schema_returns_no_runs_or_matches(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "empty.db"
    connection = _initialize_test_database(db_path)
    connection.close()

    review = load_reconciliation_review(db_path)

    assert load_reconciliation_runs(db_path) == []
    assert review["available"] is True
    assert review["matches"] == []


def test_reconciliation_runs_load_in_deterministic_order(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)
    connection = connect(db_path)
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
            "recon-later",
            "acct-cash",
            "2026-01-01",
            "2026-01-31",
            "2026-02-01T00:00:00+00:00",
            "2026-02-01T00:00:01+00:00",
            "completed",
            json.dumps({"mode": "fuzzy"}),
        ),
    )
    connection.commit()
    connection.close()

    runs = load_reconciliation_runs(db_path)

    assert [run["reconciliation_run_id"] for run in runs] == [
        "recon-later",
        "recon-demo",
    ]
    assert runs[0]["config"] == {"mode": "fuzzy"}


def test_reconciliation_review_loads_match_rows_and_links(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    review = load_reconciliation_review(db_path, "recon-demo")
    match = review["matches"][0]

    assert review["available"] is True
    assert match["bank_transaction_id"] == "bank-demo"
    assert match["bank_transaction_date"] == "2026-01-01"
    assert match["bank_description_raw"] == "DEPOSIT OWNER CONTRIBUTION"
    assert match["match_type"] == "exact"
    assert match["match_status"] == "auto_matched"
    assert match["score"] == 100.0
    assert match["amount_delta_cents"] == 0
    assert match["date_delta_days"] == 0
    assert match["ledger_link_count"] == 1
    assert match["matched_ledger_journal_entry_ids"] == [
        "je-owner-contribution"
    ]
    assert match["matched_ledger_journal_line_ids"] == [
        "line-owner-contribution-cash"
    ]


def test_reconciliation_match_details_loads_ledger_detail(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    details = load_reconciliation_match_details(db_path, "match-demo")

    assert details is not None
    assert details["ledger_link_count"] == 1
    assert details["ledger_links"][0]["journal_entry_id"] == (
        "je-owner-contribution"
    )
    assert details["ledger_links"][0]["journal_entry_date"] == "2026-01-01"
    assert details["ledger_links"][0]["account_code"] == "1000"


def test_reconciliation_helper_output_is_json_serializable(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)

    payload = {
        "runs": load_reconciliation_runs(db_path),
        "review": load_reconciliation_review(db_path),
        "details": load_reconciliation_match_details(db_path, "match-demo"),
    }

    json.dumps(payload)


def test_reconciliation_helpers_do_not_mutate_database(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_database(db_path)
    connection = connect(db_path)
    before_events = connection.execute(
        "SELECT COUNT(*) FROM ledger_events"
    ).fetchone()[0]
    before_bank_rows = connection.execute(
        "SELECT COUNT(*) FROM bank_transactions"
    ).fetchone()[0]
    before_runs = connection.execute(
        "SELECT COUNT(*) FROM reconciliation_runs"
    ).fetchone()[0]
    before_matches = connection.execute(
        "SELECT COUNT(*) FROM reconciliation_matches"
    ).fetchone()[0]

    load_reconciliation_runs(db_path)
    load_reconciliation_review(db_path)
    load_reconciliation_match_details(db_path, "match-demo")

    after_events = connection.execute(
        "SELECT COUNT(*) FROM ledger_events"
    ).fetchone()[0]
    after_bank_rows = connection.execute(
        "SELECT COUNT(*) FROM bank_transactions"
    ).fetchone()[0]
    after_runs = connection.execute(
        "SELECT COUNT(*) FROM reconciliation_runs"
    ).fetchone()[0]
    after_matches = connection.execute(
        "SELECT COUNT(*) FROM reconciliation_matches"
    ).fetchone()[0]
    connection.close()

    assert after_events == before_events
    assert after_bank_rows == before_bank_rows
    assert after_runs == before_runs
    assert after_matches == before_matches


def test_categorization_missing_database_returns_friendly_empty_data(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "missing.db"

    review = load_categorization_review(db_path)

    assert review["available"] is False
    assert review["rows"] == []
    assert load_categorization_review_rows(db_path) == []
    assert load_category_correction_summary(db_path)["correction_count"] == 0


def test_categorization_empty_schema_returns_no_rows(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "empty.db"
    connection = _initialize_test_database(db_path)
    connection.close()

    review = load_categorization_review(db_path)

    assert review["available"] is True
    assert review["rows"] == []
    assert review["summary"]["total_bank_transactions"] == 0


def test_categorization_review_shows_rules_corrections_and_unknowns(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "categories.db"
    connection = _initialize_test_database(db_path)
    _insert_categorization_review_bank_rows(connection)
    _insert_demo_category_correction(connection)
    connection.close()

    rows = load_categorization_review_rows(db_path)
    by_id = {row["bank_transaction_id"]: row for row in rows}

    assert by_id["bank-software"]["category"] == "Software"
    assert by_id["bank-software"]["category_source"] == "rule"
    assert by_id["bank-software"]["category_rule_id"]
    assert by_id["bank-correction"]["category"] == "Office Supplies"
    assert by_id["bank-correction"]["category_source"] == "correction"
    assert by_id["bank-correction"]["correction_id"] == "corr-demo"
    assert by_id["bank-uncategorized"]["category"] is None
    assert by_id["bank-uncategorized"]["duplicate_group_id"] == (
        "dup-fingerprint-demo"
    )


def test_categorization_summary_counts_review_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "categories.db"
    connection = _initialize_test_database(db_path)
    _insert_categorization_review_bank_rows(connection)
    _insert_demo_category_correction(connection)
    connection.close()

    review = load_categorization_review(db_path)
    summary = review["summary"]

    assert summary["total_bank_transactions"] == 3
    assert summary["categorized_count"] == 2
    assert summary["uncategorized_count"] == 1
    assert summary["rule_based_count"] == 1
    assert summary["correction_based_count"] == 1
    assert summary["classifier_based_count"] == 0
    assert summary["duplicate_flagged_count"] == 1
    assert summary["classifier_used"] is False


def test_categorization_handles_missing_correction_table_gracefully(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "categories.db"
    connection = _initialize_test_database(db_path)
    _insert_categorization_review_bank_rows(connection)
    connection.close()

    rows = load_categorization_review_rows(db_path)
    correction_summary = load_category_correction_summary(db_path)

    assert rows
    assert correction_summary["correction_table_exists"] is False
    assert correction_summary["correction_count"] == 0


def test_categorization_helper_output_is_json_serializable(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "categories.db"
    connection = _initialize_test_database(db_path)
    _insert_categorization_review_bank_rows(connection)
    _insert_demo_category_correction(connection)
    connection.close()

    payload = {
        "review": load_categorization_review(db_path),
        "rows": load_categorization_review_rows(db_path),
        "corrections": load_category_correction_summary(db_path),
    }

    json.dumps(payload)


def test_categorization_helpers_do_not_mutate_or_write_files(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "categories.db"
    connection = _initialize_test_database(db_path)
    _insert_categorization_review_bank_rows(connection)
    _insert_demo_category_correction(connection)
    before_events = connection.execute(
        "SELECT COUNT(*) FROM ledger_events"
    ).fetchone()[0]
    before_bank_rows = connection.execute(
        "SELECT COUNT(*) FROM bank_transactions"
    ).fetchone()[0]
    before_corrections = connection.execute(
        "SELECT COUNT(*) FROM category_corrections"
    ).fetchone()[0]

    load_categorization_review(db_path)
    load_categorization_review_rows(db_path)
    load_category_correction_summary(db_path)

    after_events = connection.execute(
        "SELECT COUNT(*) FROM ledger_events"
    ).fetchone()[0]
    after_bank_rows = connection.execute(
        "SELECT COUNT(*) FROM bank_transactions"
    ).fetchone()[0]
    after_corrections = connection.execute(
        "SELECT COUNT(*) FROM category_corrections"
    ).fetchone()[0]
    connection.close()

    assert after_events == before_events
    assert after_bank_rows == before_bank_rows
    assert after_corrections == before_corrections
    assert not (tmp_path / "exports").exists()
    assert list(tmp_path.glob("*.pkl")) == []
    assert list(tmp_path.glob("*.joblib")) == []

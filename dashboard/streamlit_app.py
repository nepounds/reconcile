"""Streamlit dashboard foundation for Reconcile."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from reconcile.db import connect
from reconcile.exceptions import ValidationError
from reconcile.reports.balance_sheet import generate_balance_sheet
from reconcile.reports.cash_flow import (
    cash_flow_totals,
    generate_cash_flow_statement,
)
from reconcile.reports.income_statement import (
    generate_income_statement,
    income_statement_totals,
)
from reconcile.reports.trial_balance import (
    generate_trial_balance,
    trial_balance_totals,
)

DEFAULT_DB_PATH = Path("exports/reconcile.db")
DEFAULT_START_DATE = date(2026, 1, 1)
DEFAULT_END_DATE = date(2026, 1, 31)
DEFAULT_AS_OF_DATE = date(2026, 1, 31)

PAGE_OVERVIEW = "Overview"
PAGE_TRIAL_BALANCE = "Trial Balance"
PAGE_INCOME_STATEMENT = "Income Statement"
PAGE_BALANCE_SHEET = "Balance Sheet"
PAGE_CASH_FLOW = "Cash Flow"
PAGE_EVENT_TIMELINE = "Event Timeline"

DASHBOARD_PAGES = (
    PAGE_OVERVIEW,
    PAGE_TRIAL_BALANCE,
    PAGE_INCOME_STATEMENT,
    PAGE_BALANCE_SHEET,
    PAGE_CASH_FLOW,
    PAGE_EVENT_TIMELINE,
)

TABLE_NAMES = (
    "ledger_events",
    "accounts",
    "journal_entries",
    "journal_entry_lines",
    "account_balances",
    "bank_statement_imports",
    "bank_transactions",
    "reconciliation_runs",
    "reconciliation_matches",
    "category_corrections",
)

EVENT_TIMELINE_COLUMNS = (
    "event_sequence",
    "event_type",
    "effective_date",
    "event_timestamp",
    "source",
    "actor",
    "correlation_id",
    "causation_id",
)

SETUP_COMMAND_LINES = (
    "python scripts/run_reconcile.py init-db "
    "--db-path exports/reconcile.db",
    "python scripts/run_reconcile.py seed-demo "
    "--db-path exports/reconcile.db",
    "python scripts/run_reconcile.py import-bank "
    "examples/demo_company/bank_statement.csv "
    "--db-path exports/reconcile.db",
    "python scripts/run_reconcile.py reconcile exact "
    "--db-path exports/reconcile.db "
    "--cash-account-id acct-cash "
    "--from 2026-01-01 "
    "--to 2026-01-31",
)

SETUP_COMMANDS = "\n".join(SETUP_COMMAND_LINES)


ReportRow = dict[str, object]
ReportResult = dict[str, object]


def database_exists(db_path: str | Path) -> bool:
    """Return whether the dashboard database file exists."""
    return Path(db_path).is_file()


def format_cents_for_dashboard(cents: int | None) -> str:
    """Format integer cents for dashboard display."""
    if cents is None:
        return "N/A"

    if not isinstance(cents, int) or isinstance(cents, bool):
        raise TypeError("cents must be an integer or None")

    sign = "-" if cents < 0 else ""
    absolute_cents = abs(cents)
    dollars = absolute_cents // 100
    remaining_cents = absolute_cents % 100
    return f"{sign}${dollars:,}.{remaining_cents:02d}"


def format_bool_status(value: bool | None) -> str:
    """Format optional booleans for dashboard display."""
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "N/A"


def validate_date_range(start_date: date, end_date: date) -> None:
    """Validate a report date range."""
    if not isinstance(start_date, date) or isinstance(start_date, datetime):
        raise ValidationError("start_date must be a date")

    if not isinstance(end_date, date) or isinstance(end_date, datetime):
        raise ValidationError("end_date must be a date")

    if start_date > end_date:
        raise ValidationError("start_date must be on or before end_date")


def validate_as_of_date(as_of_date: date) -> None:
    """Validate a report as-of date."""
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise ValidationError("as_of_date must be a date")


def rows_to_display_rows(rows: list[ReportRow]) -> list[ReportRow]:
    """Convert report rows with cent fields into display rows."""
    display_rows = []

    for row in rows:
        display_row = dict(row)
        for key, value in row.items():
            if key.endswith("_cents"):
                display_key = key.removesuffix("_cents")
                cents = int(value) if value is not None else None
                display_row[display_key] = format_cents_for_dashboard(cents)
                display_row.pop(key, None)
        display_rows.append(display_row)

    return display_rows


def _first_existing_value(
    values: dict[str, object],
    keys: tuple[str, ...],
) -> object | None:
    for key in keys:
        if key in values:
            return values[key]
    return None


def _first_existing_int(
    values: dict[str, object],
    keys: tuple[str, ...],
) -> int:
    """Return the first available integer value from possible report keys."""
    value = _first_existing_value(values, keys)
    if value is not None:
        return int(value)

    available_keys = ", ".join(sorted(values))
    expected_keys = ", ".join(keys)
    raise KeyError(
        f"Expected one of {expected_keys}; available keys: {available_keys}"
    )


def _extract_report_rows(statement: object) -> list[dict[str, object]]:
    """Extract display rows from list or sectioned report dictionaries."""
    if isinstance(statement, list):
        return [
            dict(row)
            for row in statement
            if isinstance(row, dict)
        ]

    if not isinstance(statement, dict):
        return []

    direct_rows = statement.get("rows")
    if isinstance(direct_rows, list):
        return [
            dict(row)
            for row in direct_rows
            if isinstance(row, dict)
        ]

    rows = []
    for section_name, section_value in statement.items():
        if not isinstance(section_value, list):
            continue

        for item in section_value:
            if not isinstance(item, dict):
                continue

            row = dict(item)
            row.setdefault("section", section_name)
            rows.append(row)

    return rows


def _cash_flow_rows_from_totals(
    totals: dict[str, object],
) -> list[dict[str, object]]:
    """Build cash flow section rows from totals when no detail rows exist."""
    return [
        {
            "section": "operating",
            "description": "Operating cash flow",
            "amount_cents": _first_existing_int(
                totals,
                (
                    "operating_cash_flow_cents",
                    "net_operating_cash_flow_cents",
                ),
            ),
        },
        {
            "section": "investing",
            "description": "Investing cash flow",
            "amount_cents": _first_existing_int(
                totals,
                (
                    "investing_cash_flow_cents",
                    "net_investing_cash_flow_cents",
                ),
            ),
        },
        {
            "section": "financing",
            "description": "Financing cash flow",
            "amount_cents": _first_existing_int(
                totals,
                (
                    "financing_cash_flow_cents",
                    "net_financing_cash_flow_cents",
                ),
            ),
        },
    ]


def _rows_from_statement(statement: object) -> list[ReportRow]:
    """Extract row dictionaries from supported report statement shapes."""
    if isinstance(statement, list):
        return [dict(row) for row in statement]

    if not isinstance(statement, dict):
        return []

    rows = statement.get("rows")
    if isinstance(rows, list):
        return [dict(row) for row in rows]

    section_rows: list[ReportRow] = []
    section_keys = (
        "asset_rows",
        "liability_rows",
        "equity_rows",
        "revenue_rows",
        "expense_rows",
        "operating_rows",
        "investing_rows",
        "financing_rows",
        "assets",
        "liabilities",
        "equity",
        "revenues",
        "expenses",
        "operating",
        "investing",
        "financing",
    )
    for key in section_keys:
        value = statement.get(key)
        if isinstance(value, list):
            for row in value:
                display_row = dict(row)
                display_row.setdefault("section", key.removesuffix("_rows"))
                section_rows.append(display_row)

    return section_rows


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _count_table(connection: sqlite3.Connection, table_name: str) -> int:
    if not _table_exists(connection, table_name):
        return 0

    row = connection.execute(
        f"SELECT COUNT(*) AS row_count FROM {table_name}"
    ).fetchone()
    return int(row["row_count"])


def load_database_counts(db_path: str | Path) -> dict[str, int]:
    """Load useful table counts without mutating the database."""
    counts = {table_name: 0 for table_name in TABLE_NAMES}

    if not database_exists(db_path):
        return counts

    try:
        connection = connect(db_path)
        try:
            for table_name in TABLE_NAMES:
                counts[table_name] = _count_table(connection, table_name)
        finally:
            connection.close()
    except sqlite3.Error:
        return counts

    return counts


def load_trial_balance_report(db_path: str | Path) -> ReportResult:
    """Load trial balance report rows and totals."""
    if not database_exists(db_path):
        return {"available": False, "rows": [], "totals": {}}

    try:
        connection = connect(db_path)
        try:
            if not _table_exists(connection, "accounts"):
                return {"available": False, "rows": [], "totals": {}}
            if not _table_exists(connection, "account_balances"):
                return {"available": False, "rows": [], "totals": {}}

            rows = generate_trial_balance(connection)
            totals = trial_balance_totals(rows)
        finally:
            connection.close()
    except (sqlite3.Error, ValidationError) as error:
        return _unavailable_report(error)

    return {"available": True, "rows": rows, "totals": totals}


def load_income_statement_report(
    db_path: str | Path,
    start_date: date,
    end_date: date,
) -> ReportResult:
    """Load income statement report rows and totals."""
    try:
        validate_date_range(start_date, end_date)
    except ValidationError as error:
        return _unavailable_report(error)

    if not database_exists(db_path):
        return {"available": False, "rows": [], "totals": {}}

    try:
        connection = connect(db_path)
        try:
            statement = generate_income_statement(
                connection,
                start_date=start_date,
                end_date=end_date,
            )
            rows = _extract_report_rows(statement)
            row_totals = income_statement_totals(rows)
            totals = dict(statement) if isinstance(statement, dict) else {}
            totals.update(row_totals)
        finally:
            connection.close()
    except (sqlite3.Error, ValidationError) as error:
        return _unavailable_report(error)

    return {
        "available": True,
        "rows": rows,
        "totals": totals,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }


def load_balance_sheet_report(
    db_path: str | Path,
    as_of_date: date,
) -> ReportResult:
    """Load balance sheet report rows and totals."""
    try:
        validate_as_of_date(as_of_date)
    except ValidationError as error:
        return _unavailable_report(error)

    if not database_exists(db_path):
        return {"available": False, "rows": [], "totals": {}}

    try:
        connection = connect(db_path)
        try:
            statement = generate_balance_sheet(
                connection,
                as_of_date=as_of_date,
            )
            rows = _extract_report_rows(statement)
        finally:
            connection.close()
    except (sqlite3.Error, ValidationError) as error:
        return _unavailable_report(error)

    totals = dict(statement) if isinstance(statement, dict) else {}
    return {
        "available": True,
        "rows": rows,
        "totals": totals,
        "as_of_date": as_of_date.isoformat(),
    }


def load_cash_flow_report(
    db_path: str | Path,
    start_date: date,
    end_date: date,
) -> ReportResult:
    """Load cash flow statement rows and totals."""
    try:
        validate_date_range(start_date, end_date)
    except ValidationError as error:
        return _unavailable_report(error)

    if not database_exists(db_path):
        return {"available": False, "rows": [], "totals": {}}

    try:
        connection = connect(db_path)
        try:
            statement = generate_cash_flow_statement(
                connection,
                start_date=start_date,
                end_date=end_date,
            )
            totals = cash_flow_totals(statement)
            rows = _extract_report_rows(statement)
            if not rows:
                rows = _cash_flow_rows_from_totals(totals)
        finally:
            connection.close()
    except (sqlite3.Error, ValidationError) as error:
        return _unavailable_report(error)

    return {
        "available": True,
        "rows": rows,
        "totals": totals,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }


def load_event_timeline(db_path: str | Path) -> list[ReportRow]:
    """Load ledger events in deterministic event sequence order."""
    if not database_exists(db_path):
        return []

    try:
        connection = connect(db_path)
        try:
            if not _table_exists(connection, "ledger_events"):
                return []

            rows = connection.execute(
                """
                SELECT
                    event_sequence,
                    event_type,
                    effective_date,
                    event_timestamp,
                    source,
                    actor,
                    correlation_id,
                    causation_id,
                    payload_json
                FROM ledger_events
                ORDER BY event_sequence ASC
                """
            ).fetchall()
        finally:
            connection.close()
    except sqlite3.Error:
        return []

    return [dict(row) for row in rows]


def load_trial_balance_preview(db_path: str | Path) -> list[ReportRow]:
    """Load a small trial balance preview from an existing database."""
    report = load_trial_balance_report(db_path)
    rows = report["rows"] if report["available"] else []

    preview_rows = []
    for row in rows[:10]:
        preview_rows.append(
            {
                "code": row["account_code"],
                "name": row["account_name"],
                "type": row["account_type"],
                "debit_total": format_cents_for_dashboard(
                    int(row["debit_total_cents"])
                ),
                "credit_total": format_cents_for_dashboard(
                    int(row["credit_total_cents"])
                ),
                "ending_debit": format_cents_for_dashboard(
                    int(row["ending_debit_balance_cents"])
                ),
                "ending_credit": format_cents_for_dashboard(
                    int(row["ending_credit_balance_cents"])
                ),
            }
        )

    return preview_rows


def _load_trial_balance_status(db_path: str | Path) -> bool | None:
    report = load_trial_balance_report(db_path)
    if not report["available"]:
        return None

    rows = report["rows"]
    if not rows:
        return None

    totals = report["totals"]
    return bool(totals["is_balanced"])


def _load_cash_ending_balance(db_path: str | Path) -> int | None:
    if not database_exists(db_path):
        return None

    try:
        connection = connect(db_path)
        try:
            if not _table_exists(connection, "accounts"):
                return None
            if not _table_exists(connection, "account_balances"):
                return None

            account_count_row = connection.execute(
                "SELECT COUNT(*) AS account_count FROM accounts"
            ).fetchone()
            if int(account_count_row["account_count"]) == 0:
                return None

            row = connection.execute(
                """
                SELECT COALESCE(SUM(ab.balance_cents), 0) AS cash_balance
                FROM accounts AS a
                JOIN account_balances AS ab
                  ON ab.account_id = a.account_id
                WHERE a.account_type = 'asset'
                  AND a.normal_balance = 'debit'
                  AND (
                    lower(a.name) LIKE '%cash%'
                    OR lower(a.name) LIKE '%checking%'
                    OR lower(a.name) LIKE '%bank%'
                    OR a.code = '1000'
                  )
                """
            ).fetchone()
        finally:
            connection.close()
    except sqlite3.Error:
        return None

    if row is None:
        return None

    return int(row["cash_balance"])


def load_dashboard_summary(db_path: str | Path) -> ReportResult:
    """Load JSON-serializable dashboard summary metrics."""
    counts = load_database_counts(db_path)
    trial_balance_balanced = _load_trial_balance_status(db_path)
    cash_ending_balance = _load_cash_ending_balance(db_path)

    return {
        "database_exists": database_exists(db_path),
        "ledger_events": counts["ledger_events"],
        "accounts": counts["accounts"],
        "posted_journal_entries": counts["journal_entries"],
        "imported_bank_transactions": counts["bank_transactions"],
        "reconciliation_runs": counts["reconciliation_runs"],
        "trial_balance_balanced": trial_balance_balanced,
        "cash_ending_balance": format_cents_for_dashboard(
            cash_ending_balance
        ),
        "cash_flow_tie_status": "N/A",
    }


def _unavailable_report(error: Exception | None = None) -> ReportResult:
    result: ReportResult = {"available": False, "rows": [], "totals": {}}
    if error is not None:
        result["error"] = str(error)
    return result


def _render_setup_instructions(streamlit_module: Any) -> None:
    streamlit_module.info("No demo database found yet.")
    streamlit_module.write("Run:")
    streamlit_module.code(SETUP_COMMANDS, language="bash")


def _render_report_error(streamlit_module: Any, report: ReportResult) -> None:
    error = report.get("error")
    if error:
        streamlit_module.error(f"Unable to load report: {error}")
    else:
        streamlit_module.info("No report data is available yet.")


def _metric_cents(
    columns: Any,
    index: int,
    label: str,
    values: dict[str, object],
    keys: tuple[str, ...],
) -> None:
    columns[index].metric(
        label,
        format_cents_for_dashboard(_first_existing_int(values, keys)),
    )


def _metric_bool(
    columns: Any,
    index: int,
    label: str,
    values: dict[str, object],
    keys: tuple[str, ...],
) -> None:
    value = _first_existing_value(values, keys)
    columns[index].metric(label, format_bool_status(bool(value)))


def render_overview(db_path: str | Path) -> None:
    """Render the dashboard overview page."""
    import streamlit as st

    st.header("Overview")
    st.write(
        "This demo shows the current Reconcile engine status, database health, "
        "summary counts, and a small account-balance preview."
    )

    summary = load_dashboard_summary(db_path)
    counts = load_database_counts(db_path)

    st.success(f"Connected to local database: `{db_path}`")

    metric_columns = st.columns(4)
    metric_columns[0].metric("Ledger events", summary["ledger_events"])
    metric_columns[1].metric("Accounts", summary["accounts"])
    metric_columns[2].metric(
        "Journal entries",
        summary["posted_journal_entries"],
    )
    metric_columns[3].metric(
        "Bank transactions",
        summary["imported_bank_transactions"],
    )

    second_metric_columns = st.columns(4)
    second_metric_columns[0].metric(
        "Reconciliation runs",
        summary["reconciliation_runs"],
    )
    second_metric_columns[1].metric(
        "Trial balance balanced",
        format_bool_status(summary["trial_balance_balanced"]),
    )
    second_metric_columns[2].metric(
        "Cash ending balance",
        summary["cash_ending_balance"],
    )
    second_metric_columns[3].metric(
        "Cash flow tie",
        summary["cash_flow_tie_status"],
    )

    st.subheader("Database table counts")
    count_rows = [
        {"table": table_name, "rows": row_count}
        for table_name, row_count in counts.items()
    ]
    st.table(count_rows)

    st.subheader("Account balances preview")
    preview_rows = load_trial_balance_preview(db_path)
    if preview_rows:
        st.table(preview_rows)
    else:
        st.info("No account balance or trial balance rows are available yet.")


def render_trial_balance_page(db_path: str | Path) -> None:
    """Render the trial balance page."""
    import streamlit as st

    st.header("Trial Balance")
    report = load_trial_balance_report(db_path)

    if not report["available"]:
        _render_report_error(st, report)
        return

    rows = report["rows"]
    totals = report["totals"]

    if not rows:
        st.info("No trial balance rows are available yet.")
        return

    metric_columns = st.columns(3)
    _metric_cents(
        metric_columns,
        0,
        "Ending debit balance",
        totals,
        (
            "ending_debit_balance_cents",
            "ending_debit_balances_cents",
            "total_ending_debit_balance_cents",
        ),
    )
    _metric_cents(
        metric_columns,
        1,
        "Ending credit balance",
        totals,
        (
            "ending_credit_balance_cents",
            "ending_credit_balances_cents",
            "total_ending_credit_balance_cents",
        ),
    )
    _metric_bool(metric_columns, 2, "Balanced", totals, ("is_balanced",))

    display_rows = []
    for row in rows:
        display_rows.append(
            {
                "account_code": row["account_code"],
                "account_name": row["account_name"],
                "account_type": row["account_type"],
                "normal_balance": row["normal_balance"],
                "debit_total": format_cents_for_dashboard(
                    int(row["debit_total_cents"])
                ),
                "credit_total": format_cents_for_dashboard(
                    int(row["credit_total_cents"])
                ),
                "ending_debit_balance": format_cents_for_dashboard(
                    int(row["ending_debit_balance_cents"])
                ),
                "ending_credit_balance": format_cents_for_dashboard(
                    int(row["ending_credit_balance_cents"])
                ),
            }
        )

    st.table(display_rows)


def render_income_statement_page(db_path: str | Path) -> None:
    """Render the income statement page."""
    import streamlit as st

    st.header("Income Statement")
    start_date = st.date_input("Start date", value=DEFAULT_START_DATE)
    end_date = st.date_input("End date", value=DEFAULT_END_DATE)

    report = load_income_statement_report(db_path, start_date, end_date)

    if not report["available"]:
        _render_report_error(st, report)
        return

    st.caption(f"Selected range: {start_date.isoformat()} to {end_date.isoformat()}")

    rows = report["rows"]
    totals = report["totals"]

    metric_columns = st.columns(3)
    _metric_cents(
        metric_columns,
        0,
        "Total revenue",
        totals,
        ("total_revenue_cents", "revenue_cents"),
    )
    _metric_cents(
        metric_columns,
        1,
        "Total expenses",
        totals,
        (
            "total_expenses_cents",
            "total_expense_cents",
            "expenses_cents",
            "expense_cents",
        ),
    )
    _metric_cents(
        metric_columns,
        2,
        "Net income",
        totals,
        ("net_income_cents", "net_income_or_loss_cents"),
    )

    if not rows:
        st.info("No income statement rows are available for this range.")
        return

    st.table(rows_to_display_rows(rows))


def render_balance_sheet_page(db_path: str | Path) -> None:
    """Render the balance sheet page."""
    import streamlit as st

    st.header("Balance Sheet")
    as_of_date = st.date_input("As-of date", value=DEFAULT_AS_OF_DATE)

    report = load_balance_sheet_report(db_path, as_of_date)

    if not report["available"]:
        _render_report_error(st, report)
        return

    st.caption(f"Selected as-of date: {as_of_date.isoformat()}")

    rows = report["rows"]
    totals = report["totals"]

    metric_columns = st.columns(5)
    _metric_cents(
        metric_columns,
        0,
        "Assets",
        totals,
        ("total_assets_cents", "assets_cents"),
    )
    _metric_cents(
        metric_columns,
        1,
        "Liabilities",
        totals,
        ("total_liabilities_cents", "liabilities_cents"),
    )
    _metric_cents(
        metric_columns,
        2,
        "Equity",
        totals,
        ("total_equity_cents", "equity_cents"),
    )
    _metric_cents(
        metric_columns,
        3,
        "Liabilities + equity",
        totals,
        (
            "total_liabilities_and_equity_cents",
            "total_liability_and_equity_cents",
            "total_liabilities_plus_equity_cents",
        ),
    )
    _metric_bool(metric_columns, 4, "Balanced", totals, ("is_balanced",))

    if not rows:
        st.info("No balance sheet rows are available yet.")
        return

    st.table(rows_to_display_rows(rows))


def render_cash_flow_page(db_path: str | Path) -> None:
    """Render the cash flow page."""
    import streamlit as st

    st.header("Cash Flow")
    start_date = st.date_input("Start date", value=DEFAULT_START_DATE)
    end_date = st.date_input("End date", value=DEFAULT_END_DATE)

    report = load_cash_flow_report(db_path, start_date, end_date)

    if not report["available"]:
        _render_report_error(st, report)
        return

    st.caption(f"Selected range: {start_date.isoformat()} to {end_date.isoformat()}")

    rows = report["rows"]
    totals = report["totals"]

    metric_columns = st.columns(4)
    _metric_cents(
        metric_columns,
        0,
        "Operating",
        totals,
        (
            "operating_cash_flow_cents",
            "total_operating_cash_flow_cents",
        ),
    )
    _metric_cents(
        metric_columns,
        1,
        "Investing",
        totals,
        (
            "investing_cash_flow_cents",
            "total_investing_cash_flow_cents",
        ),
    )
    _metric_cents(
        metric_columns,
        2,
        "Financing",
        totals,
        (
            "financing_cash_flow_cents",
            "total_financing_cash_flow_cents",
        ),
    )
    _metric_cents(
        metric_columns,
        3,
        "Net change",
        totals,
        ("net_cash_change_cents", "net_change_cents"),
    )

    second_metric_columns = st.columns(3)
    _metric_cents(
        second_metric_columns,
        0,
        "Beginning cash",
        totals,
        ("beginning_cash_cents", "beginning_cash_balance_cents"),
    )
    _metric_cents(
        second_metric_columns,
        1,
        "Ending cash",
        totals,
        ("ending_cash_cents", "ending_cash_balance_cents"),
    )
    _metric_bool(
        second_metric_columns,
        2,
        "Cash balances tie",
        totals,
        ("cash_balances_tie",),
    )

    st.caption(
        "Known accounting refinement: customer collections through Accounts "
        "Receivable should classify as operating cash flow, not investing."
    )

    if not rows:
        st.info("No cash flow rows are available for this range.")
        return

    st.table(rows_to_display_rows(rows))


def render_event_timeline_page(db_path: str | Path) -> None:
    """Render the event timeline page."""
    import streamlit as st

    st.header("Event Timeline")
    events = load_event_timeline(db_path)

    if not events:
        st.info("No ledger events are available yet.")
        return

    timeline_rows = [
        {column: event.get(column) for column in EVENT_TIMELINE_COLUMNS}
        for event in events
    ]
    st.table(timeline_rows)

    st.subheader("Event payloads")
    for event in events:
        event_sequence = event["event_sequence"]
        event_type = event["event_type"]
        label = f"Event {event_sequence}: {event_type}"
        with st.expander(label):
            payload_json = str(event["payload_json"])
            try:
                payload = json.loads(payload_json)
                st.json(payload)
            except json.JSONDecodeError:
                st.code(payload_json, language="json")


def main() -> None:
    """Render the Streamlit dashboard."""
    import streamlit as st

    st.set_page_config(page_title="Reconcile", layout="wide")

    st.title("Reconcile")
    st.caption("Local-first event-sourced accounting engine")

    st.sidebar.header("Database")
    db_path_text = st.sidebar.text_input(
        "Database path",
        value=str(DEFAULT_DB_PATH),
    )
    st.sidebar.caption("This dashboard expects a local demo database.")

    selected_page = st.sidebar.radio("Page", DASHBOARD_PAGES)
    db_path = Path(db_path_text)

    if not database_exists(db_path):
        _render_setup_instructions(st)
        return

    if selected_page == PAGE_OVERVIEW:
        render_overview(db_path)
    elif selected_page == PAGE_TRIAL_BALANCE:
        render_trial_balance_page(db_path)
    elif selected_page == PAGE_INCOME_STATEMENT:
        render_income_statement_page(db_path)
    elif selected_page == PAGE_BALANCE_SHEET:
        render_balance_sheet_page(db_path)
    elif selected_page == PAGE_CASH_FLOW:
        render_cash_flow_page(db_path)
    elif selected_page == PAGE_EVENT_TIMELINE:
        render_event_timeline_page(db_path)


if __name__ == "__main__":
    main()

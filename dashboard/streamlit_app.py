"""Streamlit dashboard foundation for Reconcile."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from reconcile.db import connect
from reconcile.reports.trial_balance import (
    generate_trial_balance,
    trial_balance_totals,
)

DEFAULT_DB_PATH = Path("exports/reconcile.db")

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


def database_exists(db_path: str | Path) -> bool:
    """Return whether the dashboard database file exists."""
    return Path(db_path).is_file()


def format_cents_for_dashboard(cents: int) -> str:
    """Format integer cents for dashboard display."""
    if not isinstance(cents, int) or isinstance(cents, bool):
        raise TypeError("cents must be an integer")

    sign = "-" if cents < 0 else ""
    absolute_cents = abs(cents)
    dollars = absolute_cents // 100
    remaining_cents = absolute_cents % 100
    return f"{sign}${dollars:,}.{remaining_cents:02d}"


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
        f"SELECT COUNT(*) AS row_count FROM {table_name}").fetchone()
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


def load_trial_balance_preview(db_path: str | Path) -> list[dict[str, object]]:
    """Load a small trial balance preview from an existing database."""
    if not database_exists(db_path):
        return []

    try:
        connection = connect(db_path)
        try:
            if not _table_exists(connection, "accounts"):
                return []
            if not _table_exists(connection, "account_balances"):
                return []

            rows = generate_trial_balance(connection)
        finally:
            connection.close()
    except sqlite3.Error:
        return []

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
    if not database_exists(db_path):
        return None

    try:
        connection = connect(db_path)
        try:
            if not _table_exists(connection, "accounts"):
                return None
            if not _table_exists(connection, "account_balances"):
                return None

            rows = generate_trial_balance(connection)
            if not rows:
                return None

            totals = trial_balance_totals(rows)
            return bool(totals["is_balanced"])
        finally:
            connection.close()
    except sqlite3.Error:
        return None


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


def load_dashboard_summary(db_path: str | Path) -> dict[str, object]:
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
        "cash_ending_balance": (
            format_cents_for_dashboard(cash_ending_balance)
            if cash_ending_balance is not None
            else "N/A"
        ),
        "cash_flow_tie_status": "N/A",
    }


def _render_setup_instructions(streamlit_module: Any) -> None:
    streamlit_module.info("No demo database found yet.")
    streamlit_module.write("Run:")
    streamlit_module.code(SETUP_COMMANDS, language="bash")


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

    db_path = Path(db_path_text)

    st.header("Overview")
    st.write(
        "This demo shows the current Reconcile engine status, database health, "
        "summary counts, and a small account-balance preview."
    )

    if not database_exists(db_path):
        _render_setup_instructions(st)
        return

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
        str(summary["trial_balance_balanced"]),
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


if __name__ == "__main__":
    main()
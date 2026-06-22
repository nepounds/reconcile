"""Streamlit dashboard foundation for Reconcile."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

from reconcile.categorization.rules import (
    categorize_transaction,
    default_category_rules,
)
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
PAGE_BANK_RECONCILIATION = "Bank Reconciliation"
PAGE_CATEGORIZATION_REVIEW = "Categorization Review"

DASHBOARD_PAGES = (
    PAGE_OVERVIEW,
    PAGE_TRIAL_BALANCE,
    PAGE_INCOME_STATEMENT,
    PAGE_BALANCE_SHEET,
    PAGE_CASH_FLOW,
    PAGE_EVENT_TIMELINE,
    PAGE_BANK_RECONCILIATION,
    PAGE_CATEGORIZATION_REVIEW,
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
TABLE_NAME_SET = frozenset(TABLE_NAMES)

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


def _object_to_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an integer")
    return value


def _object_to_bool(value: object, field_name: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a boolean or None")
    return value


def _object_to_str_list(value: object, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple):
        return [str(item) for item in value]
    raise ValidationError(f"{field_name} must be a list or tuple")


def _report_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _report_rows(value: object) -> list[ReportRow]:
    if not isinstance(value, list):
        return []
    return [dict(row) for row in value if isinstance(row, dict)]


def _metric_value(value: object) -> str | int | float | None:
    if value is None or isinstance(value, str | int | float):
        return value
    return str(value)


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


def rows_to_display_rows(rows: object) -> list[ReportRow]:
    """Convert report rows with cent fields into display rows."""
    display_rows = []

    for row in _report_rows(rows):
        display_row = dict(row)
        for key, value in row.items():
            if key.endswith("_cents"):
                display_key = key.removesuffix("_cents")
                cents = (
                    _object_to_int(value, key)
                    if value is not None
                    else None
                )
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
        return _object_to_int(value, keys[0])

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


def _validate_dashboard_table_name(table_name: str) -> str:
    if table_name not in TABLE_NAME_SET:
        raise ValidationError(f"Unsupported dashboard table name: {table_name}")
    return table_name


def _count_table(connection: sqlite3.Connection, table_name: str) -> int:
    clean_table_name = _validate_dashboard_table_name(table_name)

    if not _table_exists(connection, clean_table_name):
        return 0

    query = (
        f"SELECT COUNT(*) AS row_count FROM {clean_table_name}"  # noqa: S608
    )
    row = connection.execute(query).fetchone()
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
            row_totals = income_statement_totals(
                cast("list[dict[str, int | str]]", rows)
            )
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
    rows = _report_rows(report.get("rows")) if report["available"] else []

    preview_rows = []
    for row in rows[:10]:
        preview_rows.append(
            {
                "code": row["account_code"],
                "name": row["account_name"],
                "type": row["account_type"],
                "debit_total": format_cents_for_dashboard(
                    _object_to_int(row["debit_total_cents"], "debit_total_cents")
                ),
                "credit_total": format_cents_for_dashboard(
                    _object_to_int(row["credit_total_cents"], "credit_total_cents")
                ),
                "ending_debit": format_cents_for_dashboard(
                    _object_to_int(
                        row["ending_debit_balance_cents"],
                        "ending_debit_balance_cents",
                    )
                ),
                "ending_credit": format_cents_for_dashboard(
                    _object_to_int(
                        row["ending_credit_balance_cents"],
                        "ending_credit_balance_cents",
                    )
                ),
            }
        )

    return preview_rows


def _load_trial_balance_status(db_path: str | Path) -> bool | None:
    report = load_trial_balance_report(db_path)
    if not report["available"]:
        return None

    rows = _report_rows(report.get("rows"))
    if not rows:
        return None

    totals = _report_dict(report.get("totals"))
    return _object_to_bool(totals.get("is_balanced"), "is_balanced")


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



def _safe_json_loads(value: str | None) -> object | None:
    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _json_dict(value: str | None) -> dict[str, object]:
    parsed = _safe_json_loads(value)
    if isinstance(parsed, dict):
        return parsed
    return {}


def _explanation_summary(parsed: object) -> str:
    if not isinstance(parsed, dict):
        return "Invalid explanation JSON"

    reason = parsed.get("reason") or parsed.get("decision_reason")
    if isinstance(reason, str) and reason.strip():
        return reason.strip()

    status = parsed.get("status") or parsed.get("decision_status")
    match_type = parsed.get("match_type") or parsed.get("type")
    if status and match_type:
        return f"{match_type} match marked {status}"
    if status:
        return f"Match marked {status}"
    if match_type:
        return f"{match_type} match explanation"

    return "Explanation available"


def parse_explanation_json(value: str | None) -> dict[str, object]:
    """Parse reconciliation explanation JSON for read-only review."""
    if value is None or not value.strip():
        return {
            "valid": False,
            "summary": "No explanation JSON",
            "raw": value,
            "parsed": None,
        }

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {
            "valid": False,
            "summary": "Invalid explanation JSON",
            "raw": value,
            "parsed": None,
        }

    if not isinstance(parsed, dict):
        return {
            "valid": False,
            "summary": "Explanation JSON is not an object",
            "raw": value,
            "parsed": parsed,
        }

    score_components = parsed.get("score_components")
    if not isinstance(score_components, dict):
        score_components = {
            key: parsed.get(key)
            for key in (
                "amount_score",
                "date_score",
                "description_score",
                "duplicate_penalty",
                "split_penalty",
            )
            if key in parsed
        }

    split_components = parsed.get("component_details")
    if split_components is None:
        split_components = parsed.get("split_components")

    return {
        "valid": True,
        "summary": _explanation_summary(parsed),
        "raw": value,
        "parsed": parsed,
        "score_components": score_components,
        "split_components": split_components,
        "decision_reason": parsed.get("decision_reason")
        or parsed.get("reason"),
    }


def load_reconciliation_runs(db_path: str | Path) -> list[dict[str, object]]:
    """Load reconciliation runs in deterministic newest-first order."""
    if not database_exists(db_path):
        return []

    try:
        connection = connect(db_path)
        try:
            if not _table_exists(connection, "reconciliation_runs"):
                return []

            rows = connection.execute(
                """
                SELECT
                    reconciliation_run_id,
                    cash_account_id,
                    statement_start_date,
                    statement_end_date,
                    started_at,
                    completed_at,
                    status,
                    config_json
                FROM reconciliation_runs
                ORDER BY
                    COALESCE(completed_at, started_at, '') DESC,
                    started_at DESC,
                    reconciliation_run_id ASC
                """
            ).fetchall()
        finally:
            connection.close()
    except sqlite3.Error:
        return []

    runs: list[dict[str, object]] = []
    for row in rows:
        run = dict(row)
        run["config"] = _json_dict(str(run.get("config_json") or "{}"))
        runs.append(run)

    return runs


def _load_reconciliation_links(
    connection: sqlite3.Connection,
    match_ids: list[str],
) -> list[dict[str, object]]:
    if not match_ids:
        return []
    if not _table_exists(connection, "reconciliation_match_ledger_links"):
        return []

    placeholders = ", ".join("?" for _ in match_ids)
    where_clause = (
        f"WHERE rll.reconciliation_match_id IN ({placeholders})"  # noqa: S608
    )
    query = """
        SELECT
            rll.reconciliation_match_id,
            rll.journal_entry_id,
            rll.journal_entry_line_id,
            rll.amount_cents,
            je.entry_date AS journal_entry_date,
            je.description AS journal_entry_description,
            a.code AS account_code,
            a.name AS account_name
        FROM reconciliation_match_ledger_links AS rll
        LEFT JOIN journal_entries AS je
          ON je.journal_entry_id = rll.journal_entry_id
        LEFT JOIN journal_entry_lines AS jel
          ON jel.line_id = rll.journal_entry_line_id
        LEFT JOIN accounts AS a
          ON a.account_id = jel.account_id
        """ + where_clause + """
        ORDER BY
            rll.reconciliation_match_id ASC,
            rll.journal_entry_id ASC,
            COALESCE(rll.journal_entry_line_id, '') ASC
        """
    rows = connection.execute(query, match_ids).fetchall()

    return [dict(row) for row in rows]


def _links_by_match(
    links: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for link in links:
        match_id = str(link["reconciliation_match_id"])
        grouped.setdefault(match_id, []).append(link)
    return grouped


def _reconciliation_empty_result(
    message: str,
) -> dict[str, object]:
    return {
        "available": False,
        "message": message,
        "runs": [],
        "selected_run": None,
        "matches": [],
        "ledger_links": [],
    }


def load_reconciliation_review(
    db_path: str | Path,
    reconciliation_run_id: str | None = None,
) -> dict[str, object]:
    """Load read-only reconciliation run, match, and ledger-link data."""
    if not database_exists(db_path):
        return _reconciliation_empty_result("Database does not exist.")

    runs = load_reconciliation_runs(db_path)
    if not runs:
        return {
            "available": True,
            "message": "No reconciliation runs are available yet.",
            "runs": [],
            "selected_run": None,
            "matches": [],
            "ledger_links": [],
        }

    selected_run = runs[0]
    if reconciliation_run_id is not None:
        selected_run = next(
            (
                run for run in runs
                if run["reconciliation_run_id"] == reconciliation_run_id
            ),
            runs[0],
        )

    selected_run_id = str(selected_run["reconciliation_run_id"])

    try:
        connection = connect(db_path)
        try:
            required_tables = (
                "reconciliation_matches",
                "bank_transactions",
            )
            if not all(_table_exists(connection, name) for name in required_tables):
                return {
                    "available": True,
                    "message": "No reconciliation match data is available yet.",
                    "runs": runs,
                    "selected_run": selected_run,
                    "matches": [],
                    "ledger_links": [],
                }

            rows = connection.execute(
                """
                SELECT
                    rm.reconciliation_match_id,
                    rm.reconciliation_run_id,
                    rm.bank_transaction_id,
                    bt.transaction_date AS bank_transaction_date,
                    bt.description_raw AS bank_description_raw,
                    bt.description_normalized AS bank_description_normalized,
                    bt.amount_cents AS bank_amount_cents,
                    bt.duplicate_group_id,
                    rm.match_type,
                    rm.status AS match_status,
                    rm.score,
                    rm.amount_delta_cents,
                    rm.date_delta_days,
                    rm.explanation_json,
                    rm.created_at
                FROM reconciliation_matches AS rm
                JOIN bank_transactions AS bt
                  ON bt.bank_transaction_id = rm.bank_transaction_id
                WHERE rm.reconciliation_run_id = ?
                ORDER BY
                    bt.transaction_date ASC,
                    bt.bank_transaction_id ASC,
                    rm.status ASC,
                    rm.match_type ASC,
                    rm.reconciliation_match_id ASC
                """,
                (selected_run_id,),
            ).fetchall()

            matches = [dict(row) for row in rows]
            match_ids = [str(row["reconciliation_match_id"]) for row in matches]
            links = _load_reconciliation_links(connection, match_ids)
        finally:
            connection.close()
    except sqlite3.Error:
        return _reconciliation_empty_result("Unable to load reconciliation data.")

    grouped_links = _links_by_match(links)
    for match in matches:
        match_id = str(match["reconciliation_match_id"])
        match_links = grouped_links.get(match_id, [])
        entry_ids = sorted({str(link["journal_entry_id"]) for link in match_links})
        line_ids = sorted(
            {
                str(link["journal_entry_line_id"])
                for link in match_links
                if link.get("journal_entry_line_id") is not None
            }
        )
        explanation = parse_explanation_json(
            str(match.get("explanation_json") or "")
        )
        match["ledger_link_count"] = len(match_links)
        match["matched_ledger_journal_entry_ids"] = entry_ids
        match["matched_ledger_journal_line_ids"] = line_ids
        match["explanation"] = explanation
        match["explanation_summary"] = explanation["summary"]
        match["bank_amount"] = format_cents_for_dashboard(
            int(match["bank_amount_cents"])
        )
        match["amount_delta"] = format_cents_for_dashboard(
            int(match["amount_delta_cents"])
        )

    return {
        "available": True,
        "message": "",
        "runs": runs,
        "selected_run": selected_run,
        "matches": matches,
        "ledger_links": links,
    }


def load_reconciliation_match_details(
    db_path: str | Path,
    reconciliation_match_id: str,
) -> dict[str, object] | None:
    """Load one reconciliation match with linked ledger movement details."""
    if not database_exists(db_path):
        return None
    if not reconciliation_match_id.strip():
        return None

    try:
        connection = connect(db_path)
        try:
            if not _table_exists(connection, "reconciliation_matches"):
                return None
            if not _table_exists(connection, "bank_transactions"):
                return None

            row = connection.execute(
                """
                SELECT
                    rm.reconciliation_match_id,
                    rm.reconciliation_run_id,
                    rm.bank_transaction_id,
                    bt.transaction_date AS bank_transaction_date,
                    bt.description_raw AS bank_description_raw,
                    bt.description_normalized AS bank_description_normalized,
                    bt.amount_cents AS bank_amount_cents,
                    rm.match_type,
                    rm.status AS match_status,
                    rm.score,
                    rm.amount_delta_cents,
                    rm.date_delta_days,
                    rm.explanation_json,
                    rm.created_at
                FROM reconciliation_matches AS rm
                JOIN bank_transactions AS bt
                  ON bt.bank_transaction_id = rm.bank_transaction_id
                WHERE rm.reconciliation_match_id = ?
                """,
                (reconciliation_match_id,),
            ).fetchone()

            if row is None:
                return None

            links = _load_reconciliation_links(
                connection,
                [reconciliation_match_id],
            )
        finally:
            connection.close()
    except sqlite3.Error:
        return None

    match = dict(row)
    explanation = parse_explanation_json(
        str(match.get("explanation_json") or "")
    )
    match["explanation"] = explanation
    match["explanation_summary"] = explanation["summary"]
    match["ledger_links"] = links
    match["ledger_link_count"] = len(links)
    return match


def _latest_corrections_by_bank_transaction(
    connection: sqlite3.Connection,
) -> dict[str, dict[str, object]]:
    if not _table_exists(connection, "category_corrections"):
        return {}

    rows = connection.execute(
        """
        SELECT
            correction_id,
            bank_transaction_id,
            corrected_category,
            corrected_by,
            reason,
            corrected_at,
            created_at
        FROM category_corrections
        ORDER BY
            bank_transaction_id ASC,
            corrected_at DESC,
            created_at DESC,
            correction_id DESC
        """
    ).fetchall()

    latest: dict[str, dict[str, object]] = {}
    for row in rows:
        correction = dict(row)
        bank_transaction_id = str(correction["bank_transaction_id"])
        latest.setdefault(bank_transaction_id, correction)
    return latest


def _bank_transactions_for_review(
    connection: sqlite3.Connection,
) -> list[dict[str, object]]:
    if not _table_exists(connection, "bank_transactions"):
        return []

    rows = connection.execute(
        """
        SELECT
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
        FROM bank_transactions
        ORDER BY
            transaction_date ASC,
            bank_transaction_id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _friendly_reason(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "No reason provided"


def load_categorization_review_rows(
    db_path: str | Path,
) -> list[dict[str, object]]:
    """Load bank transactions with read-only category review details."""
    if not database_exists(db_path):
        return []

    try:
        connection = connect(db_path)
        try:
            transactions = _bank_transactions_for_review(connection)
            corrections = _latest_corrections_by_bank_transaction(connection)
        finally:
            connection.close()
    except sqlite3.Error:
        return []

    rules = default_category_rules()
    review_rows: list[dict[str, object]] = []
    for transaction in transactions:
        result = categorize_transaction(transaction, rules)
        bank_transaction_id = str(transaction["bank_transaction_id"])
        correction = corrections.get(bank_transaction_id)

        category = result.get("category")
        category_source = result.get("category_source")
        category_rule_id = result.get("category_rule_id")
        category_reason = result.get("category_reason")
        correction_id = None
        correction_reason = None
        corrected_at = None

        if correction is not None:
            category = correction["corrected_category"]
            category_source = "correction"
            correction_id = correction["correction_id"]
            correction_reason = correction.get("reason")
            corrected_at = correction["corrected_at"]
        elif category is None:
            category_source = "uncategorized"

        review_rows.append(
            {
                "bank_transaction_id": bank_transaction_id,
                "transaction_date": transaction["transaction_date"],
                "description_raw": transaction["description_raw"],
                "description_normalized": transaction[
                    "description_normalized"
                ],
                "amount_cents": transaction["amount_cents"],
                "amount": format_cents_for_dashboard(
                    _object_to_int(transaction["amount_cents"], "amount_cents")
                ),
                "duplicate_group_id": transaction.get("duplicate_group_id"),
                "category": category,
                "category_source": category_source,
                "category_rule_id": category_rule_id,
                "category_reason": _friendly_reason(category_reason),
                "correction_id": correction_id,
                "correction_reason": _friendly_reason(correction_reason),
                "corrected_at": corrected_at,
                "classifier_confidence": None,
            }
        )

    return review_rows


def load_category_correction_summary(
    db_path: str | Path,
) -> dict[str, object]:
    """Load read-only category correction counts."""
    if not database_exists(db_path):
        return {
            "correction_table_exists": False,
            "correction_count": 0,
            "corrected_transaction_count": 0,
        }

    try:
        connection = connect(db_path)
        try:
            if not _table_exists(connection, "category_corrections"):
                return {
                    "correction_table_exists": False,
                    "correction_count": 0,
                    "corrected_transaction_count": 0,
                }

            counts = connection.execute(
                """
                SELECT
                    COUNT(*) AS correction_count,
                    COUNT(DISTINCT bank_transaction_id)
                        AS corrected_transaction_count
                FROM category_corrections
                """
            ).fetchone()
        finally:
            connection.close()
    except sqlite3.Error:
        return {
            "correction_table_exists": False,
            "correction_count": 0,
            "corrected_transaction_count": 0,
        }

    return {
        "correction_table_exists": True,
        "correction_count": int(counts["correction_count"]),
        "corrected_transaction_count": int(
            counts["corrected_transaction_count"]
        ),
    }


def load_categorization_review(db_path: str | Path) -> dict[str, object]:
    """Load read-only categorization review rows and summary metrics."""
    if not database_exists(db_path):
        return {
            "available": False,
            "message": "Database does not exist.",
            "rows": [],
            "summary": {
                "total_bank_transactions": 0,
                "categorized_count": 0,
                "uncategorized_count": 0,
                "rule_based_count": 0,
                "correction_based_count": 0,
                "classifier_based_count": 0,
                "duplicate_flagged_count": 0,
                "classifier_used": False,
            },
        }

    rows = load_categorization_review_rows(db_path)
    total = len(rows)
    rule_count = sum(1 for row in rows if row["category_source"] == "rule")
    correction_count = sum(
        1 for row in rows
        if row["category_source"] == "correction"
    )
    classifier_count = sum(
        1 for row in rows
        if row["category_source"] == "classifier"
    )
    categorized_count = sum(1 for row in rows if row["category"] is not None)
    duplicate_count = sum(
        1 for row in rows
        if row.get("duplicate_group_id") is not None
    )

    return {
        "available": True,
        "message": "" if rows else "No bank transactions are available yet.",
        "rows": rows,
        "summary": {
            "total_bank_transactions": total,
            "categorized_count": categorized_count,
            "uncategorized_count": total - categorized_count,
            "rule_based_count": rule_count,
            "correction_based_count": correction_count,
            "classifier_based_count": classifier_count,
            "duplicate_flagged_count": duplicate_count,
            "classifier_used": classifier_count > 0,
        },
        "correction_summary": load_category_correction_summary(db_path),
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
    values: object,
    keys: tuple[str, ...],
) -> None:
    values = _report_dict(values)
    columns[index].metric(
        label,
        format_cents_for_dashboard(_first_existing_int(values, keys)),
    )


def _metric_bool(
    columns: Any,
    index: int,
    label: str,
    values: object,
    keys: tuple[str, ...],
) -> None:
    values = _report_dict(values)
    value = _first_existing_value(values, keys)
    columns[index].metric(
        label,
        format_bool_status(_object_to_bool(value, keys[0])),
    )


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
    metric_columns[0].metric("Ledger events", _metric_value(summary["ledger_events"]))
    metric_columns[1].metric("Accounts", _metric_value(summary["accounts"]))
    metric_columns[2].metric(
        "Journal entries",
        _metric_value(summary["posted_journal_entries"]),
    )
    metric_columns[3].metric(
        "Bank transactions",
        _metric_value(summary["imported_bank_transactions"]),
    )

    second_metric_columns = st.columns(4)
    second_metric_columns[0].metric(
        "Reconciliation runs",
        _metric_value(summary["reconciliation_runs"]),
    )
    second_metric_columns[1].metric(
        "Trial balance balanced",
        format_bool_status(
            _object_to_bool(
                summary["trial_balance_balanced"],
                "trial_balance_balanced",
            )
        ),
    )
    second_metric_columns[2].metric(
        "Cash ending balance",
        _metric_value(summary["cash_ending_balance"]),
    )
    second_metric_columns[3].metric(
        "Cash flow tie",
        _metric_value(summary["cash_flow_tie_status"]),
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

    rows = _report_rows(report.get("rows"))
    totals = _report_dict(report.get("totals"))

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
                    _object_to_int(row["debit_total_cents"], "debit_total_cents")
                ),
                "credit_total": format_cents_for_dashboard(
                    _object_to_int(row["credit_total_cents"], "credit_total_cents")
                ),
                "ending_debit_balance": format_cents_for_dashboard(
                    _object_to_int(
                        row["ending_debit_balance_cents"],
                        "ending_debit_balance_cents",
                    )
                ),
                "ending_credit_balance": format_cents_for_dashboard(
                    _object_to_int(
                        row["ending_credit_balance_cents"],
                        "ending_credit_balance_cents",
                    )
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

    rows = _report_rows(report.get("rows"))
    totals = _report_dict(report.get("totals"))

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

    rows = _report_rows(report.get("rows"))
    totals = _report_dict(report.get("totals"))

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

    rows = _report_rows(report.get("rows"))
    totals = _report_dict(report.get("totals"))

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



def render_bank_reconciliation_page(db_path: str | Path) -> None:
    """Render read-only reconciliation review data."""
    import streamlit as st

    st.header("Bank Reconciliation")
    review = load_reconciliation_review(db_path)

    if not review["available"] and not review["runs"]:
        st.info(str(review["message"]))
        return

    runs = _report_rows(review.get("runs"))
    if not runs:
        st.info("No reconciliation runs are available yet.")
        return

    run_ids = [str(run["reconciliation_run_id"]) for run in runs]
    selected_run_id = st.selectbox(
        "Reconciliation run",
        run_ids,
        index=0,
    )
    review = load_reconciliation_review(db_path, selected_run_id)
    selected_run = review["selected_run"]

    if isinstance(selected_run, dict):
        st.subheader("Selected run")
        run_columns = st.columns(4)
        run_columns[0].metric("Run status", selected_run["status"])
        run_columns[1].metric("Cash account", selected_run["cash_account_id"])
        run_columns[2].metric(
            "Statement start",
            selected_run["statement_start_date"],
        )
        run_columns[3].metric(
            "Statement end",
            selected_run["statement_end_date"],
        )
        st.caption(
            "Started: "
            f"{selected_run.get('started_at')} | Completed: "
            f"{selected_run.get('completed_at')}"
        )
        with st.expander("Run configuration JSON"):
            st.json(selected_run.get("config") or {})

    matches = _report_rows(review.get("matches"))
    if not matches:
        st.info("No reconciliation matches are available for this run yet.")
        return

    st.subheader("Match review")
    display_rows = []
    for match in matches:
        display_rows.append(
            {
                "reconciliation_match_id": match[
                    "reconciliation_match_id"
                ],
                "bank_transaction_id": match["bank_transaction_id"],
                "bank_transaction_date": match["bank_transaction_date"],
                "raw_description": match["bank_description_raw"],
                "normalized_description": match[
                    "bank_description_normalized"
                ],
                "bank_amount": match["bank_amount"],
                "match_type": match["match_type"],
                "match_status": match["match_status"],
                "score": match["score"],
                "amount_delta": match["amount_delta"],
                "date_delta_days": match["date_delta_days"],
                "ledger_link_count": match["ledger_link_count"],
                "journal_entry_ids": ", ".join(
                    _object_to_str_list(
                        match["matched_ledger_journal_entry_ids"],
                        "matched_ledger_journal_entry_ids",
                    )
                ),
                "journal_line_ids": ", ".join(
                    _object_to_str_list(
                        match["matched_ledger_journal_line_ids"],
                        "matched_ledger_journal_line_ids",
                    )
                ),
                "explanation_summary": match["explanation_summary"],
            }
        )
    st.table(display_rows)

    st.subheader("Match explanations and ledger links")
    links_by_match = _links_by_match(_report_rows(review.get("ledger_links")))
    for match in matches:
        match_id = str(match["reconciliation_match_id"])
        label = f"{match_id} — {match['match_status']}"
        with st.expander(label):
            explanation = match.get("explanation", {})
            if isinstance(explanation, dict):
                st.write(explanation.get("summary"))
                parsed = explanation.get("parsed")
                if parsed is not None:
                    st.json(parsed)
                else:
                    st.code(
                        str(explanation.get("raw") or ""),
                        language="json",
                    )

            match_links = links_by_match.get(match_id, [])
            if match_links:
                st.write("Linked ledger movements")
                st.table(rows_to_display_rows(match_links))
            else:
                st.info("No ledger links are stored for this match.")


def render_categorization_review_page(db_path: str | Path) -> None:
    """Render read-only categorization review data."""
    import streamlit as st

    st.header("Categorization Review")
    review = load_categorization_review(db_path)

    if not review["available"]:
        st.info(str(review["message"]))
        return

    summary = _report_dict(review.get("summary"))
    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Bank transactions",
        _metric_value(summary["total_bank_transactions"]),
    )
    metric_columns[1].metric("Categorized", _metric_value(summary["categorized_count"]))
    metric_columns[2].metric(
        "Uncategorized",
        _metric_value(summary["uncategorized_count"]),
    )
    metric_columns[3].metric(
        "Duplicate flagged",
        _metric_value(summary["duplicate_flagged_count"]),
    )

    second_metric_columns = st.columns(4)
    second_metric_columns[0].metric("Rule", _metric_value(summary["rule_based_count"]))
    second_metric_columns[1].metric(
        "Correction",
        _metric_value(summary["correction_based_count"]),
    )
    second_metric_columns[2].metric(
        "Classifier",
        _metric_value(summary["classifier_based_count"]),
    )
    second_metric_columns[3].metric(
        "Classifier used",
        format_bool_status(bool(summary.get("classifier_used"))),
    )

    rows = _report_rows(review.get("rows"))
    if not rows:
        st.info("No imported bank transactions are available yet.")
        return

    display_rows = []
    for row in rows:
        display_rows.append(
            {
                "bank_transaction_id": row["bank_transaction_id"],
                "transaction_date": row["transaction_date"],
                "raw_description": row["description_raw"],
                "normalized_description": row["description_normalized"],
                "amount": row["amount"],
                "duplicate_group_id": row["duplicate_group_id"],
                "category": row["category"],
                "category_source": row["category_source"],
                "category_rule_id": row["category_rule_id"],
                "category_reason": row["category_reason"],
                "correction_id": row["correction_id"],
                "corrected_at": row["corrected_at"],
                "classifier_confidence": row["classifier_confidence"],
            }
        )
    st.table(display_rows)

    with st.expander("Correction summary"):
        st.json(review.get("correction_summary") or {})

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
    elif selected_page == PAGE_BANK_RECONCILIATION:
        render_bank_reconciliation_page(db_path)
    elif selected_page == PAGE_CATEGORIZATION_REVIEW:
        render_categorization_review_page(db_path)


if __name__ == "__main__":
    main()

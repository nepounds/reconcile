"""CSV export helpers for Reconcile reports."""

from __future__ import annotations

import csv
import sqlite3
from datetime import date, datetime
from pathlib import Path

from reconcile.exceptions import ValidationError
from reconcile.reports.balance_sheet import generate_balance_sheet
from reconcile.reports.cash_flow import (
    cash_flow_totals,
    generate_cash_flow_statement,
)
from reconcile.reports.income_statement import generate_income_statement
from reconcile.reports.trial_balance import (
    generate_trial_balance,
    trial_balance_totals,
)

TRIAL_BALANCE_FILENAME = "trial_balance.csv"
INCOME_STATEMENT_FILENAME = "income_statement.csv"
BALANCE_SHEET_FILENAME = "balance_sheet.csv"
CASH_FLOW_FILENAME = "cash_flow.csv"
RECONCILIATION_RESULTS_FILENAME = "reconciliation_results.csv"

TRIAL_BALANCE_COLUMNS = [
    "account_id",
    "account_code",
    "account_name",
    "account_type",
    "normal_balance",
    "debit_total_cents",
    "credit_total_cents",
    "ending_debit_balance_cents",
    "ending_credit_balance_cents",
]

INCOME_STATEMENT_COLUMNS = [
    "section",
    "account_id",
    "account_code",
    "account_name",
    "account_type",
    "amount_cents",
]

BALANCE_SHEET_COLUMNS = [
    "section",
    "account_id",
    "account_code",
    "account_name",
    "account_type",
    "amount_cents",
]

RECONCILIATION_RESULTS_COLUMNS = [
    "reconciliation_run_id",
    "reconciliation_match_id",
    "bank_transaction_id",
    "bank_transaction_date",
    "bank_description_raw",
    "bank_description_normalized",
    "bank_amount_cents",
    "match_type",
    "status",
    "score",
    "amount_delta_cents",
    "date_delta_days",
    "ledger_link_count",
    "ledger_entry_ids",
    "ledger_line_ids",
    "ledger_amount_cents",
    "explanation_json",
]

CASH_FLOW_COLUMNS = [
    "section",
    "journal_entry_id",
    "entry_date",
    "description",
    "cash_account_id",
    "cash_account_code",
    "cash_account_name",
    "cash_line_id",
    "cash_side",
    "cash_amount_cents",
    "cash_flow_amount_cents",
    "counterparty_account_id",
    "counterparty_account_code",
    "counterparty_account_name",
    "counterparty_account_type",
    "counterparty_line_id",
    "counterparty_side",
    "counterparty_amount_cents",
    "classification_reason",
]


def export_trial_balance_csv(
    connection: sqlite3.Connection,
    output_path: str | Path,
) -> dict[str, object]:
    """Export trial balance rows to a CSV file."""
    rows = generate_trial_balance(connection)
    totals = trial_balance_totals(rows)

    csv_rows = [
        {
            "account_id": row["account_id"],
            "account_code": row["account_code"],
            "account_name": row["account_name"],
            "account_type": row["account_type"],
            "normal_balance": row["normal_balance"],
            "debit_total_cents": row["debit_total_cents"],
            "credit_total_cents": row["credit_total_cents"],
            "ending_debit_balance_cents": row["ending_debit_balance_cents"],
            "ending_credit_balance_cents": row["ending_credit_balance_cents"],
        }
        for row in rows
    ]

    path = _write_csv(output_path, TRIAL_BALANCE_COLUMNS, csv_rows)

    return {
        "output_path": str(path),
        "row_count": len(csv_rows),
        "total_debit_balance_cents": totals[
            "total_ending_debit_balance_cents"
        ],
        "total_credit_balance_cents": totals[
            "total_ending_credit_balance_cents"
        ],
        "is_balanced": totals["is_balanced"],
    }


def export_income_statement_csv(
    connection: sqlite3.Connection,
    *,
    start_date: date,
    end_date: date,
    output_path: str | Path,
) -> dict[str, object]:
    """Export income statement rows to a CSV file."""
    _validate_date(start_date, "start_date")
    _validate_date(end_date, "end_date")

    if start_date > end_date:
        raise ValidationError("start_date must be less than or equal to end_date")

    report = generate_income_statement(
        connection,
        start_date=start_date,
        end_date=end_date,
    )

    csv_rows = [
        *_income_statement_section_rows("revenue", report["revenue_accounts"]),
        *_income_statement_section_rows("expense", report["expense_accounts"]),
    ]

    path = _write_csv(output_path, INCOME_STATEMENT_COLUMNS, csv_rows)

    return {
        "output_path": str(path),
        "row_count": len(csv_rows),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_revenue_cents": report["total_revenue_cents"],
        "total_expense_cents": report["total_expenses_cents"],
        "net_income_cents": report["net_income_cents"],
    }


def export_balance_sheet_csv(
    connection: sqlite3.Connection,
    *,
    as_of_date: date,
    output_path: str | Path,
) -> dict[str, object]:
    """Export balance sheet rows to a CSV file."""
    _validate_date(as_of_date, "as_of_date")

    report = generate_balance_sheet(connection, as_of_date=as_of_date)

    csv_rows = [
        *_balance_sheet_section_rows("asset", report["asset_accounts"]),
        *_balance_sheet_section_rows("liability", report["liability_accounts"]),
        *_balance_sheet_section_rows("equity", report["equity_accounts"]),
        {
            "section": "equity",
            "account_id": "",
            "account_code": "",
            "account_name": "Current Period Net Income",
            "account_type": "equity",
            "amount_cents": report["current_period_net_income_cents"],
        },
    ]

    path = _write_csv(output_path, BALANCE_SHEET_COLUMNS, csv_rows)

    return {
        "output_path": str(path),
        "row_count": len(csv_rows),
        "as_of_date": as_of_date.isoformat(),
        "total_assets_cents": report["total_assets_cents"],
        "total_liabilities_cents": report["total_liabilities_cents"],
        "total_equity_cents": report["total_equity_cents"],
        "total_liabilities_and_equity_cents": report[
            "total_liabilities_and_equity_cents"
        ],
        "is_balanced": report["is_balanced"],
    }


def export_reconciliation_results_csv(
    connection: sqlite3.Connection,
    *,
    reconciliation_run_id: str,
    output_path: str | Path,
) -> dict[str, object]:
    """Export reconciliation match rows to a CSV file."""
    run_id = _validate_nonblank(reconciliation_run_id, "reconciliation_run_id")
    _ensure_reconciliation_run_exists(connection, run_id)

    rows = _load_reconciliation_rows(connection, run_id)
    path = _write_csv(output_path, RECONCILIATION_RESULTS_COLUMNS, rows)

    auto_matched_count = 0
    candidate_count = 0
    ambiguous_count = 0
    unmatched_count = 0

    for row in rows:
        status = row["status"]
        if status == "auto_matched":
            auto_matched_count += 1
        elif status == "candidate":
            candidate_count += 1
        elif status == "ambiguous":
            ambiguous_count += 1
        elif status == "unmatched":
            unmatched_count += 1

    return {
        "output_path": str(path),
        "row_count": len(rows),
        "reconciliation_run_id": run_id,
        "auto_matched_count": auto_matched_count,
        "candidate_count": candidate_count,
        "ambiguous_count": ambiguous_count,
        "unmatched_count": unmatched_count,
    }


def export_all_reports(
    connection: sqlite3.Connection,
    *,
    output_dir: str | Path,
    income_start_date: date,
    income_end_date: date,
    balance_sheet_as_of_date: date,
    reconciliation_run_id: str | None = None,
) -> dict[str, object]:
    """Export all implemented CSV reports to an output directory."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    trial_balance = export_trial_balance_csv(
        connection,
        directory / TRIAL_BALANCE_FILENAME,
    )
    income_statement = export_income_statement_csv(
        connection,
        start_date=income_start_date,
        end_date=income_end_date,
        output_path=directory / INCOME_STATEMENT_FILENAME,
    )
    balance_sheet = export_balance_sheet_csv(
        connection,
        as_of_date=balance_sheet_as_of_date,
        output_path=directory / BALANCE_SHEET_FILENAME,
    )
    cash_flow = export_cash_flow_csv(
        connection,
        start_date=income_start_date,
        end_date=income_end_date,
        output_path=directory / CASH_FLOW_FILENAME,
    )

    if reconciliation_run_id is None:
        reconciliation_results: dict[str, object] = {
            "skipped": True,
            "reason": "No reconciliation_run_id provided.",
            "output_path": None,
            "row_count": 0,
        }
    else:
        reconciliation_results = export_reconciliation_results_csv(
            connection,
            reconciliation_run_id=reconciliation_run_id,
            output_path=directory / RECONCILIATION_RESULTS_FILENAME,
        )
        reconciliation_results["skipped"] = False

    return {
        "output_dir": str(directory),
        "trial_balance": trial_balance,
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "reconciliation_results": reconciliation_results,
    }


def export_cash_flow_csv(
    connection: sqlite3.Connection,
    *,
    start_date: date,
    end_date: date,
    output_path: str | Path,
    cash_account_id: str | None = None,
) -> dict[str, object]:
    """Export direct-method cash flow section rows to a CSV file."""
    statement = generate_cash_flow_statement(
        connection,
        start_date=start_date,
        end_date=end_date,
        cash_account_id=cash_account_id,
    )

    sections = statement["sections"]
    if not isinstance(sections, dict):
        raise ValidationError("Cash flow statement sections are malformed.")

    rows: list[dict[str, object]] = []
    for section in ("operating", "investing", "financing"):
        section_rows = sections.get(section, [])
        if not isinstance(section_rows, list):
            raise ValidationError(f"Cash flow section is malformed: {section}.")
        rows.extend(section_rows)

    path = _write_csv(output_path, CASH_FLOW_COLUMNS, rows)
    totals = cash_flow_totals(statement)

    return {
        "output_path": str(path),
        "row_count": len(rows),
        "start_date": statement["start_date"],
        "end_date": statement["end_date"],
        "operating_cash_flow_cents": totals["operating_cash_flow_cents"],
        "investing_cash_flow_cents": totals["investing_cash_flow_cents"],
        "financing_cash_flow_cents": totals["financing_cash_flow_cents"],
        "net_cash_change_cents": totals["net_cash_change_cents"],
        "beginning_cash_cents": totals["beginning_cash_cents"],
        "ending_cash_cents": totals["ending_cash_cents"],
        "cash_balances_tie": totals["cash_balances_tie"],
    }


def _income_statement_section_rows(
    section: str,
    rows: object,
) -> list[dict[str, object]]:
    if not isinstance(rows, list):
        raise ValidationError(f"{section} rows must be a list")

    return [
        {
            "section": section,
            "account_id": row["account_id"],
            "account_code": row["account_code"],
            "account_name": row["account_name"],
            "account_type": row["account_type"],
            "amount_cents": row["amount_cents"],
        }
        for row in rows
    ]


def _balance_sheet_section_rows(
    section: str,
    rows: object,
) -> list[dict[str, object]]:
    if not isinstance(rows, list):
        raise ValidationError(f"{section} rows must be a list")

    return [
        {
            "section": section,
            "account_id": row["account_id"],
            "account_code": row["account_code"],
            "account_name": row["account_name"],
            "account_type": row["account_type"],
            "amount_cents": row["balance_cents"],
        }
        for row in rows
    ]


def _load_reconciliation_rows(
    connection: sqlite3.Connection,
    reconciliation_run_id: str,
) -> list[dict[str, object]]:
    match_rows = connection.execute(
        """
        SELECT
            m.reconciliation_run_id,
            m.reconciliation_match_id,
            m.bank_transaction_id,
            b.transaction_date AS bank_transaction_date,
            b.description_raw AS bank_description_raw,
            b.description_normalized AS bank_description_normalized,
            b.amount_cents AS bank_amount_cents,
            m.match_type,
            m.status,
            m.score,
            m.amount_delta_cents,
            m.date_delta_days,
            m.explanation_json,
            m.created_at
        FROM reconciliation_matches AS m
        JOIN bank_transactions AS b
            ON b.bank_transaction_id = m.bank_transaction_id
        WHERE m.reconciliation_run_id = ?
        ORDER BY
            b.transaction_date,
            b.bank_transaction_id,
            m.created_at,
            m.reconciliation_match_id
        """,
        (reconciliation_run_id,),
    ).fetchall()

    export_rows: list[dict[str, object]] = []

    for row in match_rows:
        links = _load_reconciliation_links(
            connection,
            str(row["reconciliation_match_id"]),
        )

        ledger_entry_ids = ";".join(str(link["journal_entry_id"]) for link in links)
        ledger_line_ids = ";".join(
            str(link["journal_entry_line_id"])
            for link in links
            if link["journal_entry_line_id"] is not None
        )
        ledger_amount_cents = sum(int(link["amount_cents"]) for link in links)

        export_rows.append(
            {
                "reconciliation_run_id": row["reconciliation_run_id"],
                "reconciliation_match_id": row["reconciliation_match_id"],
                "bank_transaction_id": row["bank_transaction_id"],
                "bank_transaction_date": row["bank_transaction_date"],
                "bank_description_raw": row["bank_description_raw"],
                "bank_description_normalized": (
                    row["bank_description_normalized"] or ""
                ),
                "bank_amount_cents": row["bank_amount_cents"],
                "match_type": row["match_type"],
                "status": row["status"],
                "score": row["score"],
                "amount_delta_cents": row["amount_delta_cents"],
                "date_delta_days": (
                    "" if row["date_delta_days"] is None else row["date_delta_days"]
                ),
                "ledger_link_count": len(links),
                "ledger_entry_ids": ledger_entry_ids,
                "ledger_line_ids": ledger_line_ids,
                "ledger_amount_cents": ledger_amount_cents if links else 0,
                "explanation_json": row["explanation_json"],
            }
        )

    return export_rows


def _load_reconciliation_links(
    connection: sqlite3.Connection,
    reconciliation_match_id: str,
) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT
                journal_entry_id,
                journal_entry_line_id,
                amount_cents
            FROM reconciliation_match_ledger_links
            WHERE reconciliation_match_id = ?
            ORDER BY
                journal_entry_id,
                journal_entry_line_id
            """,
            (reconciliation_match_id,),
        ).fetchall()
    )


def _ensure_reconciliation_run_exists(
    connection: sqlite3.Connection,
    reconciliation_run_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT reconciliation_run_id
        FROM reconciliation_runs
        WHERE reconciliation_run_id = ?
        """,
        (reconciliation_run_id,),
    ).fetchone()

    if row is None:
        raise ValidationError(
            f"reconciliation_run_id does not exist: {reconciliation_run_id}"
        )


def _write_csv(
    output_path: str | Path,
    columns: list[str],
    rows: list[dict[str, object]],
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    return path


def _validate_date(value: date, field_name: str) -> None:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValidationError(f"{field_name} must be a datetime.date instance")


def _validate_nonblank(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a nonblank string")
    return value.strip()

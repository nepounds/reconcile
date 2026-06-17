"""Income statement report generation for Reconcile."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any

from reconcile.accounts.models import validate_account_type
from reconcile.exceptions import ValidationError

_VALID_LINE_SIDES = {"debit", "credit"}


def _validate_report_date(value: date, field_name: str) -> None:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValidationError(f"{field_name} must be a datetime.date instance")


def _validate_line_side(side: str) -> None:
    if side not in _VALID_LINE_SIDES:
        raise ValidationError(f"invalid journal line side: {side!r}")


def income_statement_totals(rows: list[dict[str, int | str]]) -> dict[str, int]:
    """Calculate income statement totals from report account rows."""
    total_revenue_cents = 0
    total_expenses_cents = 0

    for row in rows:
        account_type = str(row["account_type"])
        validate_account_type(account_type)

        amount_cents = row["amount_cents"]
        if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
            raise ValidationError("amount_cents must be an integer")

        if account_type == "revenue":
            total_revenue_cents += amount_cents
        elif account_type == "expense":
            total_expenses_cents += amount_cents
        else:
            raise ValidationError(
                "income statement rows must be revenue or expense accounts"
            )

    return {
        "total_revenue_cents": total_revenue_cents,
        "total_expenses_cents": total_expenses_cents,
        "net_income_cents": total_revenue_cents - total_expenses_cents,
    }


def generate_income_statement(
    connection: sqlite3.Connection,
    *,
    start_date: date,
    end_date: date,
) -> dict[str, object]:
    """Generate income statement data for an inclusive date range."""
    _validate_report_date(start_date, "start_date")
    _validate_report_date(end_date, "end_date")

    if start_date > end_date:
        raise ValidationError("start_date must be less than or equal to end_date")

    rows = connection.execute(
        """
        SELECT
            accounts.account_id,
            accounts.code AS account_code,
            accounts.name AS account_name,
            accounts.account_type,
            journal_entry_lines.side,
            SUM(journal_entry_lines.amount_cents) AS amount_cents
        FROM journal_entries
        JOIN journal_entry_lines
            ON journal_entry_lines.journal_entry_id =
                journal_entries.journal_entry_id
        JOIN accounts
            ON accounts.account_id = journal_entry_lines.account_id
        WHERE
            journal_entries.status = 'posted'
            AND journal_entries.entry_date >= ?
            AND journal_entries.entry_date <= ?
            AND accounts.account_type IN ('revenue', 'expense')
        GROUP BY
            accounts.account_id,
            accounts.code,
            accounts.name,
            accounts.account_type,
            journal_entry_lines.side
        ORDER BY
            accounts.code,
            accounts.account_id
        """,
        (start_date.isoformat(), end_date.isoformat()),
    ).fetchall()

    account_activity: dict[str, dict[str, Any]] = {}

    for row in rows:
        account_type = row["account_type"]
        validate_account_type(account_type)

        if account_type not in {"revenue", "expense"}:
            raise ValidationError(
                "income statement can only include revenue and expense accounts"
            )

        side = row["side"]
        _validate_line_side(side)

        amount_cents = row["amount_cents"]
        if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
            raise ValidationError("journal line amount must be an integer")

        account_id = row["account_id"]
        activity = account_activity.setdefault(
            account_id,
            {
                "account_id": account_id,
                "account_code": row["account_code"],
                "account_name": row["account_name"],
                "account_type": account_type,
                "debit_total_cents": 0,
                "credit_total_cents": 0,
            },
        )

        if side == "debit":
            activity["debit_total_cents"] += amount_cents
        else:
            activity["credit_total_cents"] += amount_cents

    revenue_accounts: list[dict[str, int | str]] = []
    expense_accounts: list[dict[str, int | str]] = []

    for activity in account_activity.values():
        account_type = str(activity["account_type"])
        debit_total = int(activity["debit_total_cents"])
        credit_total = int(activity["credit_total_cents"])

        if debit_total == 0 and credit_total == 0:
            continue

        if account_type == "revenue":
            amount_cents = credit_total - debit_total
            revenue_accounts.append(
                {
                    "account_id": str(activity["account_id"]),
                    "account_code": str(activity["account_code"]),
                    "account_name": str(activity["account_name"]),
                    "account_type": account_type,
                    "amount_cents": amount_cents,
                }
            )
        elif account_type == "expense":
            amount_cents = debit_total - credit_total
            expense_accounts.append(
                {
                    "account_id": str(activity["account_id"]),
                    "account_code": str(activity["account_code"]),
                    "account_name": str(activity["account_name"]),
                    "account_type": account_type,
                    "amount_cents": amount_cents,
                }
            )
        else:
            raise ValidationError(
                f"invalid income statement account type: {account_type}"
            )

    revenue_accounts.sort(
        key=lambda row: (str(row["account_code"]), str(row["account_id"]))
    )
    expense_accounts.sort(
        key=lambda row: (str(row["account_code"]), str(row["account_id"]))
    )

    totals = income_statement_totals(revenue_accounts + expense_accounts)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "revenue_accounts": revenue_accounts,
        "expense_accounts": expense_accounts,
        "total_revenue_cents": totals["total_revenue_cents"],
        "total_expenses_cents": totals["total_expenses_cents"],
        "net_income_cents": totals["net_income_cents"],
    }
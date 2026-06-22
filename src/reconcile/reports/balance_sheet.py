"""Balance sheet report generation for Reconcile."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import TypedDict

from reconcile.accounts.models import validate_account_type, validate_normal_balance
from reconcile.exceptions import ValidationError

_VALID_LINE_SIDES = {"debit", "credit"}
_BALANCE_SHEET_ACCOUNT_TYPES = {"asset", "liability", "equity"}


class _BalanceSheetAccount(TypedDict):
    account_id: str
    account_code: str
    account_name: str
    account_type: str
    normal_balance: str
    debit_total_cents: int
    credit_total_cents: int


def _validate_report_date(value: date, field_name: str) -> None:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValidationError(f"{field_name} must be a datetime.date instance")


def _validate_line_side(side: str) -> None:
    if side not in _VALID_LINE_SIDES:
        raise ValidationError(f"invalid journal line side: {side!r}")


def _normal_balance_amount(
    *,
    normal_balance: str,
    debit_total_cents: int,
    credit_total_cents: int,
) -> int:
    if normal_balance == "debit":
        return debit_total_cents - credit_total_cents
    if normal_balance == "credit":
        return credit_total_cents - debit_total_cents

    raise ValidationError(f"invalid normal balance: {normal_balance!r}")


def _net_income_through_date(
    connection: sqlite3.Connection,
    *,
    as_of_date: date,
) -> int:
    rows = connection.execute(
        """
        SELECT
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
            AND journal_entries.entry_date <= ?
            AND accounts.account_type IN ('revenue', 'expense')
        GROUP BY
            accounts.account_type,
            journal_entry_lines.side
        """,
        (as_of_date.isoformat(),),
    ).fetchall()

    revenue_debits = 0
    revenue_credits = 0
    expense_debits = 0
    expense_credits = 0

    for row in rows:
        account_type = str(row["account_type"])
        validate_account_type(account_type)

        side = str(row["side"])
        _validate_line_side(side)

        amount_cents = row["amount_cents"]
        if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
            raise ValidationError("journal line amount must be an integer")

        if account_type == "revenue":
            if side == "debit":
                revenue_debits += amount_cents
            else:
                revenue_credits += amount_cents
        elif account_type == "expense":
            if side == "debit":
                expense_debits += amount_cents
            else:
                expense_credits += amount_cents
        else:
            raise ValidationError(
                "net income can only include revenue and expense accounts"
            )

    total_revenue_cents = revenue_credits - revenue_debits
    total_expenses_cents = expense_debits - expense_credits

    return total_revenue_cents - total_expenses_cents


def generate_balance_sheet(
    connection: sqlite3.Connection,
    *,
    as_of_date: date,
) -> dict[str, object]:
    """Generate balance sheet data as of a specific accounting date."""
    _validate_report_date(as_of_date, "as_of_date")

    account_rows = connection.execute(
        """
        SELECT
            account_id,
            code AS account_code,
            name AS account_name,
            account_type,
            normal_balance
        FROM accounts
        ORDER BY code, account_id
        """
    ).fetchall()

    account_data: dict[str, _BalanceSheetAccount] = {}

    for row in account_rows:
        account_type = str(row["account_type"])
        normal_balance = str(row["normal_balance"])

        validate_account_type(account_type)
        validate_normal_balance(normal_balance)

        if account_type in _BALANCE_SHEET_ACCOUNT_TYPES:
            account_id = str(row["account_id"])
            account_data[account_id] = {
                "account_id": account_id,
                "account_code": str(row["account_code"]),
                "account_name": str(row["account_name"]),
                "account_type": str(account_type),
                "normal_balance": str(normal_balance),
                "debit_total_cents": 0,
                "credit_total_cents": 0,
            }

    activity_rows = connection.execute(
        """
        SELECT
            accounts.account_id,
            accounts.account_type,
            accounts.normal_balance,
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
            AND journal_entries.entry_date <= ?
        GROUP BY
            accounts.account_id,
            accounts.account_type,
            accounts.normal_balance,
            journal_entry_lines.side
        ORDER BY
            accounts.code,
            accounts.account_id
        """,
        (as_of_date.isoformat(),),
    ).fetchall()

    for row in activity_rows:
        account_type = str(row["account_type"])
        normal_balance = str(row["normal_balance"])

        validate_account_type(account_type)
        validate_normal_balance(normal_balance)

        side = str(row["side"])
        _validate_line_side(side)

        amount_cents = row["amount_cents"]
        if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
            raise ValidationError("journal line amount must be an integer")

        if account_type not in _BALANCE_SHEET_ACCOUNT_TYPES:
            continue

        account_id = str(row["account_id"])
        if account_id not in account_data:
            raise ValidationError(f"balance sheet account is missing: {account_id}")

        if side == "debit":
            account_data[account_id]["debit_total_cents"] += amount_cents
        else:
            account_data[account_id]["credit_total_cents"] += amount_cents

    asset_accounts: list[dict[str, int | str]] = []
    liability_accounts: list[dict[str, int | str]] = []
    equity_accounts: list[dict[str, int | str]] = []

    for account in account_data.values():
        balance_cents = _normal_balance_amount(
            normal_balance=account["normal_balance"],
            debit_total_cents=account["debit_total_cents"],
            credit_total_cents=account["credit_total_cents"],
        )

        report_row: dict[str, int | str] = {
            "account_id": account["account_id"],
            "account_code": account["account_code"],
            "account_name": account["account_name"],
            "account_type": account["account_type"],
            "balance_cents": balance_cents,
        }

        if account["account_type"] == "asset":
            asset_accounts.append(report_row)
        elif account["account_type"] == "liability":
            liability_accounts.append(report_row)
        elif account["account_type"] == "equity":
            equity_accounts.append(report_row)
        else:
            raise ValidationError(
                f"invalid balance sheet account type: {account['account_type']}"
            )

    asset_accounts.sort(
        key=lambda row: (str(row["account_code"]), str(row["account_id"]))
    )
    liability_accounts.sort(
        key=lambda row: (str(row["account_code"]), str(row["account_id"]))
    )
    equity_accounts.sort(
        key=lambda row: (str(row["account_code"]), str(row["account_id"]))
    )

    current_period_net_income_cents = _net_income_through_date(
        connection,
        as_of_date=as_of_date,
    )

    total_assets_cents = sum(int(row["balance_cents"]) for row in asset_accounts)
    total_liabilities_cents = sum(
        int(row["balance_cents"]) for row in liability_accounts
    )
    base_equity_cents = sum(int(row["balance_cents"]) for row in equity_accounts)
    total_equity_cents = base_equity_cents + current_period_net_income_cents
    total_liabilities_and_equity_cents = (
        total_liabilities_cents + total_equity_cents
    )

    return {
        "as_of_date": as_of_date.isoformat(),
        "asset_accounts": asset_accounts,
        "liability_accounts": liability_accounts,
        "equity_accounts": equity_accounts,
        "current_period_net_income_cents": current_period_net_income_cents,
        "total_assets_cents": total_assets_cents,
        "total_liabilities_cents": total_liabilities_cents,
        "total_equity_cents": total_equity_cents,
        "total_liabilities_and_equity_cents": total_liabilities_and_equity_cents,
        "is_balanced": total_assets_cents == total_liabilities_and_equity_cents,
    }
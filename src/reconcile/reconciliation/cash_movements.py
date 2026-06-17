"""Extract bank-comparable ledger cash movements."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from reconcile.exceptions import ValidationError

VALID_LINE_SIDES = {"debit", "credit"}


def get_cash_account(
    connection: sqlite3.Connection,
    cash_account_id: str,
) -> dict[str, object]:
    """Return and validate the selected cash account."""
    if not isinstance(cash_account_id, str) or not cash_account_id.strip():
        raise ValidationError("cash_account_id must be a nonblank string")

    row = connection.execute(
        """
        SELECT
            account_id,
            code,
            name,
            account_type,
            normal_balance,
            is_active,
            opened_at,
            closed_at
        FROM accounts
        WHERE account_id = ?
        """,
        (cash_account_id,),
    ).fetchone()

    if row is None:
        raise ValidationError(f"cash account does not exist: {cash_account_id}")

    account = dict(row)

    if not isinstance(account["account_id"], str) or not account["account_id"].strip():
        raise ValidationError("cash account has invalid account_id")
    if not isinstance(account["code"], str) or not account["code"].strip():
        raise ValidationError("cash account has invalid code")
    if not isinstance(account["name"], str) or not account["name"].strip():
        raise ValidationError("cash account has invalid name")

    if account["account_type"] != "asset":
        raise ValidationError("cash account must have account_type='asset'")

    if account["normal_balance"] != "debit":
        raise ValidationError("cash account must have normal_balance='debit'")

    return account


def extract_ledger_cash_movements(
    connection: sqlite3.Connection,
    *,
    cash_account_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    include_reversed: bool = False,
) -> list[dict[str, object]]:
    """Extract bank-comparable ledger cash movements for one cash account."""
    _validate_date_range(start_date=start_date, end_date=end_date)
    cash_account = get_cash_account(connection, cash_account_id)

    where_clauses = ["jel.account_id = ?"]
    parameters: list[object] = [cash_account_id]

    if start_date is not None:
        where_clauses.append("je.entry_date >= ?")
        parameters.append(start_date.isoformat())

    if end_date is not None:
        where_clauses.append("je.entry_date <= ?")
        parameters.append(end_date.isoformat())

    if not include_reversed:
        where_clauses.append("je.reversed_by_entry_id IS NULL")
        where_clauses.append("je.reversal_of_entry_id IS NULL")

    where_sql = " AND ".join(where_clauses)

    rows = connection.execute(
        f"""
        SELECT
            je.journal_entry_id,
            jel.line_id AS journal_entry_line_id,
            je.entry_date,
            je.description,
            jel.description AS line_description,
            jel.side,
            jel.amount_cents,
            je.reversal_of_entry_id,
            je.reversed_by_entry_id
        FROM journal_entry_lines AS jel
        INNER JOIN journal_entries AS je
            ON je.journal_entry_id = jel.journal_entry_id
        WHERE {where_sql}
        ORDER BY
            je.entry_date ASC,
            je.journal_entry_id ASC,
            jel.line_id ASC
        """,
        parameters,
    ).fetchall()

    movements: list[dict[str, object]] = []
    for row in rows:
        movement = _build_cash_movement(row=row, cash_account=cash_account)
        movements.append(movement)

    return movements


def _validate_date_range(
    *,
    start_date: date | None,
    end_date: date | None,
) -> None:
    for name, value in (("start_date", start_date), ("end_date", end_date)):
        if value is None:
            continue
        if isinstance(value, datetime) or not isinstance(value, date):
            raise ValidationError(f"{name} must be a datetime.date instance")

    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValidationError("start_date must be on or before end_date")


def _build_cash_movement(
    *,
    row: sqlite3.Row,
    cash_account: dict[str, object],
) -> dict[str, object]:
    side = row["side"]
    amount_cents = row["amount_cents"]

    if side not in VALID_LINE_SIDES:
        raise ValidationError(f"invalid journal line side: {side!r}")

    if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
        raise ValidationError("journal line amount_cents must be an integer")

    if amount_cents <= 0:
        raise ValidationError("journal line amount_cents must be positive")

    signed_amount_cents = amount_cents if side == "debit" else -amount_cents

    journal_entry_line_id = row["journal_entry_line_id"]
    if not isinstance(journal_entry_line_id, str) or not journal_entry_line_id.strip():
        raise ValidationError("journal entry line has invalid line_id")

    entry_date = row["entry_date"]
    if not isinstance(entry_date, str) or not entry_date.strip():
        raise ValidationError("journal entry has invalid entry_date")

    return {
        "ledger_cash_movement_id": f"cashmov-{journal_entry_line_id}",
        "journal_entry_id": row["journal_entry_id"],
        "journal_entry_line_id": journal_entry_line_id,
        "entry_date": entry_date,
        "description": row["description"],
        "line_description": row["line_description"],
        "cash_account_id": cash_account["account_id"],
        "cash_account_code": cash_account["code"],
        "cash_account_name": cash_account["name"],
        "side": side,
        "amount_cents": signed_amount_cents,
        "source": None,
        "external_reference": None,
        "is_reversal": row["reversal_of_entry_id"] is not None,
        "reversal_of_entry_id": row["reversal_of_entry_id"],
        "reversed_by_entry_id": row["reversed_by_entry_id"],
    }
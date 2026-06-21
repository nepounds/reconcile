"""Direct-method cash flow reporting."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any

from reconcile.exceptions import ValidationError

VALID_ACCOUNT_TYPES = {"asset", "liability", "equity", "revenue", "expense"}
VALID_SECTIONS = {"operating", "investing", "financing"}


def generate_cash_flow_statement(
    connection: sqlite3.Connection,
    *,
    start_date: date,
    end_date: date,
    cash_account_id: str | None = None,
) -> dict[str, object]:
    """Generate a direct-method cash flow statement from posted journal activity."""
    _validate_report_dates(start_date, end_date)
    cash_accounts = _cash_accounts(connection, cash_account_id=cash_account_id)
    cash_account_ids = [str(account["account_id"]) for account in cash_accounts]

    beginning_cash_cents = _cash_balance_before(
        connection,
        cash_account_ids,
        start_date,
    )
    ending_cash_cents = _cash_balance_through(
        connection,
        cash_account_ids,
        end_date,
    )
    sections = _cash_movements_by_section(
        connection,
        cash_account_ids,
        start_date,
        end_date,
    )

    statement: dict[str, object] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "cash_account_ids": cash_account_ids,
        "sections": sections,
        "totals": {},
    }
    statement["totals"] = _compute_totals(
        sections,
        beginning_cash_cents=beginning_cash_cents,
        ending_cash_cents=ending_cash_cents,
    )
    return statement


def cash_flow_totals(statement: dict[str, object]) -> dict[str, object]:
    """Return cash flow totals from a generated statement."""
    if not isinstance(statement, dict):
        raise ValidationError("Cash flow statement must be a dictionary.")

    sections = statement.get("sections")
    if not isinstance(sections, dict):
        raise ValidationError("Cash flow statement must include sections.")

    totals = statement.get("totals")
    if not isinstance(totals, dict):
        raise ValidationError("Cash flow statement must include totals.")

    required_total_keys = {
        "beginning_cash_cents",
        "ending_cash_cents",
    }
    missing = required_total_keys - set(totals)
    if missing:
        missing_keys = ", ".join(sorted(missing))
        raise ValidationError(f"Cash flow totals missing keys: {missing_keys}.")

    beginning_cash_cents = _validate_int_field(
        totals["beginning_cash_cents"],
        "beginning_cash_cents",
    )
    ending_cash_cents = _validate_int_field(
        totals["ending_cash_cents"],
        "ending_cash_cents",
    )
    return _compute_totals(
        sections,
        beginning_cash_cents=beginning_cash_cents,
        ending_cash_cents=ending_cash_cents,
    )


def classify_cash_flow_section(
    counterparty_account_type: str,
    counterparty_account_code: str | None = None,
    counterparty_account_name: str | None = None,
) -> str:
    """Classify a cash movement into operating, investing, or financing."""
    if counterparty_account_code is not None and not isinstance(
        counterparty_account_code,
        str,
    ):
        raise ValidationError("Counterparty account code must be a string or None.")
    if counterparty_account_name is not None and not isinstance(
        counterparty_account_name,
        str,
    ):
        raise ValidationError("Counterparty account name must be a string or None.")
    if not isinstance(counterparty_account_type, str):
        raise ValidationError("Counterparty account type must be a string.")

    account_type = counterparty_account_type.strip().lower()
    if account_type not in VALID_ACCOUNT_TYPES:
        raise ValidationError(f"Invalid counterparty account type: {account_type}.")

    if account_type in {"revenue", "expense"}:
        return "operating"
    if account_type == "asset":
        return "investing"
    if account_type in {"liability", "equity"}:
        return "financing"

    raise ValidationError(f"Unsupported counterparty account type: {account_type}.")


def _validate_report_dates(start_date: date, end_date: date) -> None:
    if isinstance(start_date, datetime) or not isinstance(start_date, date):
        raise ValidationError("start_date must be a datetime.date, not datetime.")
    if isinstance(end_date, datetime) or not isinstance(end_date, date):
        raise ValidationError("end_date must be a datetime.date, not datetime.")
    if start_date > end_date:
        raise ValidationError("start_date must be on or before end_date.")


def _cash_accounts(
    connection: sqlite3.Connection,
    cash_account_id: str | None = None,
) -> list[sqlite3.Row]:
    if cash_account_id is not None:
        if not isinstance(cash_account_id, str) or not cash_account_id.strip():
            raise ValidationError("cash_account_id must be a nonblank string.")
        rows = connection.execute(
            """
            SELECT account_id, code, name, account_type, normal_balance
            FROM accounts
            WHERE account_id = ?
            ORDER BY code, account_id
            """,
            (cash_account_id,),
        ).fetchall()
        if not rows:
            raise ValidationError(f"Cash account not found: {cash_account_id}.")
        if not _is_cash_like_account(rows[0]):
            raise ValidationError("Selected account is not cash-like.")
        return list(rows)

    rows = connection.execute(
        """
        SELECT account_id, code, name, account_type, normal_balance
        FROM accounts
        WHERE account_type = 'asset'
          AND normal_balance = 'debit'
        ORDER BY code, account_id
        """,
    ).fetchall()
    return [row for row in rows if _is_cash_like_account(row)]


def _beginning_cash_balance(
    connection: sqlite3.Connection,
    cash_account_ids: list[str],
    start_date: date,
) -> int:
    """Return cash balance immediately before start_date."""
    return _cash_balance_before(connection, cash_account_ids, start_date)


def _ending_cash_balance(
    connection: sqlite3.Connection,
    cash_account_ids: list[str],
    end_date: date,
) -> int:
    """Return cash balance through end_date."""
    return _cash_balance_through(connection, cash_account_ids, end_date)


def _cash_balance_before(
    connection: sqlite3.Connection,
    cash_account_ids: list[str],
    start_date: date,
) -> int:
    if not cash_account_ids:
        return 0
    placeholders = ", ".join("?" for _ in cash_account_ids)
    rows = connection.execute(
        f"""
        SELECT jel.side, jel.amount_cents
        FROM journal_entry_lines AS jel
        JOIN journal_entries AS je
          ON je.journal_entry_id = jel.journal_entry_id
        WHERE jel.account_id IN ({placeholders})
          AND je.status = 'posted'
          AND je.entry_date < ?
        """,
        (*cash_account_ids, start_date.isoformat()),
    ).fetchall()
    return _cash_balance_from_rows(rows)


def _cash_balance_through(
    connection: sqlite3.Connection,
    cash_account_ids: list[str],
    end_date: date,
) -> int:
    if not cash_account_ids:
        return 0
    placeholders = ", ".join("?" for _ in cash_account_ids)
    rows = connection.execute(
        f"""
        SELECT jel.side, jel.amount_cents
        FROM journal_entry_lines AS jel
        JOIN journal_entries AS je
          ON je.journal_entry_id = jel.journal_entry_id
        WHERE jel.account_id IN ({placeholders})
          AND je.status = 'posted'
          AND je.entry_date <= ?
        """,
        (*cash_account_ids, end_date.isoformat()),
    ).fetchall()
    return _cash_balance_from_rows(rows)


def _cash_balance_from_rows(rows: list[sqlite3.Row]) -> int:
    balance = 0
    for row in rows:
        side = _validate_side(str(row["side"]))
        amount_cents = _validate_int_field(row["amount_cents"], "amount_cents")
        if amount_cents <= 0:
            raise ValidationError("Journal line amount_cents must be positive.")
        if side == "debit":
            balance += amount_cents
        else:
            balance -= amount_cents
    return balance


def _cash_movements_by_section(
    connection: sqlite3.Connection,
    cash_account_ids: list[str],
    start_date: date,
    end_date: date,
) -> dict[str, list[dict[str, object]]]:
    sections: dict[str, list[dict[str, object]]] = {
        "operating": [],
        "investing": [],
        "financing": [],
    }
    if not cash_account_ids:
        return sections

    placeholders = ", ".join("?" for _ in cash_account_ids)
    cash_lines = connection.execute(
        f"""
        SELECT
            je.journal_entry_id,
            je.entry_date,
            je.description,
            jel.line_id AS cash_line_id,
            jel.account_id AS cash_account_id,
            cash_account.code AS cash_account_code,
            cash_account.name AS cash_account_name,
            jel.side AS cash_side,
            jel.amount_cents AS cash_amount_cents
        FROM journal_entry_lines AS jel
        JOIN journal_entries AS je
          ON je.journal_entry_id = jel.journal_entry_id
        JOIN accounts AS cash_account
          ON cash_account.account_id = jel.account_id
        WHERE jel.account_id IN ({placeholders})
          AND je.status = 'posted'
          AND je.entry_date >= ?
          AND je.entry_date <= ?
        ORDER BY je.entry_date, je.journal_entry_id, jel.line_number, jel.line_id
        """,
        (*cash_account_ids, start_date.isoformat(), end_date.isoformat()),
    ).fetchall()

    cash_account_id_set = set(cash_account_ids)
    for cash_line in cash_lines:
        counterparty_lines = _counterparty_lines(
            connection,
            str(cash_line["journal_entry_id"]),
            cash_account_id_set,
        )
        if not counterparty_lines:
            continue

        cash_flow_amount_cents = _cash_flow_amount(cash_line)
        allocated_amounts = _allocate_cash_flow_amount(
            cash_flow_amount_cents,
            counterparty_lines,
        )
        multiple_counterparties = len(counterparty_lines) > 1

        for counterparty, allocated_amount in zip(
            counterparty_lines,
            allocated_amounts,
            strict=True,
        ):
            section = classify_cash_flow_section(
                str(counterparty["counterparty_account_type"]),
                counterparty_account_code=counterparty["counterparty_account_code"],
                counterparty_account_name=counterparty["counterparty_account_name"],
            )
            row = _cash_flow_row(
                section=section,
                cash_line=cash_line,
                cash_flow_amount_cents=allocated_amount,
                counterparty=counterparty,
                multiple_counterparties=multiple_counterparties,
            )
            sections[section].append(row)

    return sections


def _counterparty_lines(
    connection: sqlite3.Connection,
    journal_entry_id: str,
    cash_account_ids: set[str],
) -> list[sqlite3.Row]:
    rows = connection.execute(
        """
        SELECT
            jel.line_id AS counterparty_line_id,
            jel.account_id AS counterparty_account_id,
            account.code AS counterparty_account_code,
            account.name AS counterparty_account_name,
            account.account_type AS counterparty_account_type,
            account.normal_balance AS counterparty_normal_balance,
            jel.side AS counterparty_side,
            jel.amount_cents AS counterparty_amount_cents
        FROM journal_entry_lines AS jel
        JOIN accounts AS account
          ON account.account_id = jel.account_id
        WHERE jel.journal_entry_id = ?
        ORDER BY jel.line_number, jel.line_id
        """,
        (journal_entry_id,),
    ).fetchall()

    counterparties: list[sqlite3.Row] = []
    for row in rows:
        account_id = str(row["counterparty_account_id"])
        if account_id in cash_account_ids:
            continue
        if _is_cash_like_account(row):
            continue
        counterparties.append(row)
    return counterparties


def _cash_flow_amount(cash_line: sqlite3.Row) -> int:
    side = _validate_side(str(cash_line["cash_side"]))
    amount_cents = _validate_int_field(
        cash_line["cash_amount_cents"],
        "cash_amount_cents",
    )
    if amount_cents <= 0:
        raise ValidationError("Cash line amount_cents must be positive.")
    if side == "debit":
        return amount_cents
    return -amount_cents


def _allocate_cash_flow_amount(
    cash_flow_amount_cents: int,
    counterparty_lines: list[sqlite3.Row],
) -> list[int]:
    if not counterparty_lines:
        return []
    if len(counterparty_lines) == 1:
        return [cash_flow_amount_cents]

    counterparty_amounts = [
        _validate_int_field(
            row["counterparty_amount_cents"], 
            "counterparty_amount_cents"
        )
        for row in counterparty_lines
    ]
    total_counterparty_amount = sum(counterparty_amounts)
    if total_counterparty_amount <= 0:
        raise ValidationError("Counterparty amounts must have a positive total.")

    sign = 1 if cash_flow_amount_cents >= 0 else -1
    remaining_abs_amount = abs(cash_flow_amount_cents)
    allocated: list[int] = []
    for index, counterparty_amount in enumerate(counterparty_amounts):
        if counterparty_amount <= 0:
            raise ValidationError("Counterparty amount_cents must be positive.")
        if index == len(counterparty_amounts) - 1:
            portion_abs = remaining_abs_amount
        else:
            portion_abs = abs(cash_flow_amount_cents) * counterparty_amount
            portion_abs //= total_counterparty_amount
            remaining_abs_amount -= portion_abs
        allocated.append(portion_abs * sign)
    return allocated


def _cash_flow_row(
    *,
    section: str,
    cash_line: sqlite3.Row,
    cash_flow_amount_cents: int,
    counterparty: sqlite3.Row,
    multiple_counterparties: bool,
) -> dict[str, object]:
    if section not in VALID_SECTIONS:
        raise ValidationError(f"Invalid cash flow section: {section}.")
    cash_side = _validate_side(str(cash_line["cash_side"]))
    counterparty_side = _validate_side(str(counterparty["counterparty_side"]))
    cash_amount_cents = _validate_int_field(
        cash_line["cash_amount_cents"],
        "cash_amount_cents",
    )
    counterparty_amount_cents = _validate_int_field(
        counterparty["counterparty_amount_cents"],
        "counterparty_amount_cents",
    )
    classification_reason = _classification_reason(
        section,
        str(counterparty["counterparty_account_type"]),
        multiple_counterparties,
    )
    return {
        "section": section,
        "journal_entry_id": str(cash_line["journal_entry_id"]),
        "entry_date": str(cash_line["entry_date"]),
        "description": str(cash_line["description"]),
        "cash_account_id": str(cash_line["cash_account_id"]),
        "cash_account_code": str(cash_line["cash_account_code"]),
        "cash_account_name": str(cash_line["cash_account_name"]),
        "cash_line_id": str(cash_line["cash_line_id"]),
        "cash_side": cash_side,
        "cash_amount_cents": cash_amount_cents,
        "cash_flow_amount_cents": cash_flow_amount_cents,
        "counterparty_account_id": str(counterparty["counterparty_account_id"]),
        "counterparty_account_code": str(counterparty["counterparty_account_code"]),
        "counterparty_account_name": str(counterparty["counterparty_account_name"]),
        "counterparty_account_type": str(counterparty["counterparty_account_type"]),
        "counterparty_line_id": str(counterparty["counterparty_line_id"]),
        "counterparty_side": counterparty_side,
        "counterparty_amount_cents": counterparty_amount_cents,
        "classification_reason": classification_reason,
    }


def _classification_reason(
    section: str,
    account_type: str,
    multiple_counterparties: bool,
) -> str:
    reason = f"Classified as {section} because counterparty is {account_type}."
    if multiple_counterparties:
        reason += " Cash flow amount was proportionally allocated."
    return reason


def _compute_totals(
    sections: dict[str, Any],
    *,
    beginning_cash_cents: int,
    ending_cash_cents: int,
) -> dict[str, object]:
    section_totals: dict[str, int] = {}
    for section in ("operating", "investing", "financing"):
        rows = sections.get(section)
        if not isinstance(rows, list):
            raise ValidationError(f"Cash flow section must be a list: {section}.")
        section_totals[section] = sum(_row_cash_flow_amount(row) for row in rows)

    net_cash_change_cents = sum(section_totals.values())
    return {
        "operating_cash_flow_cents": section_totals["operating"],
        "investing_cash_flow_cents": section_totals["investing"],
        "financing_cash_flow_cents": section_totals["financing"],
        "net_cash_change_cents": net_cash_change_cents,
        "beginning_cash_cents": beginning_cash_cents,
        "ending_cash_cents": ending_cash_cents,
        "cash_balances_tie": (
            beginning_cash_cents + net_cash_change_cents == ending_cash_cents
        ),
    }


def _row_cash_flow_amount(row: object) -> int:
    if not isinstance(row, dict):
        raise ValidationError("Cash flow section rows must be dictionaries.")
    if "cash_flow_amount_cents" not in row:
        raise ValidationError("Cash flow row missing cash_flow_amount_cents.")
    return _validate_int_field(
        row["cash_flow_amount_cents"],
        "cash_flow_amount_cents",
    )


def _is_cash_like_account(row: sqlite3.Row) -> bool:
    keys = set(row.keys())
    account_type_key = (
        "account_type" if "account_type" in keys else "counterparty_account_type"
    )
    normal_balance_key = (
        "normal_balance"
        if "normal_balance" in keys
        else "counterparty_normal_balance"
    )
    code_key = "code" if "code" in keys else "counterparty_account_code"
    name_key = "name" if "name" in keys else "counterparty_account_name"

    account_type = str(row[account_type_key]).strip().lower()
    normal_balance = str(row[normal_balance_key]).strip().lower()
    code = str(row[code_key])
    name = str(row[name_key])
    if account_type != "asset" or normal_balance != "debit":
        return False
    normalized_name = name.strip().lower()
    return code.strip() == "1000" or any(
        token in normalized_name for token in ("cash", "checking", "bank")
    )


def _validate_side(side: str) -> str:
    if side not in {"debit", "credit"}:
        raise ValidationError(f"Invalid journal line side: {side}.")
    return side


def _validate_int_field(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an integer.")
    return value

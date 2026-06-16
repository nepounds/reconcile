"""Journal entry and journal line models for Reconcile."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from reconcile.exceptions import ValidationError

DEBIT = "debit"
CREDIT = "credit"
VALID_LINE_SIDES = frozenset({DEBIT, CREDIT})


def _validate_required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        msg = f"{field_name} must be a string."
        raise ValidationError(msg)
    if value.strip() == "":
        msg = f"{field_name} cannot be blank."
        raise ValidationError(msg)
    return value


def _validate_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _validate_required_text(value, field_name)


def _validate_positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer."
        raise ValidationError(msg)
    if value <= 0:
        msg = f"{field_name} must be greater than zero."
        raise ValidationError(msg)
    return value


def _validate_entry_date(value: date) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        msg = "entry_date must be a datetime.date."
        raise ValidationError(msg)
    return value


@dataclass(frozen=True)
class JournalLine:
    """One debit or credit line inside a journal entry."""

    line_id: str
    journal_entry_id: str
    account_id: str
    side: str
    amount_cents: int
    line_number: int
    description: str | None = None

    def __post_init__(self) -> None:
        _validate_required_text(self.line_id, "line_id")
        _validate_required_text(self.journal_entry_id, "journal_entry_id")
        _validate_required_text(self.account_id, "account_id")
        _validate_required_text(self.side, "side")
        if self.side not in VALID_LINE_SIDES:
            msg = "side must be 'debit' or 'credit'."
            raise ValidationError(msg)
        _validate_positive_int(self.amount_cents, "amount_cents")
        _validate_positive_int(self.line_number, "line_number")
        _validate_optional_text(self.description, "description")


@dataclass(frozen=True)
class JournalEntry:
    """A balanced double-entry accounting journal entry."""

    journal_entry_id: str
    entry_date: date
    description: str
    lines: list[JournalLine]
    source: str
    external_reference: str | None = None

    def __post_init__(self) -> None:
        _validate_required_text(self.journal_entry_id, "journal_entry_id")
        _validate_entry_date(self.entry_date)
        _validate_required_text(self.description, "description")
        _validate_required_text(self.source, "source")
        _validate_optional_text(self.external_reference, "external_reference")
        self._validate_lines()

    def _validate_lines(self) -> None:
        if not isinstance(self.lines, list):
            msg = "lines must be a list."
            raise ValidationError(msg)
        if len(self.lines) < 2:
            msg = "journal entry must contain at least two lines."
            raise ValidationError(msg)

        line_numbers: set[int] = set()
        debit_total = 0
        credit_total = 0

        for line in self.lines:
            if not isinstance(line, JournalLine):
                msg = "every item in lines must be a JournalLine."
                raise ValidationError(msg)
            if line.journal_entry_id != self.journal_entry_id:
                msg = "every line must match the journal_entry_id."
                raise ValidationError(msg)
            if line.line_number in line_numbers:
                msg = "line_number values must be unique within a journal entry."
                raise ValidationError(msg)
            line_numbers.add(line.line_number)

            if line.side == DEBIT:
                debit_total += line.amount_cents
            elif line.side == CREDIT:
                credit_total += line.amount_cents
            else:
                msg = "side must be 'debit' or 'credit'."
                raise ValidationError(msg)

        if debit_total != credit_total:
            msg = "journal entry is unbalanced: total debits must equal total credits."
            raise ValidationError(msg)

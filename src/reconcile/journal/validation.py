"""Validation helpers for journal entries and journal lines."""

from __future__ import annotations

from reconcile.exceptions import ValidationError
from reconcile.journal.models import CREDIT, DEBIT, JournalEntry, JournalLine


def validate_journal_line(line: JournalLine) -> JournalLine:
    """Return a journal line after confirming it is valid."""
    if not isinstance(line, JournalLine):
        msg = "line must be a JournalLine."
        raise ValidationError(msg)
    return JournalLine(
        line_id=line.line_id,
        journal_entry_id=line.journal_entry_id,
        account_id=line.account_id,
        side=line.side,
        amount_cents=line.amount_cents,
        line_number=line.line_number,
        description=line.description,
    )


def validate_journal_entry(entry: JournalEntry) -> JournalEntry:
    """Return a journal entry after confirming it is valid and balanced."""
    if not isinstance(entry, JournalEntry):
        msg = "entry must be a JournalEntry."
        raise ValidationError(msg)
    return JournalEntry(
        journal_entry_id=entry.journal_entry_id,
        entry_date=entry.entry_date,
        description=entry.description,
        lines=entry.lines,
        source=entry.source,
        external_reference=entry.external_reference,
    )


def _validate_lines(lines: list[JournalLine]) -> list[JournalLine]:
    if not isinstance(lines, list):
        msg = "lines must be a list."
        raise ValidationError(msg)
    for line in lines:
        validate_journal_line(line)
    return lines


def total_debits(lines: list[JournalLine]) -> int:
    """Return the total debit amount in integer cents."""
    valid_lines = _validate_lines(lines)
    return sum(line.amount_cents for line in valid_lines if line.side == DEBIT)


def total_credits(lines: list[JournalLine]) -> int:
    """Return the total credit amount in integer cents."""
    valid_lines = _validate_lines(lines)
    return sum(line.amount_cents for line in valid_lines if line.side == CREDIT)


def is_balanced(lines: list[JournalLine]) -> bool:
    """Return whether total debits equal total credits."""
    return total_debits(lines) == total_credits(lines)

from datetime import date

import pytest

from reconcile.exceptions import ValidationError
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.validation import is_balanced, total_credits, total_debits


def make_line(
    *,
    line_id: str = "line-1",
    journal_entry_id: str = "je-1",
    account_id: str = "acct-1",
    side: str = "debit",
    amount_cents: int = 1000,
    line_number: int = 1,
    description: str | None = "Line description",
) -> JournalLine:
    return JournalLine(
        line_id=line_id,
        journal_entry_id=journal_entry_id,
        account_id=account_id,
        side=side,
        amount_cents=amount_cents,
        line_number=line_number,
        description=description,
    )


def make_balanced_lines(journal_entry_id: str = "je-1") -> list[JournalLine]:
    return [
        make_line(
            line_id="line-1",
            journal_entry_id=journal_entry_id,
            account_id="cash",
            side="debit",
            amount_cents=1000,
            line_number=1,
        ),
        make_line(
            line_id="line-2",
            journal_entry_id=journal_entry_id,
            account_id="revenue",
            side="credit",
            amount_cents=1000,
            line_number=2,
        ),
    ]


def make_entry(
    *,
    journal_entry_id: str = "je-1",
    entry_date: date = date(2026, 1, 1),
    description: str = "Record service revenue",
    lines: list[JournalLine] | None = None,
    source: str = "manual",
    external_reference: str | None = None,
) -> JournalEntry:
    if lines is None:
        lines = make_balanced_lines(journal_entry_id)
    return JournalEntry(
        journal_entry_id=journal_entry_id,
        entry_date=entry_date,
        description=description,
        lines=lines,
        source=source,
        external_reference=external_reference,
    )


def test_creates_valid_debit_journal_line():
    line = make_line(side="debit")

    assert line.side == "debit"
    assert line.amount_cents == 1000


def test_creates_valid_credit_journal_line():
    line = make_line(side="credit")

    assert line.side == "credit"
    assert line.amount_cents == 1000


def test_rejects_blank_line_id():
    with pytest.raises(ValidationError):
        make_line(line_id=" ")


def test_rejects_blank_line_journal_entry_id():
    with pytest.raises(ValidationError):
        make_line(journal_entry_id=" ")


def test_rejects_blank_account_id():
    with pytest.raises(ValidationError):
        make_line(account_id=" ")


def test_rejects_invalid_line_side():
    with pytest.raises(ValidationError):
        make_line(side="increase")


def test_rejects_zero_amount_cents():
    with pytest.raises(ValidationError):
        make_line(amount_cents=0)


def test_rejects_negative_amount_cents():
    with pytest.raises(ValidationError):
        make_line(amount_cents=-1)


def test_rejects_non_int_amount_cents():
    with pytest.raises(ValidationError):
        make_line(amount_cents="1000")


def test_rejects_bool_amount_cents():
    with pytest.raises(ValidationError):
        make_line(amount_cents=True)


def test_rejects_zero_line_number():
    with pytest.raises(ValidationError):
        make_line(line_number=0)


def test_rejects_negative_line_number():
    with pytest.raises(ValidationError):
        make_line(line_number=-1)


def test_rejects_non_int_line_number():
    with pytest.raises(ValidationError):
        make_line(line_number="1")


def test_rejects_bool_line_number():
    with pytest.raises(ValidationError):
        make_line(line_number=False)


def test_rejects_blank_line_description_when_provided():
    with pytest.raises(ValidationError):
        make_line(description=" ")


def test_creates_valid_balanced_journal_entry():
    entry = make_entry()

    assert entry.journal_entry_id == "je-1"
    assert len(entry.lines) == 2


def test_rejects_blank_entry_journal_entry_id():
    with pytest.raises(ValidationError):
        make_entry(journal_entry_id=" ")


def test_rejects_non_date_entry_date():
    with pytest.raises(ValidationError):
        make_entry(entry_date="2026-01-01")


def test_rejects_blank_entry_description():
    with pytest.raises(ValidationError):
        make_entry(description=" ")


def test_rejects_blank_source():
    with pytest.raises(ValidationError):
        make_entry(source=" ")


def test_rejects_blank_external_reference_when_provided():
    with pytest.raises(ValidationError):
        make_entry(external_reference=" ")


def test_rejects_non_list_lines():
    with pytest.raises(ValidationError):
        make_entry(lines=tuple(make_balanced_lines()))


def test_rejects_entry_with_fewer_than_two_lines():
    with pytest.raises(ValidationError):
        make_entry(lines=[make_balanced_lines()[0]])


def test_rejects_non_journal_line_items_in_lines():
    lines = [make_balanced_lines()[0], "not-a-line"]

    with pytest.raises(ValidationError):
        make_entry(lines=lines)


def test_rejects_lines_whose_journal_entry_id_does_not_match_entry():
    lines = make_balanced_lines(journal_entry_id="different-entry")

    with pytest.raises(ValidationError):
        make_entry(journal_entry_id="je-1", lines=lines)


def test_rejects_duplicate_line_numbers():
    lines = [
        make_line(line_id="line-1", side="debit", line_number=1),
        make_line(line_id="line-2", side="credit", line_number=1),
    ]

    with pytest.raises(ValidationError):
        make_entry(lines=lines)


def test_rejects_unbalanced_journal_entries():
    lines = [
        make_line(line_id="line-1", side="debit", amount_cents=1000, line_number=1),
        make_line(line_id="line-2", side="credit", amount_cents=900, line_number=2),
    ]

    with pytest.raises(ValidationError):
        make_entry(lines=lines)


def test_total_debits_returns_expected_cents():
    assert total_debits(make_balanced_lines()) == 1000


def test_total_credits_returns_expected_cents():
    assert total_credits(make_balanced_lines()) == 1000


def test_is_balanced_returns_true_for_balanced_lines():
    assert is_balanced(make_balanced_lines()) is True


def test_invalid_journal_data_raises_validation_error():
    with pytest.raises(ValidationError):
        JournalLine(
            line_id="line-1",
            journal_entry_id="je-1",
            account_id="cash",
            side="debit",
            amount_cents=0,
            line_number=1,
        )

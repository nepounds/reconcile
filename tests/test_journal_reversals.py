from __future__ import annotations

from datetime import date

import pytest

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.events.handlers import apply_event
from reconcile.events.models import LedgerEvent
from reconcile.events.store import append_event, load_events
from reconcile.exceptions import ValidationError
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import post_journal_entry, reverse_journal_entry
from reconcile.projections.balances import get_account_balance
from reconcile.projections.rebuild import rebuild_projections
from reconcile.reports.balance_sheet import generate_balance_sheet
from reconcile.reports.income_statement import generate_income_statement
from reconcile.reports.trial_balance import generate_trial_balance, trial_balance_totals


def _connection(tmp_path):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)
    return connection


def _account(
    account_id: str,
    code: str,
    name: str,
    account_type: str,
    normal_balance: str,
) -> Account:
    return Account(
        account_id=account_id,
        code=code,
        name=name,
        account_type=account_type,
        normal_balance=normal_balance,
        is_active=True,
        opened_at="2026-01-01T00:00:00+00:00",
        closed_at=None,
    )


def _seed_accounts(connection):
    cash = _account("acct-cash", "1000", "Cash", "asset", "debit")
    revenue = _account("acct-revenue", "4000", "Revenue", "revenue", "credit")
    expense = _account("acct-expense", "5000", "Expense", "expense", "debit")
    equity = _account("acct-equity", "3000", "Equity", "equity", "credit")

    for account in (cash, revenue, expense, equity):
        open_account(connection, account=account)

    return cash, revenue, expense, equity


def _post_cash_revenue_entry(connection, entry_id="je-1"):
    entry = JournalEntry(
        journal_entry_id=entry_id,
        entry_date=date(2026, 1, 15),
        description="Earned revenue",
        lines=[
            JournalLine(
                line_id=f"{entry_id}-line-1",
                journal_entry_id=entry_id,
                account_id="acct-cash",
                side="debit",
                amount_cents=10_000,
                description="Cash received",
                line_number=1,
            ),
            JournalLine(
                line_id=f"{entry_id}-line-2",
                journal_entry_id=entry_id,
                account_id="acct-revenue",
                side="credit",
                amount_cents=10_000,
                description="Revenue earned",
                line_number=2,
            ),
        ],
        source="manual",
        external_reference=None,
    )
    return post_journal_entry(connection, journal_entry=entry)


def test_reversing_posted_journal_entry_appends_reversal_event(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)

    reverse_journal_entry(
        connection,
        "je-1",
        reversal_entry_id="rev-je-1",
        reversal_date=date(2026, 1, 20),
    )

    events = load_events(connection)
    assert events[-1].event_type == "JournalEntryReversed"
    assert events[-1].payload["original_journal_entry_id"] == "je-1"
    assert events[-1].payload["reversal_journal_entry_id"] == "rev-je-1"


def test_reversal_entry_and_original_entry_are_projected_correctly(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)

    reverse_journal_entry(
        connection,
        "je-1",
        reversal_entry_id="rev-je-1",
        reversal_date=date(2026, 1, 20),
    )

    original = connection.execute(
        """
        SELECT status, reversed_by_entry_id, reversal_of_entry_id
        FROM journal_entries
        WHERE journal_entry_id = 'je-1'
        """
    ).fetchone()
    reversal = connection.execute(
        """
        SELECT status, reversed_by_entry_id, reversal_of_entry_id
        FROM journal_entries
        WHERE journal_entry_id = 'rev-je-1'
        """
    ).fetchone()

    assert original["status"] == "posted"
    assert original["reversed_by_entry_id"] == "rev-je-1"
    assert original["reversal_of_entry_id"] is None

    assert reversal["status"] == "posted"
    assert reversal["reversed_by_entry_id"] is None
    assert reversal["reversal_of_entry_id"] == "je-1"


def test_original_journal_lines_are_not_changed(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)

    before = connection.execute(
        """
        SELECT line_id, side, amount_cents, line_number
        FROM journal_entry_lines
        WHERE journal_entry_id = 'je-1'
        ORDER BY line_number
        """
    ).fetchall()

    reverse_journal_entry(connection, "je-1", reversal_entry_id="rev-je-1")

    after = connection.execute(
        """
        SELECT line_id, side, amount_cents, line_number
        FROM journal_entry_lines
        WHERE journal_entry_id = 'je-1'
        ORDER BY line_number
        """
    ).fetchall()

    assert [dict(row) for row in after] == [dict(row) for row in before]


def test_reversal_lines_flip_sides_and_preserve_order_accounts_and_amounts(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)

    reversal = reverse_journal_entry(
        connection,
        "je-1",
        reversal_entry_id="rev-je-1",
    )

    assert [line.line_number for line in reversal.lines] == [1, 2]
    assert [line.account_id for line in reversal.lines] == [
        "acct-cash",
        "acct-revenue",
    ]
    assert [line.amount_cents for line in reversal.lines] == [10_000, 10_000]
    assert [line.side for line in reversal.lines] == ["credit", "debit"]

    stored_lines = connection.execute(
        """
        SELECT account_id, side, amount_cents, line_number
        FROM journal_entry_lines
        WHERE journal_entry_id = 'rev-je-1'
        ORDER BY line_number
        """
    ).fetchall()

    assert [row["side"] for row in stored_lines] == ["credit", "debit"]


def test_reversal_updates_account_balances_without_erasing_activity(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)

    reverse_journal_entry(connection, "je-1", reversal_entry_id="rev-je-1")

    cash_balance = get_account_balance(connection, "acct-cash")
    revenue_balance = get_account_balance(connection, "acct-revenue")

    assert cash_balance["debit_total_cents"] == 10_000
    assert cash_balance["credit_total_cents"] == 10_000
    assert cash_balance["balance_cents"] == 0

    assert revenue_balance["credit_total_cents"] == 10_000
    assert revenue_balance["debit_total_cents"] == 10_000
    assert revenue_balance["balance_cents"] == 0


def test_reversal_event_payload_contains_rebuildable_line_data(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)

    reverse_journal_entry(connection, "je-1", reversal_entry_id="rev-je-1")

    event = load_events(connection)[-1]
    line = event.payload["lines"][0]

    assert {
        "line_id",
        "journal_entry_id",
        "account_id",
        "side",
        "amount_cents",
        "description",
        "line_number",
    } <= set(line)


def test_explicit_reversal_date_and_id_are_used(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)

    reversal = reverse_journal_entry(
        connection,
        "je-1",
        reversal_entry_id="custom-reversal",
        reversal_date=date(2026, 2, 1),
    )

    assert reversal.journal_entry_id == "custom-reversal"
    assert reversal.entry_date == date(2026, 2, 1)


def test_missing_reversal_date_uses_original_entry_date(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)

    reversal = reverse_journal_entry(
        connection,
        "je-1",
        reversal_entry_id="rev-je-1",
    )

    assert reversal.entry_date == date(2026, 1, 15)


@pytest.mark.parametrize("bad_id", ["", "   ", None])
def test_blank_original_entry_id_raises_validation_error(tmp_path, bad_id):
    connection = _connection(tmp_path)
    _seed_accounts(connection)

    with pytest.raises(ValidationError):
        reverse_journal_entry(connection, bad_id)


def test_missing_original_journal_entry_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)

    with pytest.raises(ValidationError):
        reverse_journal_entry(connection, "missing")


def test_already_reversed_original_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)
    reverse_journal_entry(connection, "je-1", reversal_entry_id="rev-je-1")

    with pytest.raises(ValidationError):
        reverse_journal_entry(connection, "je-1", reversal_entry_id="rev-je-2")


def test_attempting_to_reverse_reversal_entry_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)
    reverse_journal_entry(connection, "je-1", reversal_entry_id="rev-je-1")

    with pytest.raises(ValidationError):
        reverse_journal_entry(connection, "rev-je-1", reversal_entry_id="rev-rev-je-1")


def test_duplicate_reversal_entry_id_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection, entry_id="je-1")
    _post_cash_revenue_entry(connection, entry_id="je-2")

    with pytest.raises(ValidationError):
        reverse_journal_entry(connection, "je-1", reversal_entry_id="je-2")


def test_pre_validation_failure_does_not_append_reversal_event(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    before_count = len(load_events(connection))

    with pytest.raises(ValidationError):
        reverse_journal_entry(connection, "missing")

    after_count = len(load_events(connection))
    assert after_count == before_count


def test_apply_reversal_event_directly_creates_projection_and_balances(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)

    event = LedgerEvent(
        event_id="event-direct-reversal",
        event_type="JournalEntryReversed",
        event_version=1,
        event_timestamp="2026-01-20T00:00:00+00:00",
        effective_date="2026-01-20",
        source="manual",
        actor=None,
        correlation_id=None,
        causation_id=None,
        payload={
            "original_journal_entry_id": "je-1",
            "reversal_journal_entry_id": "rev-direct",
            "reversal_date": "2026-01-20",
            "description": "Direct reversal",
            "source": "manual",
            "external_reference": "je-1",
            "lines": [
                {
                    "line_id": "rev-direct-line-1",
                    "journal_entry_id": "rev-direct",
                    "account_id": "acct-cash",
                    "side": "credit",
                    "amount_cents": 10_000,
                    "description": "Cash received",
                    "line_number": 1,
                },
                {
                    "line_id": "rev-direct-line-2",
                    "journal_entry_id": "rev-direct",
                    "account_id": "acct-revenue",
                    "side": "debit",
                    "amount_cents": 10_000,
                    "description": "Revenue earned",
                    "line_number": 2,
                },
            ],
        },
        created_at="2026-01-20T00:00:00+00:00",
    )

    stored_event = append_event(connection, event)
    apply_event(connection, stored_event)

    reversal = connection.execute(
        """
        SELECT reversal_of_entry_id
        FROM journal_entries
        WHERE journal_entry_id = 'rev-direct'
        """
    ).fetchone()

    original = connection.execute(
        """
        SELECT reversed_by_entry_id
        FROM journal_entries
        WHERE journal_entry_id = 'je-1'
        """
    ).fetchone()

    assert reversal["reversal_of_entry_id"] == "je-1"
    assert original["reversed_by_entry_id"] == "rev-direct"
    assert get_account_balance(connection, "acct-cash")["balance_cents"] == 0


def test_invalid_reversal_event_payload_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)

    event = LedgerEvent(
        event_id="event-bad-reversal",
        event_type="JournalEntryReversed",
        event_version=1,
        event_timestamp="2026-01-20T00:00:00+00:00",
        effective_date="2026-01-20",
        source="manual",
        actor=None,
        correlation_id=None,
        causation_id=None,
        payload={
            "original_journal_entry_id": "je-1",
            "reversal_journal_entry_id": "rev-bad",
            "reversal_date": "2026-01-20",
            "description": "Bad reversal",
            "source": "manual",
            "external_reference": "je-1",
            "lines": [
                {
                    "line_id": "rev-bad-line-1",
                    "journal_entry_id": "rev-bad",
                    "account_id": "acct-cash",
                    "side": "nonsense",
                    "amount_cents": 10_000,
                    "description": None,
                    "line_number": 1,
                }
            ],
        },
        created_at="2026-01-20T00:00:00+00:00",
    )

    with pytest.raises(ValidationError):
        apply_event(connection, event)


def test_projection_rebuild_restores_reversal_state_and_balances(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)
    reverse_journal_entry(connection, "je-1", reversal_entry_id="rev-je-1")

    rebuild_projections(connection)

    original = connection.execute(
        """
        SELECT reversed_by_entry_id
        FROM journal_entries
        WHERE journal_entry_id = 'je-1'
        """
    ).fetchone()
    reversal = connection.execute(
        """
        SELECT reversal_of_entry_id
        FROM journal_entries
        WHERE journal_entry_id = 'rev-je-1'
        """
    ).fetchone()

    assert original["reversed_by_entry_id"] == "rev-je-1"
    assert reversal["reversal_of_entry_id"] == "je-1"
    assert get_account_balance(connection, "acct-cash")["balance_cents"] == 0
    assert get_account_balance(connection, "acct-revenue")["balance_cents"] == 0


def test_reports_reflect_reversal_activity(tmp_path):
    connection = _connection(tmp_path)
    _seed_accounts(connection)
    _post_cash_revenue_entry(connection)
    reverse_journal_entry(
        connection,
        "je-1",
        reversal_entry_id="rev-je-1",
        reversal_date=date(2026, 1, 20),
    )

    trial_balance = generate_trial_balance(connection)
    trial_balance_total = trial_balance_totals(trial_balance)
    income_statement = generate_income_statement(
        connection,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    balance_sheet = generate_balance_sheet(
        connection,
        as_of_date=date(2026, 1, 31),
    )

    assert trial_balance_total["is_balanced"] is True
    assert income_statement["total_revenue_cents"] == 0
    assert income_statement["net_income_cents"] == 0
    assert balance_sheet["total_assets_cents"] == 0
    assert balance_sheet["is_balanced"] is True
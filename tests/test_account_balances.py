from __future__ import annotations

from datetime import date

import pytest

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.events.handlers import apply_event
from reconcile.events.models import LedgerEvent
from reconcile.events.store import load_events
from reconcile.exceptions import ValidationError
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import post_journal_entry
from reconcile.projections.balances import (
    apply_journal_entry_posted_to_balances,
    get_account_balance,
    list_account_balances,
)


def _connection(tmp_path):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)
    return connection


def _open_account(
    connection,
    *,
    account_id,
    code,
    account_type,
    normal_balance,
    name=None,
):
    account = Account(
        account_id=account_id,
        code=code,
        name=name or code,
        account_type=account_type,
        normal_balance=normal_balance,
        is_active=True,
        opened_at="2026-01-01T00:00:00+00:00",
        closed_at=None,
    )
    return open_account(connection, account=account)


def _open_standard_accounts(connection):
    _open_account(
        connection,
        account_id="cash",
        code="1000",
        name="Cash",
        account_type="asset",
        normal_balance="debit",
    )
    _open_account(
        connection,
        account_id="expense",
        code="5000",
        name="Expense",
        account_type="expense",
        normal_balance="debit",
    )
    _open_account(
        connection,
        account_id="liability",
        code="2000",
        name="Liability",
        account_type="liability",
        normal_balance="credit",
    )
    _open_account(
        connection,
        account_id="equity",
        code="3000",
        name="Equity",
        account_type="equity",
        normal_balance="credit",
    )
    _open_account(
        connection,
        account_id="revenue",
        code="4000",
        name="Revenue",
        account_type="revenue",
        normal_balance="credit",
    )


def _post_entry(connection, journal_entry_id, lines):
    entry = JournalEntry(
        journal_entry_id=journal_entry_id,
        entry_date=date(2026, 1, 1),
        description=journal_entry_id,
        lines=[
            JournalLine(
                line_id=f"{journal_entry_id}-line-{index}",
                journal_entry_id=journal_entry_id,
                account_id=account_id,
                side=side,
                amount_cents=amount_cents,
                description=None,
                line_number=index,
            )
            for index, (account_id, side, amount_cents) in enumerate(lines, start=1)
        ],
        source="test",
        external_reference=None,
    )
    return post_journal_entry(connection, entry)


def _latest_journal_entry_posted_event(connection):
    events = [
        event
        for event in load_events(connection)
        if event.event_type == "JournalEntryPosted"
    ]
    return events[-1]


def _event(
    *,
    event_type="JournalEntryPosted",
    event_sequence=1,
    payload=None,
):
    return LedgerEvent(
        event_id=f"event-{event_sequence}",
        event_type=event_type,
        event_version=1,
        event_timestamp="2026-01-01T00:00:00+00:00",
        effective_date="2026-01-01",
        source="test",
        actor=None,
        correlation_id=None,
        causation_id=None,
        payload=payload
        or {
            "journal_entry_id": f"je-{event_sequence}",
            "entry_date": "2026-01-01",
            "description": "Test entry",
            "source": "test",
            "external_reference": None,
            "lines": [
                {
                    "line_id": f"je-{event_sequence}-line-1",
                    "journal_entry_id": f"je-{event_sequence}",
                    "account_id": "cash",
                    "side": "debit",
                    "amount_cents": 100,
                    "description": None,
                    "line_number": 1,
                },
                {
                    "line_id": f"je-{event_sequence}-line-2",
                    "journal_entry_id": f"je-{event_sequence}",
                    "account_id": "equity",
                    "side": "credit",
                    "amount_cents": 100,
                    "description": None,
                    "line_number": 2,
                },
            ],
        },
        event_sequence=event_sequence,
    )


def test_posting_journal_entry_creates_account_balance_rows(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 1000),
            ("equity", "credit", 1000),
        ],
    )

    assert get_account_balance(connection, "cash") is not None
    assert get_account_balance(connection, "equity") is not None


def test_debit_to_asset_increases_asset_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 1000),
            ("equity", "credit", 1000),
        ],
    )

    assert get_account_balance(connection, "cash")["balance_cents"] == 1000


def test_credit_to_asset_decreases_asset_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 1000),
            ("equity", "credit", 1000),
        ],
    )
    _post_entry(
        connection,
        "je-2",
        [
            ("expense", "debit", 250),
            ("cash", "credit", 250),
        ],
    )

    assert get_account_balance(connection, "cash")["balance_cents"] == 750


def test_debit_to_expense_increases_expense_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("expense", "debit", 500),
            ("cash", "credit", 500),
        ],
    )

    assert get_account_balance(connection, "expense")["balance_cents"] == 500


def test_credit_to_expense_decreases_expense_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("expense", "debit", 500),
            ("cash", "credit", 500),
        ],
    )
    _post_entry(
        connection,
        "je-2",
        [
            ("cash", "debit", 200),
            ("expense", "credit", 200),
        ],
    )

    assert get_account_balance(connection, "expense")["balance_cents"] == 300


def test_credit_to_liability_increases_liability_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 700),
            ("liability", "credit", 700),
        ],
    )

    assert get_account_balance(connection, "liability")["balance_cents"] == 700


def test_debit_to_liability_decreases_liability_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 700),
            ("liability", "credit", 700),
        ],
    )
    _post_entry(
        connection,
        "je-2",
        [
            ("liability", "debit", 300),
            ("cash", "credit", 300),
        ],
    )

    assert get_account_balance(connection, "liability")["balance_cents"] == 400


def test_credit_to_equity_increases_equity_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 1000),
            ("equity", "credit", 1000),
        ],
    )

    assert get_account_balance(connection, "equity")["balance_cents"] == 1000


def test_debit_to_equity_decreases_equity_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 1000),
            ("equity", "credit", 1000),
        ],
    )
    _post_entry(
        connection,
        "je-2",
        [
            ("equity", "debit", 200),
            ("cash", "credit", 200),
        ],
    )

    assert get_account_balance(connection, "equity")["balance_cents"] == 800


def test_credit_to_revenue_increases_revenue_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 1200),
            ("revenue", "credit", 1200),
        ],
    )

    assert get_account_balance(connection, "revenue")["balance_cents"] == 1200


def test_debit_to_revenue_decreases_revenue_balance(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 1200),
            ("revenue", "credit", 1200),
        ],
    )
    _post_entry(
        connection,
        "je-2",
        [
            ("revenue", "debit", 300),
            ("cash", "credit", 300),
        ],
    )

    assert get_account_balance(connection, "revenue")["balance_cents"] == 900


def test_debit_totals_accumulate_across_multiple_entries(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 100),
            ("equity", "credit", 100),
        ],
    )
    _post_entry(
        connection,
        "je-2",
        [
            ("cash", "debit", 200),
            ("revenue", "credit", 200),
        ],
    )

    assert get_account_balance(connection, "cash")["debit_total_cents"] == 300


def test_credit_totals_accumulate_across_multiple_entries(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("expense", "debit", 100),
            ("cash", "credit", 100),
        ],
    )
    _post_entry(
        connection,
        "je-2",
        [
            ("expense", "debit", 200),
            ("cash", "credit", 200),
        ],
    )

    assert get_account_balance(connection, "cash")["credit_total_cents"] == 300


def test_balance_cents_recalculates_after_multiple_entries(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 1000),
            ("equity", "credit", 1000),
        ],
    )
    _post_entry(
        connection,
        "je-2",
        [
            ("expense", "debit", 300),
            ("cash", "credit", 300),
        ],
    )
    _post_entry(
        connection,
        "je-3",
        [
            ("cash", "debit", 200),
            ("revenue", "credit", 200),
        ],
    )

    assert get_account_balance(connection, "cash")["balance_cents"] == 900


def test_last_event_sequence_is_set_from_applied_event(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 100),
            ("equity", "credit", 100),
        ],
    )
    posted_event = _latest_journal_entry_posted_event(connection)

    assert (
        get_account_balance(connection, "cash")["last_event_sequence"]
        == posted_event.event_sequence
    )


def test_updated_at_is_populated(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 100),
            ("equity", "credit", 100),
        ],
    )

    assert get_account_balance(connection, "cash")["updated_at"]


def test_applying_journal_entry_posted_event_directly_updates_balances(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    event = _event()

    apply_journal_entry_posted_to_balances(connection, event)

    assert get_account_balance(connection, "cash")["balance_cents"] == 100
    assert get_account_balance(connection, "equity")["balance_cents"] == 100


def test_applying_same_event_twice_does_not_double_count_balances(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    event = _event()

    apply_journal_entry_posted_to_balances(connection, event)
    apply_journal_entry_posted_to_balances(connection, event)

    assert get_account_balance(connection, "cash")["debit_total_cents"] == 100
    assert get_account_balance(connection, "equity")["credit_total_cents"] == 100


def test_missing_account_during_balance_projection_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _open_account(
        connection,
        account_id="equity",
        code="3000",
        account_type="equity",
        normal_balance="credit",
    )
    event = _event()

    with pytest.raises(ValidationError, match="account does not exist"):
        apply_journal_entry_posted_to_balances(connection, event)


def test_invalid_normal_balance_in_database_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)
    connection.execute(
        "UPDATE accounts SET normal_balance = ? WHERE account_id = ?",
        ("weird", "cash"),
    )
    connection.commit()

    with pytest.raises(ValidationError):
        apply_journal_entry_posted_to_balances(connection, _event())


def test_get_account_balance_returns_expected_dict(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 100),
            ("equity", "credit", 100),
        ],
    )
    posted_event = _latest_journal_entry_posted_event(connection)

    balance = get_account_balance(connection, "cash")

    assert balance == {
        "account_id": "cash",
        "debit_total_cents": 100,
        "credit_total_cents": 0,
        "balance_cents": 100,
        "updated_at": posted_event.event_timestamp,
        "last_event_sequence": posted_event.event_sequence,
    }


def test_get_account_balance_returns_none_for_no_row(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    assert get_account_balance(connection, "cash") is None


def test_get_account_balance_rejects_blank_account_id(tmp_path):
    connection = _connection(tmp_path)

    with pytest.raises(ValidationError, match="account_id is required"):
        get_account_balance(connection, " ")


def test_list_account_balances_returns_stable_ordered_rows(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 100),
            ("equity", "credit", 100),
        ],
    )
    _post_entry(
        connection,
        "je-2",
        [
            ("cash", "debit", 200),
            ("revenue", "credit", 200),
        ],
    )

    balances = list_account_balances(connection)

    assert [balance["account_id"] for balance in balances] == [
        "cash",
        "equity",
        "revenue",
    ]


def test_account_opened_does_not_create_account_balance_row(tmp_path):
    connection = _connection(tmp_path)

    _open_account(
        connection,
        account_id="cash",
        code="1000",
        account_type="asset",
        normal_balance="debit",
    )

    assert list_account_balances(connection) == []


def test_unsupported_event_behavior_remains_consistent(tmp_path):
    connection = _connection(tmp_path)
    event = _event(
        event_type="AccountClosed",
        payload={"account_id": "cash"},
    )

    with pytest.raises(ValidationError, match="unsupported event type"):
        apply_event(connection, event)


def test_loaded_posted_event_can_be_applied_directly_to_balances(tmp_path):
    connection = _connection(tmp_path)
    _open_standard_accounts(connection)

    _post_entry(
        connection,
        "je-1",
        [
            ("cash", "debit", 100),
            ("equity", "credit", 100),
        ],
    )
    posted_event = _latest_journal_entry_posted_event(connection)

    connection.execute("DELETE FROM account_balances")
    connection.commit()

    loaded_event = [
        event
        for event in load_events(connection)
        if event.event_id == posted_event.event_id
    ][0]

    apply_journal_entry_posted_to_balances(connection, loaded_event)

    assert get_account_balance(connection, "cash")["balance_cents"] == 100
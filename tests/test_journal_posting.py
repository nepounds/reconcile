from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.events.handlers import apply_event
from reconcile.events.models import LedgerEvent
from reconcile.events.store import append_event, load_events
from reconcile.exceptions import ValidationError
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import (
    get_journal_entry_by_id,
    list_journal_entries,
    post_journal_entry,
)


@pytest.fixture()
def connection(tmp_path):
    db_path = tmp_path / "reconcile.db"
    conn = connect(db_path)
    initialize_schema(conn)
    _open_cash_and_revenue_accounts(conn)
    return conn


def test_posting_valid_entry_appends_journal_entry_posted_event(connection):
    post_journal_entry(connection, _journal_entry())

    events = load_events(connection)

    assert events[-1].event_type == "JournalEntryPosted"


def test_posting_valid_entry_inserts_journal_entry_row(connection):
    post_journal_entry(connection, _journal_entry())

    row = connection.execute(
        """
        SELECT *
        FROM journal_entries
        WHERE journal_entry_id = ?
        """,
        ("je-1",),
    ).fetchone()

    assert row is not None
    assert row["description"] == "Record service revenue"


def test_posting_valid_entry_inserts_all_journal_entry_lines(connection):
    post_journal_entry(connection, _journal_entry())

    rows = connection.execute(
        """
        SELECT *
        FROM journal_entry_lines
        WHERE journal_entry_id = ?
        ORDER BY line_number
        """,
        ("je-1",),
    ).fetchall()

    assert len(rows) == 2
    assert rows[0]["line_id"] == "jl-1"
    assert rows[1]["line_id"] == "jl-2"


def test_posted_journal_entry_status_and_reversal_fields(connection):
    post_journal_entry(connection, _journal_entry())

    row = connection.execute(
        """
        SELECT status, reversed_by_entry_id, reversal_of_entry_id
        FROM journal_entries
        WHERE journal_entry_id = ?
        """,
        ("je-1",),
    ).fetchone()

    assert row["status"] == "posted"
    assert row["reversed_by_entry_id"] is None
    assert row["reversal_of_entry_id"] is None


def test_event_payload_contains_header_fields_needed_for_rebuild(connection):
    post_journal_entry(connection, _journal_entry(), source="manual")

    event = load_events(connection)[-1]

    assert event.payload["journal_entry_id"] == "je-1"
    assert event.payload["entry_date"] == "2026-01-05"
    assert event.payload["description"] == "Record service revenue"
    assert event.payload["source"] == "manual"
    assert event.payload["external_reference"] == "INV-1"
    assert "lines" in event.payload


def test_event_payload_contains_line_fields_needed_for_rebuild(connection):
    post_journal_entry(connection, _journal_entry())

    event = load_events(connection)[-1]
    line = event.payload["lines"][0]

    assert line == {
        "line_id": "jl-1",
        "journal_entry_id": "je-1",
        "account_id": "acct-cash",
        "side": "debit",
        "amount_cents": 10000,
        "description": "Cash received",
        "line_number": 1,
    }


def test_posting_preserves_line_numbers_and_descriptions(connection):
    post_journal_entry(connection, _journal_entry())

    rows = connection.execute(
        """
        SELECT line_number, description
        FROM journal_entry_lines
        WHERE journal_entry_id = ?
        ORDER BY line_number
        """,
        ("je-1",),
    ).fetchall()

    assert [(row["line_number"], row["description"]) for row in rows] == [
        (1, "Cash received"),
        (2, "Service revenue earned"),
    ]


def test_posting_rejects_unbalanced_journal_entries(connection):
    with pytest.raises(ValidationError, match="balanced|debits|credits"):
        post_journal_entry(connection, _journal_entry(credit_amount=9000))


def test_posting_rejects_single_line_journal_entries(connection):
    with pytest.raises(ValidationError, match="at least two|single"):
        post_journal_entry(
            connection,
            _make_journal_entry(
                journal_entry_id="je-one-line",
                lines=[
                    JournalLine(
                        line_id="jl-one-line",
                        journal_entry_id="je-one-line",
                        account_id="acct-cash",
                        side="debit",
                        amount_cents=10000,
                        description="Cash only",
                        line_number=1,
                    )
                ],
            ),
        )


def test_posting_rejects_missing_accounts(connection):
    entry = _journal_entry(cash_account_id="acct-missing")

    with pytest.raises(ValidationError, match="missing account"):
        post_journal_entry(connection, entry)


def test_posting_rejects_inactive_accounts(connection):
    connection.execute(
        "UPDATE accounts SET is_active = 0 WHERE account_id = ?",
        ("acct-cash",),
    )
    connection.commit()

    with pytest.raises(ValidationError, match="inactive account"):
        post_journal_entry(connection, _journal_entry())


def test_posting_rejects_duplicate_journal_entry_id(connection):
    post_journal_entry(connection, _journal_entry())

    with pytest.raises(ValidationError, match="duplicate journal_entry_id"):
        post_journal_entry(connection, _journal_entry())


def test_duplicate_journal_entry_failure_does_not_append_event(connection):
    post_journal_entry(connection, _journal_entry())
    before_count = _event_count(connection)

    with pytest.raises(ValidationError, match="duplicate journal_entry_id"):
        post_journal_entry(connection, _journal_entry())

    assert _event_count(connection) == before_count


def test_missing_account_failure_does_not_append_event(connection):
    before_count = _event_count(connection)

    with pytest.raises(ValidationError, match="missing account"):
        post_journal_entry(
            connection,
            _journal_entry(cash_account_id="acct-missing"),
        )

    assert _event_count(connection) == before_count


def test_inactive_account_failure_does_not_append_event(connection):
    connection.execute(
        "UPDATE accounts SET is_active = 0 WHERE account_id = ?",
        ("acct-cash",),
    )
    connection.commit()
    before_count = _event_count(connection)

    with pytest.raises(ValidationError, match="inactive account"):
        post_journal_entry(connection, _journal_entry())

    assert _event_count(connection) == before_count


def test_applying_journal_entry_posted_directly_inserts_header_and_lines(
    connection,
):
    event = append_event(connection, _journal_entry_posted_event())

    apply_event(connection, event)

    header_count = connection.execute(
        "SELECT COUNT(*) AS count FROM journal_entries",
    ).fetchone()["count"]
    line_count = connection.execute(
        "SELECT COUNT(*) AS count FROM journal_entry_lines",
    ).fetchone()["count"]

    assert header_count == 1
    assert line_count == 2


def test_applying_journal_entry_posted_rejects_duplicate_entry_id(connection):
    event = append_event(connection, _journal_entry_posted_event())
    apply_event(connection, event)

    duplicate_event = append_event(
        connection,
        _journal_entry_posted_event(event_id="evt-journal-duplicate"),
    )

    with pytest.raises(ValidationError, match="duplicate journal_entry_id"):
        apply_event(connection, duplicate_event)


def test_applying_journal_entry_posted_rejects_missing_accounts(connection):
    event = append_event(
        connection,
        _journal_entry_posted_event(cash_account_id="acct-missing"),
    )

    with pytest.raises(ValidationError, match="missing account"):
        apply_event(connection, event)


def test_applying_journal_entry_posted_does_not_write_account_balances(
    connection,
):
    event = append_event(connection, _journal_entry_posted_event())

    apply_event(connection, event)

    row_count = connection.execute(
        "SELECT COUNT(*) AS count FROM account_balances",
    ).fetchone()["count"]

    assert row_count == 0


def test_existing_account_opened_handler_behavior_still_works(tmp_path):
    conn = connect(tmp_path / "accounts.db")
    initialize_schema(conn)

    open_account(conn, _account("acct-test", "1010", "Test Cash"))

    row = conn.execute(
        """
        SELECT account_id, code, name
        FROM accounts
        WHERE account_id = ?
        """,
        ("acct-test",),
    ).fetchone()

    assert row["code"] == "1010"
    assert row["name"] == "Test Cash"


def test_unsupported_event_behavior_remains_consistent(connection):
    event = LedgerEvent(
        event_id="evt-unsupported",
        event_type="AccountClosed",
        event_version=1,
        event_timestamp=datetime.now(UTC).isoformat(),
        effective_date="2026-01-05",
        source="test",
        actor=None,
        correlation_id=None,
        causation_id=None,
        payload={"account_id": "acct-cash"},
        created_at=datetime.now(UTC).isoformat(),
    )

    with pytest.raises(ValidationError, match="unsupported event type"):
        apply_event(connection, event)


def test_lookup_helper_returns_posted_journal_entry_by_id(connection):
    post_journal_entry(connection, _journal_entry())

    entry = get_journal_entry_by_id(connection, "je-1")

    assert entry is not None
    assert entry.journal_entry_id == "je-1"
    assert entry.description == "Record service revenue"


def test_lookup_helper_returns_lines_in_line_number_order(connection):
    post_journal_entry(connection, _journal_entry())

    entry = get_journal_entry_by_id(connection, "je-1")

    assert entry is not None
    assert [line.line_number for line in entry.lines] == [1, 2]


def test_list_helper_returns_entries_in_stable_order(connection):
    post_journal_entry(
        connection,
        _journal_entry(journal_entry_id="je-2", entry_date=date(2026, 1, 6)),
    )
    post_journal_entry(
        connection,
        _journal_entry(journal_entry_id="je-1", entry_date=date(2026, 1, 5)),
    )

    entries = list_journal_entries(connection)

    assert [entry.journal_entry_id for entry in entries] == ["je-1", "je-2"]


def _open_cash_and_revenue_accounts(connection):
    open_account(
        connection,
        _account(
            account_id="acct-cash",
            code="1000",
            name="Cash",
            account_type="asset",
            normal_balance="debit",
        ),
    )
    open_account(
        connection,
        _account(
            account_id="acct-revenue",
            code="4000",
            name="Service Revenue",
            account_type="revenue",
            normal_balance="credit",
        ),
    )


def _account(
    account_id: str,
    code: str,
    name: str,
    account_type: str = "asset",
    normal_balance: str = "debit",
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


def _journal_entry(
    journal_entry_id: str = "je-1",
    entry_date: date = date(2026, 1, 5),
    cash_account_id: str = "acct-cash",
    revenue_account_id: str = "acct-revenue",
    debit_amount: int = 10000,
    credit_amount: int = 10000,
) -> JournalEntry:
    return _make_journal_entry(
        journal_entry_id=journal_entry_id,
        entry_date=entry_date,
        lines=[
            JournalLine(
                line_id=f"{journal_entry_id}-line-1"
                if journal_entry_id != "je-1"
                else "jl-1",
                journal_entry_id=journal_entry_id,
                account_id=cash_account_id,
                side="debit",
                amount_cents=debit_amount,
                description="Cash received",
                line_number=1,
            ),
            JournalLine(
                line_id=f"{journal_entry_id}-line-2"
                if journal_entry_id != "je-1"
                else "jl-2",
                journal_entry_id=journal_entry_id,
                account_id=revenue_account_id,
                side="credit",
                amount_cents=credit_amount,
                description="Service revenue earned",
                line_number=2,
            ),
        ],
    )


def _make_journal_entry(
    *,
    journal_entry_id: str,
    lines: list[JournalLine],
    entry_date: date = date(2026, 1, 5),
) -> JournalEntry:
    try:
        return JournalEntry(
            journal_entry_id=journal_entry_id,
            entry_date=entry_date,
            description="Record service revenue",
            lines=lines,
            source="manual",
            external_reference="INV-1",
        )
    except TypeError:
        return JournalEntry(
            journal_entry_id=journal_entry_id,
            entry_date=entry_date,
            description="Record service revenue",
            lines=lines,
            external_reference="INV-1",
        )


def _journal_entry_posted_event(
    event_id: str = "evt-journal-1",
    cash_account_id: str = "acct-cash",
) -> LedgerEvent:
    timestamp = datetime.now(UTC).isoformat()
    return LedgerEvent(
        event_id=event_id,
        event_type="JournalEntryPosted",
        event_version=1,
        event_timestamp=timestamp,
        effective_date="2026-01-05",
        source="manual",
        actor=None,
        correlation_id=None,
        causation_id=None,
        payload={
            "journal_entry_id": "je-direct",
            "entry_date": "2026-01-05",
            "description": "Direct posted event",
            "source": "manual",
            "external_reference": "INV-DIRECT",
            "lines": [
                {
                    "line_id": "jl-direct-1",
                    "journal_entry_id": "je-direct",
                    "account_id": cash_account_id,
                    "side": "debit",
                    "amount_cents": 10000,
                    "description": "Cash received",
                    "line_number": 1,
                },
                {
                    "line_id": "jl-direct-2",
                    "journal_entry_id": "je-direct",
                    "account_id": "acct-revenue",
                    "side": "credit",
                    "amount_cents": 10000,
                    "description": "Revenue earned",
                    "line_number": 2,
                },
            ],
        },
        created_at=timestamp,
    )


def _event_count(connection) -> int:
    return connection.execute(
        "SELECT COUNT(*) AS count FROM ledger_events",
    ).fetchone()["count"]
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from reconcile.accounts.chart import open_accounts
from reconcile.accounts.models import Account
from reconcile.accounts.service import (
    get_account_by_code,
    get_account_by_id,
    list_accounts,
    open_account,
)
from reconcile.db import connect, initialize_schema
from reconcile.events.handlers import apply_event
from reconcile.events.models import LedgerEvent
from reconcile.events.store import load_events
from reconcile.exceptions import ValidationError


def _connection(tmp_path):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)
    return connection


def _account(
    account_id: str = "acct-cash",
    code: str = "1000",
    name: str = "Cash",
    account_type: str = "asset",
    normal_balance: str = "debit",
    is_active: bool = True,
    opened_at: str = "2026-01-01T00:00:00+00:00",
    closed_at: str | None = None,
) -> Account:
    return Account(
        account_id=account_id,
        code=code,
        name=name,
        account_type=account_type,
        normal_balance=normal_balance,
        is_active=is_active,
        opened_at=opened_at,
        closed_at=closed_at,
    )


def _event(
    event_type: str = "AccountOpened",
    payload: dict[str, object] | None = None,
) -> LedgerEvent:
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    return LedgerEvent(
        event_id="evt-test-account-opened",
        event_type=event_type,
        event_version=1,
        event_timestamp=timestamp,
        effective_date="2026-01-01",
        source="test",
        actor=None,
        correlation_id=None,
        causation_id=None,
        payload=payload if payload is not None else _payload(_account()),
        created_at=timestamp,
    )


def _payload(account: Account) -> dict[str, object]:
    return {
        "account_id": account.account_id,
        "code": account.code,
        "name": account.name,
        "account_type": account.account_type,
        "normal_balance": account.normal_balance,
        "is_active": account.is_active,
        "opened_at": account.opened_at,
        "closed_at": account.closed_at,
    }


def _table_count(connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])


def test_open_account_appends_account_opened_event(tmp_path):
    connection = _connection(tmp_path)
    account = _account()

    open_account(connection, account, source="test")

    events = load_events(connection)
    assert len(events) == 1
    assert events[0].event_type == "AccountOpened"
    assert events[0].event_version == 1
    assert events[0].effective_date == "2026-01-01"
    assert events[0].source == "test"


def test_open_account_inserts_account_projection_row(tmp_path):
    connection = _connection(tmp_path)
    account = _account(closed_at="2026-12-31T00:00:00+00:00")

    returned_account = open_account(connection, account)

    row = connection.execute(
        "SELECT * FROM accounts WHERE account_id = ?",
        (account.account_id,),
    ).fetchone()
    assert row is not None
    assert row["account_id"] == account.account_id
    assert row["code"] == "1000"
    assert row["name"] == "Cash"
    assert row["account_type"] == "asset"
    assert row["normal_balance"] == "debit"
    assert row["is_active"] == 1
    assert row["opened_at"] == "2026-01-01T00:00:00+00:00"
    assert row["closed_at"] == "2026-12-31T00:00:00+00:00"
    assert returned_account == account


def test_open_account_stores_inactive_account_active_flag_as_zero(tmp_path):
    connection = _connection(tmp_path)
    account = _account(
        is_active=False,
        closed_at="2026-12-31T00:00:00+00:00",
    )

    open_account(connection, account)

    row = connection.execute("SELECT is_active FROM accounts").fetchone()
    assert row["is_active"] == 0


def test_duplicate_account_code_fails_before_event_append(tmp_path):
    connection = _connection(tmp_path)
    open_account(connection, _account(account_id="acct-cash", code="1000"))

    with pytest.raises(ValidationError, match="account code already exists"):
        open_account(connection, _account(account_id="acct-cash-2", code="1000"))

    assert len(load_events(connection)) == 1


def test_duplicate_account_id_fails_before_event_append(tmp_path):
    connection = _connection(tmp_path)
    open_account(connection, _account(account_id="acct-cash", code="1000"))

    with pytest.raises(ValidationError, match="account_id already exists"):
        open_account(connection, _account(account_id="acct-cash", code="1010"))

    assert len(load_events(connection)) == 1


def test_invalid_account_data_fails_before_event_append(tmp_path):
    connection = _connection(tmp_path)

    with pytest.raises(ValidationError, match="account must be an Account"):
        open_account(connection, object())  # type: ignore[arg-type]

    assert load_events(connection) == []
    assert _table_count(connection, "accounts") == 0


def test_account_opened_payload_contains_rebuild_fields(tmp_path):
    connection = _connection(tmp_path)
    account = _account()

    open_account(connection, account)

    event = load_events(connection)[0]
    assert event.payload == _payload(account)


def test_apply_event_can_apply_valid_account_opened_event_directly(tmp_path):
    connection = _connection(tmp_path)
    event = _event()

    apply_event(connection, event)

    projected = get_account_by_id(connection, "acct-cash")
    assert projected == _account()
    assert _table_count(connection, "ledger_events") == 0


def test_apply_event_rejects_unsupported_event_types(tmp_path):
    connection = _connection(tmp_path)
    event = _event(
        event_type="JournalEntryPosted",
        payload={"journal_entry_id": "je-1"},
    )

    with pytest.raises(ValidationError, match="unsupported event type"):
        apply_event(connection, event)


def test_apply_event_rejects_missing_account_opened_payload_fields(tmp_path):
    connection = _connection(tmp_path)
    payload = _payload(_account())
    payload.pop("normal_balance")
    event = _event(payload=payload)

    with pytest.raises(ValidationError, match="missing fields"):
        apply_event(connection, event)


def test_apply_event_duplicate_account_code_fails_clearly(tmp_path):
    connection = _connection(tmp_path)
    apply_event(connection, _event())
    duplicate = _event(
        payload=_payload(_account(account_id="acct-cash-2", code="1000")),
    )

    with pytest.raises(ValidationError, match="account code already exists"):
        apply_event(connection, duplicate)


def test_apply_event_duplicate_account_id_fails_clearly(tmp_path):
    connection = _connection(tmp_path)
    apply_event(connection, _event())
    duplicate = _event(
        payload=_payload(_account(account_id="acct-cash", code="1010")),
    )

    with pytest.raises(ValidationError, match="account_id already exists"):
        apply_event(connection, duplicate)


def test_applying_account_opened_does_not_write_other_projection_tables(tmp_path):
    connection = _connection(tmp_path)

    apply_event(connection, _event())

    assert _table_count(connection, "journal_entries") == 0
    assert _table_count(connection, "journal_entry_lines") == 0
    assert _table_count(connection, "account_balances") == 0
    assert _table_count(connection, "bank_statement_imports") == 0
    assert _table_count(connection, "bank_transactions") == 0
    assert _table_count(connection, "reconciliation_runs") == 0
    assert _table_count(connection, "reconciliation_matches") == 0
    assert _table_count(connection, "reconciliation_match_ledger_links") == 0


def test_lookup_helpers_return_accounts_by_id_and_code(tmp_path):
    connection = _connection(tmp_path)
    account = _account()
    open_account(connection, account)

    assert get_account_by_id(connection, "acct-cash") == account
    assert get_account_by_code(connection, "1000") == account


def test_lookup_helpers_return_none_for_missing_accounts(tmp_path):
    connection = _connection(tmp_path)

    assert get_account_by_id(connection, "missing") is None
    assert get_account_by_code(connection, "9999") is None


def test_lookup_helpers_reject_blank_inputs(tmp_path):
    connection = _connection(tmp_path)

    with pytest.raises(ValidationError, match="account_id cannot be blank"):
        get_account_by_id(connection, " ")
    with pytest.raises(ValidationError, match="code cannot be blank"):
        get_account_by_code(connection, "")


def test_list_accounts_returns_accounts_in_code_order(tmp_path):
    connection = _connection(tmp_path)
    revenue = _account(
        account_id="acct-revenue",
        code="4000",
        name="Service Revenue",
        account_type="revenue",
        normal_balance="credit",
    )
    cash = _account(account_id="acct-cash", code="1000")

    open_account(connection, revenue)
    open_account(connection, cash)

    assert list_accounts(connection) == [cash, revenue]


def test_open_accounts_opens_multiple_accounts(tmp_path):
    connection = _connection(tmp_path)
    accounts = [
        _account(account_id="acct-cash", code="1000"),
        _account(
            account_id="acct-revenue",
            code="4000",
            name="Service Revenue",
            account_type="revenue",
            normal_balance="credit",
        ),
    ]

    opened = open_accounts(connection, accounts, source="test")

    assert opened == accounts
    assert len(load_events(connection)) == 2
    assert [account.code for account in list_accounts(connection)] == ["1000", "4000"]


def test_open_account_returns_separate_validated_account_instance(tmp_path):
    connection = _connection(tmp_path)
    account = _account()

    opened = open_account(connection, replace(account))

    assert opened == account

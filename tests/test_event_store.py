from __future__ import annotations

import sqlite3

import pytest

from reconcile.db import connect, initialize_schema
from reconcile.events.models import ACCOUNT_OPENED, JOURNAL_ENTRY_POSTED, LedgerEvent
from reconcile.events.store import (
    append_event,
    load_event_by_id,
    load_events,
    load_events_by_type,
)
from reconcile.exceptions import ValidationError


def make_connection(tmp_path):
    db_path = tmp_path / "reconcile.db"
    connection = connect(db_path)
    initialize_schema(connection)
    return connection


def make_event(
    event_id: str = "evt-001",
    event_type: str = ACCOUNT_OPENED,
    payload: dict | None = None,
) -> LedgerEvent:
    return LedgerEvent(
        event_id=event_id,
        event_type=event_type,
        event_version=1,
        event_timestamp="2026-01-01T10:00:00",
        effective_date="2026-01-01",
        source="test",
        payload=payload or {"account_id": "acct-001", "code": "1000"},
    )


def test_creating_valid_ledger_event():
    event = make_event()

    assert event.event_id == "evt-001"
    assert event.event_type == ACCOUNT_OPENED
    assert event.event_sequence is None


def test_ledger_event_rejects_blank_event_id():
    with pytest.raises(ValidationError, match="event_id cannot be blank"):
        make_event(event_id=" ")


def test_ledger_event_rejects_blank_event_type():
    with pytest.raises(ValidationError, match="event_type cannot be blank"):
        make_event(event_type=" ")


@pytest.mark.parametrize("event_version", [0, -1, "1", 1.5])
def test_ledger_event_rejects_invalid_event_version(event_version):
    with pytest.raises(ValidationError, match="event_version"):
        LedgerEvent(
            event_id="evt-001",
            event_type=ACCOUNT_OPENED,
            event_version=event_version,
            event_timestamp="2026-01-01T10:00:00",
            effective_date="2026-01-01",
            source="test",
            payload={},
        )


def test_ledger_event_rejects_bool_event_version():
    with pytest.raises(ValidationError, match="event_version"):
        LedgerEvent(
            event_id="evt-001",
            event_type=ACCOUNT_OPENED,
            event_version=True,
            event_timestamp="2026-01-01T10:00:00",
            effective_date="2026-01-01",
            source="test",
            payload={},
        )


def test_ledger_event_rejects_blank_event_timestamp():
    with pytest.raises(ValidationError, match="event_timestamp cannot be blank"):
        LedgerEvent(
            event_id="evt-001",
            event_type=ACCOUNT_OPENED,
            event_version=1,
            event_timestamp=" ",
            effective_date="2026-01-01",
            source="test",
            payload={},
        )


def test_ledger_event_rejects_blank_effective_date():
    with pytest.raises(ValidationError, match="effective_date cannot be blank"):
        LedgerEvent(
            event_id="evt-001",
            event_type=ACCOUNT_OPENED,
            event_version=1,
            event_timestamp="2026-01-01T10:00:00",
            effective_date=" ",
            source="test",
            payload={},
        )


def test_ledger_event_rejects_blank_source():
    with pytest.raises(ValidationError, match="source cannot be blank"):
        LedgerEvent(
            event_id="evt-001",
            event_type=ACCOUNT_OPENED,
            event_version=1,
            event_timestamp="2026-01-01T10:00:00",
            effective_date="2026-01-01",
            source=" ",
            payload={},
        )


def test_ledger_event_rejects_non_dict_payload():
    with pytest.raises(ValidationError, match="payload must be a dict"):
        LedgerEvent(
            event_id="evt-001",
            event_type=ACCOUNT_OPENED,
            event_version=1,
            event_timestamp="2026-01-01T10:00:00",
            effective_date="2026-01-01",
            source="test",
            payload=["bad"],
        )


def test_ledger_event_rejects_non_json_serializable_payload():
    with pytest.raises(ValidationError, match="payload must be JSON-serializable"):
        LedgerEvent(
            event_id="evt-001",
            event_type=ACCOUNT_OPENED,
            event_version=1,
            event_timestamp="2026-01-01T10:00:00",
            effective_date="2026-01-01",
            source="test",
            payload={"bad": object()},
        )


@pytest.mark.parametrize("field_name", ["actor", "correlation_id", "causation_id"])
def test_ledger_event_rejects_blank_optional_strings(field_name):
    kwargs = {field_name: " "}

    with pytest.raises(ValidationError, match=field_name):
        LedgerEvent(
            event_id="evt-001",
            event_type=ACCOUNT_OPENED,
            event_version=1,
            event_timestamp="2026-01-01T10:00:00",
            effective_date="2026-01-01",
            source="test",
            payload={},
            **kwargs,
        )


@pytest.mark.parametrize("event_sequence", [0, -1, "1", 1.5])
def test_ledger_event_rejects_invalid_event_sequence(event_sequence):
    with pytest.raises(ValidationError, match="event_sequence"):
        LedgerEvent(
            event_id="evt-001",
            event_type=ACCOUNT_OPENED,
            event_version=1,
            event_timestamp="2026-01-01T10:00:00",
            effective_date="2026-01-01",
            source="test",
            payload={},
            event_sequence=event_sequence,
        )


def test_ledger_event_rejects_bool_event_sequence():
    with pytest.raises(ValidationError, match="event_sequence"):
        LedgerEvent(
            event_id="evt-001",
            event_type=ACCOUNT_OPENED,
            event_version=1,
            event_timestamp="2026-01-01T10:00:00",
            effective_date="2026-01-01",
            source="test",
            payload={},
            event_sequence=True,
        )


def test_append_event_inserts_one_event(tmp_path):
    connection = make_connection(tmp_path)

    append_event(connection, make_event())

    rows = connection.execute("SELECT COUNT(*) AS count FROM ledger_events").fetchone()
    assert rows["count"] == 1


def test_appended_event_receives_sequence_one(tmp_path):
    connection = make_connection(tmp_path)

    stored_event = append_event(connection, make_event())

    assert stored_event.event_sequence == 1


def test_appending_two_events_produces_increasing_sequences(tmp_path):
    connection = make_connection(tmp_path)

    first = append_event(connection, make_event(event_id="evt-001"))
    second = append_event(connection, make_event(event_id="evt-002"))

    assert first.event_sequence == 1
    assert second.event_sequence == 2


def test_load_events_returns_events_ordered_by_sequence(tmp_path):
    connection = make_connection(tmp_path)
    append_event(connection, make_event(event_id="evt-001"))
    append_event(connection, make_event(event_id="evt-002"))

    events = load_events(connection)

    assert [event.event_id for event in events] == ["evt-001", "evt-002"]
    assert [event.event_sequence for event in events] == [1, 2]


def test_loaded_events_preserve_payload_data(tmp_path):
    connection = make_connection(tmp_path)
    payload = {"account_id": "acct-001", "nested": {"amount": 1000}}

    append_event(connection, make_event(payload=payload))

    loaded_event = load_events(connection)[0]
    assert loaded_event.payload == payload


def test_duplicate_event_id_fails_clearly(tmp_path):
    connection = make_connection(tmp_path)
    append_event(connection, make_event(event_id="evt-001"))

    with pytest.raises(ValidationError, match="event_id must be unique"):
        append_event(connection, make_event(event_id="evt-001"))


def test_append_event_commits_inserted_event(tmp_path):
    db_path = tmp_path / "reconcile.db"
    connection = connect(db_path)
    initialize_schema(connection)

    append_event(connection, make_event())

    second_connection = connect(db_path)
    try:
        loaded_events = load_events(second_connection)
        assert len(loaded_events) == 1
        assert loaded_events[0].event_id == "evt-001"
    finally:
        second_connection.close()


def test_load_events_returns_empty_list_when_no_events_exist(tmp_path):
    connection = make_connection(tmp_path)

    assert load_events(connection) == []


def test_load_event_by_id_returns_found_event(tmp_path):
    connection = make_connection(tmp_path)
    append_event(connection, make_event(event_id="evt-001"))

    event = load_event_by_id(connection, "evt-001")

    assert event is not None
    assert event.event_id == "evt-001"


def test_load_event_by_id_returns_none_for_missing_event(tmp_path):
    connection = make_connection(tmp_path)

    assert load_event_by_id(connection, "missing") is None


def test_load_events_by_type_filters_and_preserves_sequence_order(tmp_path):
    connection = make_connection(tmp_path)
    append_event(connection, make_event(event_id="evt-001", event_type=ACCOUNT_OPENED))
    append_event(
        connection,
        make_event(event_id="evt-002", event_type=JOURNAL_ENTRY_POSTED),
    )
    append_event(connection, make_event(event_id="evt-003", event_type=ACCOUNT_OPENED))

    events = load_events_by_type(connection, ACCOUNT_OPENED)

    assert [event.event_id for event in events] == ["evt-001", "evt-003"]


def test_append_event_does_not_create_projection_rows(tmp_path):
    connection = make_connection(tmp_path)

    append_event(connection, make_event())

    table_names = [
        "accounts",
        "journal_entries",
        "journal_entry_lines",
        "account_balances",
        "bank_statement_imports",
        "bank_transactions",
        "reconciliation_runs",
        "reconciliation_matches",
        "reconciliation_match_ledger_links",
    ]

    for table_name in table_names:
        row = connection.execute(
            f"SELECT COUNT(*) AS count FROM {table_name}"
        ).fetchone()
        assert row["count"] == 0


def test_append_event_allows_plain_sqlite_connection_with_initialized_schema(tmp_path):
    db_path = tmp_path / "plain.db"
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    initialize_schema(connection)

    stored_event = append_event(connection, make_event())

    assert stored_event.event_sequence == 1
from __future__ import annotations

import copy
import sqlite3

import pytest

from reconcile.categorization.corrections import (
    apply_corrections_to_categorized_results,
    initialize_categorization_schema,
    latest_category_correction,
    list_category_corrections,
    record_category_correction,
    training_examples_from_corrections,
)
from reconcile.db import initialize_schema
from reconcile.exceptions import ValidationError


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    initialize_schema(connection)
    initialize_categorization_schema(connection)
    return connection


def insert_bank_transaction(
    connection: sqlite3.Connection,
    bank_transaction_id: str,
    *,
    description_raw: str = "RAW DESCRIPTION",
    description_normalized: str | None = "normalized description",
    amount_cents: int = -1200,
) -> None:
    connection.execute(
        """
        INSERT INTO bank_statement_imports (
            import_id,
            source_name,
            file_name,
            file_hash,
            imported_at,
            row_count
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("import-1", "test", "bank.csv", "hash", "2026-01-01T00:00:00+00:00", 1),
    )
    connection.execute(
        """
        INSERT INTO bank_transactions (
            bank_transaction_id,
            import_id,
            transaction_date,
            posted_date,
            description_raw,
            description_normalized,
            amount_cents,
            external_id,
            check_number,
            row_hash,
            duplicate_group_id,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            bank_transaction_id,
            "import-1",
            "2026-01-01",
            "2026-01-02",
            description_raw,
            description_normalized,
            amount_cents,
            None,
            None,
            f"hash-{bank_transaction_id}",
            None,
            "2026-01-01T00:00:00+00:00",
        ),
    )
    connection.commit()


def insert_second_bank_transaction(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO bank_transactions (
            bank_transaction_id,
            import_id,
            transaction_date,
            posted_date,
            description_raw,
            description_normalized,
            amount_cents,
            external_id,
            check_number,
            row_hash,
            duplicate_group_id,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "bank-2",
            "import-1",
            "2026-01-03",
            None,
            "RAW SECOND",
            "normalized second",
            4500,
            None,
            None,
            "hash-bank-2",
            None,
            "2026-01-01T00:00:00+00:00",
        ),
    )
    connection.commit()


def event_count(connection: sqlite3.Connection) -> int:
    return connection.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]


def bank_row(
    connection: sqlite3.Connection, 
    bank_transaction_id: str,
) -> dict[str, object]:
    row = connection.execute(
        "SELECT * FROM bank_transactions WHERE bank_transaction_id = ?",
        (bank_transaction_id,),
    ).fetchone()
    return dict(row)


def test_schema_initialization_creates_category_corrections_table() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    initialize_schema(connection)

    initialize_categorization_schema(connection)

    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'category_corrections'
        """
    ).fetchone()
    assert row["name"] == "category_corrections"


def test_schema_initialization_is_idempotent() -> None:
    connection = make_connection()

    initialize_categorization_schema(connection)
    initialize_categorization_schema(connection)

    assert list_category_corrections(connection) == []


def test_record_category_correction_for_existing_bank_transaction() -> None:
    connection = make_connection()
    insert_bank_transaction(connection, "bank-1")

    correction = record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Software",
        corrected_by="Nathan",
        reason="Actual subscription",
        corrected_at="2026-01-05T10:00:00+00:00",
    )

    assert correction["correction_id"]
    assert correction["bank_transaction_id"] == "bank-1"
    assert correction["corrected_category"] == "Software"
    assert correction["corrected_at"] == "2026-01-05T10:00:00+00:00"
    assert correction["created_at"]
    assert correction["corrected_by"] == "Nathan"
    assert correction["reason"] == "Actual subscription"


def test_record_category_correction_populates_timestamps_when_omitted() -> None:
    connection = make_connection()
    insert_bank_transaction(connection, "bank-1")

    correction = record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Meals",
    )

    assert correction["corrected_at"]
    assert correction["created_at"]


def test_multiple_corrections_for_same_transaction_are_append_only() -> None:
    connection = make_connection()
    insert_bank_transaction(connection, "bank-1")

    first = record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Meals",
        corrected_at="2026-01-01T00:00:00+00:00",
    )
    second = record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Software",
        corrected_at="2026-01-02T00:00:00+00:00",
    )

    corrections = list_category_corrections(connection)
    assert [row["correction_id"] for row in corrections] == [
        first["correction_id"],
        second["correction_id"],
    ]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"bank_transaction_id": "missing", "corrected_category": "Meals"}, "existing"),
        (
            {"bank_transaction_id": " ", "corrected_category": "Meals"}, 
            "bank_transaction_id"),
        (
            {"bank_transaction_id": "bank-1", "corrected_category": " "}, 
            "corrected_category"),
        (
            {
                "bank_transaction_id": "bank-1",
                "corrected_category": "Meals",
                "corrected_by": " ",
            },
            "corrected_by",
        ),
        (
            {
                "bank_transaction_id": "bank-1",
                "corrected_category": "Meals",
                "reason": " ",
            },
            "reason",
        ),
        (
            {
                "bank_transaction_id": "bank-1",
                "corrected_category": "Meals",
                "corrected_at": "not a timestamp",
            },
            "corrected_at",
        ),
    ],
)
def test_record_category_correction_validation_errors(
    kwargs: dict[str, object], message: str
) -> None:
    connection = make_connection()
    insert_bank_transaction(connection, "bank-1")

    with pytest.raises(ValidationError, match=message):
        record_category_correction(connection, **kwargs)  # type: ignore[arg-type]


def test_list_all_corrections_and_list_for_one_bank_transaction() -> None:
    connection = make_connection()
    insert_bank_transaction(connection, "bank-1")
    insert_second_bank_transaction(connection)
    first = record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Software",
        corrected_at="2026-01-01T00:00:00+00:00",
    )
    second = record_category_correction(
        connection,
        bank_transaction_id="bank-2",
        corrected_category="Revenue",
        corrected_at="2026-01-02T00:00:00+00:00",
    )

    assert [row["correction_id"] for row in list_category_corrections(connection)] == [
        first["correction_id"],
        second["correction_id"],
    ]
    assert [
        row["correction_id"]
        for row in list_category_corrections(connection, bank_transaction_id="bank-2")
    ] == [second["correction_id"]]


def test_list_category_corrections_rejects_blank_filter() -> None:
    connection = make_connection()

    with pytest.raises(ValidationError, match="bank_transaction_id"):
        list_category_corrections(connection, bank_transaction_id=" ")


def test_latest_category_correction_returns_newest_or_none() -> None:
    connection = make_connection()
    insert_bank_transaction(connection, "bank-1")
    first = record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Meals",
        corrected_at="2026-01-01T00:00:00+00:00",
    )
    second = record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Software",
        corrected_at="2026-01-02T00:00:00+00:00",
    )

    latest = latest_category_correction(connection, "bank-1")

    assert latest is not None
    assert latest["correction_id"] != first["correction_id"]
    assert latest["correction_id"] == second["correction_id"]
    assert latest_category_correction(connection, "missing") is None


def test_latest_category_correction_rejects_blank_bank_transaction_id() -> None:
    connection = make_connection()

    with pytest.raises(ValidationError, match="bank_transaction_id"):
        latest_category_correction(connection, " ")


def test_training_examples_join_corrections_to_bank_transactions() -> None:
    connection = make_connection()
    insert_bank_transaction(
        connection,
        "bank-1",
        description_raw="POS RAW SOFTWARE",
        description_normalized="pos raw software",
        amount_cents=-1299,
    )
    insert_second_bank_transaction(connection)
    correction = record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Software",
        corrected_at="2026-01-01T00:00:00+00:00",
    )

    examples = training_examples_from_corrections(connection)

    assert examples == [
        {
            "correction_id": correction["correction_id"],
            "bank_transaction_id": "bank-1",
            "text": "pos raw software",
            "description_raw": "POS RAW SOFTWARE",
            "description_normalized": "pos raw software",
            "amount_cents": -1299,
            "category": "Software",
            "corrected_at": "2026-01-01T00:00:00+00:00",
        }
    ]


def test_training_examples_fall_back_to_raw_description() -> None:
    connection = make_connection()
    insert_bank_transaction(
        connection,
        "bank-1",
        description_raw="RAW ONLY",
        description_normalized=None,
    )
    record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Office Supplies",
    )

    [example] = training_examples_from_corrections(connection)

    assert example["text"] == "RAW ONLY"


def test_training_examples_are_deterministically_ordered() -> None:
    connection = make_connection()
    insert_bank_transaction(connection, "bank-1")
    insert_second_bank_transaction(connection)
    second = record_category_correction(
        connection,
        bank_transaction_id="bank-2",
        corrected_category="Revenue",
        corrected_at="2026-01-02T00:00:00+00:00",
    )
    first = record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Software",
        corrected_at="2026-01-01T00:00:00+00:00",
    )

    examples = training_examples_from_corrections(connection)

    assert [example["correction_id"] for example in examples] == [
        first["correction_id"],
        second["correction_id"],
    ]


def test_apply_corrections_latest_override_and_preserve_order() -> None:
    categorized = [
        {
            "bank_transaction_id": "bank-1",
            "category": "Meals",
            "category_source": "rule",
            "category_rule_id": "rule-meals",
            "category_reason": "Rule matched",
            "matched_rule_priority": 10,
            "matched_description": "software",
            "amount_cents": -1000,
        },
        {
            "bank_transaction_id": "bank-2",
            "category": None,
            "category_source": None,
            "category_rule_id": None,
            "category_reason": "No rule matched",
            "matched_rule_priority": None,
            "matched_description": "other",
            "amount_cents": -500,
        },
    ]
    corrections = [
        {
            "correction_id": "corr-1",
            "bank_transaction_id": "bank-1",
            "corrected_category": "Old Category",
            "reason": "old",
            "corrected_at": "2026-01-01T00:00:00+00:00",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        {
            "correction_id": "corr-2",
            "bank_transaction_id": "bank-1",
            "corrected_category": "Software",
            "reason": "new",
            "corrected_at": "2026-01-02T00:00:00+00:00",
            "created_at": "2026-01-02T00:00:00+00:00",
        },
    ]
    categorized_before = copy.deepcopy(categorized)
    corrections_before = copy.deepcopy(corrections)

    output = apply_corrections_to_categorized_results(categorized, corrections)

    assert [row["bank_transaction_id"] for row in output] == ["bank-1", "bank-2"]
    assert output[0]["category"] == "Software"
    assert output[0]["category_source"] == "correction"
    assert output[0]["category_rule_id"] is None
    assert output[0]["correction_id"] == "corr-2"
    assert output[0]["corrected_at"] == "2026-01-02T00:00:00+00:00"
    assert output[1] == categorized[1]
    assert output[1] is not categorized[1]
    assert categorized == categorized_before
    assert corrections == corrections_before


def test_correction_listing_and_training_do_not_append_ledger_events() -> None:
    connection = make_connection()
    insert_bank_transaction(connection, "bank-1")
    record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Software",
    )
    before = event_count(connection)

    list_category_corrections(connection)
    training_examples_from_corrections(connection)

    assert event_count(connection) == before


def test_apply_corrections_does_not_touch_database() -> None:
    connection = make_connection()
    before = event_count(connection)

    apply_corrections_to_categorized_results([], [])

    assert event_count(connection) == before


def test_correction_storage_does_not_mutate_bank_transaction_rows() -> None:
    connection = make_connection()
    insert_bank_transaction(connection, "bank-1")
    before = bank_row(connection, "bank-1")

    record_category_correction(
        connection,
        bank_transaction_id="bank-1",
        corrected_category="Software",
    )

    assert bank_row(connection, "bank-1") == before

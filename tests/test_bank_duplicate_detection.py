from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

from reconcile.db import connect, initialize_schema
from reconcile.exceptions import ValidationError
from reconcile.imports.bank_csv import import_bank_statement_csv
from reconcile.imports.duplicate_detection import (
    detect_duplicate_bank_transactions,
    mark_duplicate_bank_transactions,
)


def _connection(tmp_path: Path) -> sqlite3.Connection:
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)
    return connection


def _write_csv(tmp_path: Path, name: str, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / name
    fieldnames = [
        "transaction_date",
        "posted_date",
        "description",
        "amount",
        "external_id",
        "check_number",
    ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return path


def _import_csv(
    connection: sqlite3.Connection,
    tmp_path: Path,
    rows: list[dict[str, str]],
    *,
    name: str = "bank.csv",
) -> str:
    path = _write_csv(tmp_path, name, rows)
    return import_bank_statement_csv(
        connection,
        path,
        source_name="Test Bank",
    )


def _bank_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT *
            FROM bank_transactions
            ORDER BY transaction_date, bank_transaction_id
            """
        ).fetchall()
    )


def _duplicate_group_ids(connection: sqlite3.Connection) -> list[str | None]:
    return [
        row["duplicate_group_id"]
        for row in connection.execute(
            """
            SELECT duplicate_group_id
            FROM bank_transactions
            ORDER BY transaction_date, bank_transaction_id
            """
        ).fetchall()
    ]


def _insert_bank_transaction(
    connection: sqlite3.Connection,
    *,
    bank_transaction_id: str,
    import_id: str = "manual-import",
    transaction_date: str = "2026-01-01",
    posted_date: str | None = "2026-01-01",
    description_raw: str = "RAW DESCRIPTION",
    description_normalized: str = "raw description",
    amount_cents: int = -1000,
    external_id: str | None = None,
    check_number: str | None = None,
    row_hash: str = "row-hash",
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO bank_statement_imports (
            import_id,
            source_name,
            file_name,
            file_hash,
            imported_at,
            row_count
        )
        VALUES (?, 'Manual', 'manual.csv', NULL, '2026-01-01T00:00:00', 0)
        """,
        (import_id,),
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
        """,
        (
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
            "2026-01-01T00:00:00",
        ),
    )
    connection.commit()


def test_same_imported_row_produces_row_hash_duplicate_group(tmp_path):
    connection = _connection(tmp_path)

    _import_csv(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-01",
                "posted_date": "2026-01-01",
                "description": "POS SOFTWARE SUBSCRIPTION",
                "amount": "-50.00",
                "external_id": "BANK-001",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-01",
                "posted_date": "2026-01-01",
                "description": "POS SOFTWARE SUBSCRIPTION",
                "amount": "-50.00",
                "external_id": "BANK-001",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-02",
                "posted_date": "2026-01-02",
                "description": "DEPOSIT OWNER CONTRIBUTION",
                "amount": "5000.00",
                "external_id": "BANK-002",
                "check_number": "",
            },
        ],
    )

    rows = _bank_rows(connection)
    duplicate_group_ids = [row["duplicate_group_id"] for row in rows]

    assert duplicate_group_ids[0] is not None
    assert duplicate_group_ids[1] == duplicate_group_ids[0]
    assert duplicate_group_ids[2] is None


def test_row_hash_detection_returns_duplicate_reason(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        row_hash="same-row-hash",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        row_hash="same-row-hash",
    )

    duplicates = detect_duplicate_bank_transactions(connection)

    assert {row["duplicate_reason"] for row in duplicates} == {"row_hash"}
    assert all(
        str(row["duplicate_group_id"]).startswith("dup-row-hash-")
        for row in duplicates
    )


def test_external_id_duplicates_are_grouped(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        external_id="EXT-1",
        row_hash="hash-1",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        external_id="EXT-1",
        row_hash="hash-2",
    )

    duplicates = mark_duplicate_bank_transactions(connection)

    assert len(duplicates) == 2
    assert {row["duplicate_reason"] for row in duplicates} == {"external_id"}
    assert len({row["duplicate_group_id"] for row in duplicates}) == 1


def test_blank_and_null_external_ids_are_ignored(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        external_id="",
        row_hash="hash-1",
        description_normalized="first",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        external_id=" ",
        row_hash="hash-2",
        description_normalized="second",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-3",
        external_id=None,
        row_hash="hash-3",
        description_normalized="third",
    )

    duplicates = mark_duplicate_bank_transactions(connection)

    assert duplicates == []
    assert _duplicate_group_ids(connection) == [None, None, None]


def test_external_id_group_id_is_deterministic(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        external_id="EXT-1",
        row_hash="hash-1",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        external_id="EXT-1",
        row_hash="hash-2",
    )

    first = mark_duplicate_bank_transactions(connection)
    second = mark_duplicate_bank_transactions(connection)

    assert first == second


def test_fingerprint_duplicates_are_grouped(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        transaction_date="2026-01-01",
        amount_cents=-5000,
        description_normalized="software subscription",
        row_hash="hash-1",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        transaction_date="2026-01-01",
        amount_cents=-5000,
        description_normalized="software subscription",
        row_hash="hash-2",
    )

    duplicates = mark_duplicate_bank_transactions(connection)

    assert len(duplicates) == 2
    assert {row["duplicate_reason"] for row in duplicates} == {"fingerprint"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description_normalized", "different description"),
        ("amount_cents", -2500),
        ("transaction_date", "2026-01-02"),
    ],
)
def test_near_fingerprints_are_not_grouped(tmp_path, field, value):
    connection = _connection(tmp_path)

    first = {
        "bank_transaction_id": "bt-1",
        "transaction_date": "2026-01-01",
        "amount_cents": -5000,
        "description_normalized": "software subscription",
        "row_hash": "hash-1",
    }
    second = {
        "bank_transaction_id": "bt-2",
        "transaction_date": "2026-01-01",
        "amount_cents": -5000,
        "description_normalized": "software subscription",
        "row_hash": "hash-2",
    }
    second[field] = value

    _insert_bank_transaction(connection, **first)
    _insert_bank_transaction(connection, **second)

    assert mark_duplicate_bank_transactions(connection) == []


def test_row_hash_precedence_wins_over_fingerprint(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        transaction_date="2026-01-01",
        amount_cents=-5000,
        description_normalized="software subscription",
        row_hash="same-row-hash",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        transaction_date="2026-01-01",
        amount_cents=-5000,
        description_normalized="software subscription",
        row_hash="same-row-hash",
    )

    duplicates = mark_duplicate_bank_transactions(connection)

    assert {row["duplicate_reason"] for row in duplicates} == {"row_hash"}


def test_external_id_precedence_wins_over_fingerprint(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        external_id="EXT-1",
        transaction_date="2026-01-01",
        amount_cents=-5000,
        description_normalized="software subscription",
        row_hash="hash-1",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        external_id="EXT-1",
        transaction_date="2026-01-01",
        amount_cents=-5000,
        description_normalized="software subscription",
        row_hash="hash-2",
    )

    duplicates = mark_duplicate_bank_transactions(connection)

    assert {row["duplicate_reason"] for row in duplicates} == {"external_id"}
    assert all(
        str(row["duplicate_group_id"]).startswith("dup-external-id-")
        for row in duplicates
    )


def test_row_receives_only_one_duplicate_group_id(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        external_id="EXT-1",
        transaction_date="2026-01-01",
        amount_cents=-5000,
        description_normalized="software subscription",
        row_hash="hash-1",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        external_id="EXT-1",
        transaction_date="2026-01-01",
        amount_cents=-5000,
        description_normalized="software subscription",
        row_hash="hash-2",
    )

    duplicates = mark_duplicate_bank_transactions(connection)

    assert len(duplicates) == 2
    assert len({row["bank_transaction_id"] for row in duplicates}) == 2


def test_detect_does_not_mutate_database(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        row_hash="same-row-hash",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        row_hash="same-row-hash",
    )

    duplicates = detect_duplicate_bank_transactions(connection)

    assert len(duplicates) == 2
    assert _duplicate_group_ids(connection) == [None, None]


def test_mark_updates_duplicate_group_ids_and_returns_rows(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        row_hash="same-row-hash",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        row_hash="same-row-hash",
    )

    duplicates = mark_duplicate_bank_transactions(connection)

    assert len(duplicates) == 2
    assert _duplicate_group_ids(connection)[0] is not None
    assert _duplicate_group_ids(connection)[0] == _duplicate_group_ids(connection)[1]


def test_mark_is_idempotent(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        row_hash="same-row-hash",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        row_hash="same-row-hash",
    )

    first = mark_duplicate_bank_transactions(connection)
    second = mark_duplicate_bank_transactions(connection)

    assert first == second
    assert _duplicate_group_ids(connection)[0] == _duplicate_group_ids(connection)[1]


def test_mark_recalculates_after_adding_duplicate(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        transaction_date="2026-01-01",
        amount_cents=-1000,
        description_normalized="first transaction",
        row_hash="same-row-hash",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        transaction_date="2026-01-02",
        amount_cents=-2000,
        description_normalized="second transaction",
        row_hash="different-row-hash",
    )

    assert mark_duplicate_bank_transactions(connection) == []

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-3",
        transaction_date="2026-01-03",
        amount_cents=-3000,
        description_normalized="third transaction",
        row_hash="same-row-hash",
    )

    duplicates = mark_duplicate_bank_transactions(connection)

    assert {row["bank_transaction_id"] for row in duplicates} == {"bt-1", "bt-3"}
    assert {row["duplicate_reason"] for row in duplicates} == {"row_hash"}


def test_import_marks_duplicate_rows_after_import(tmp_path):
    connection = _connection(tmp_path)

    _import_csv(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-01",
                "posted_date": "2026-01-01",
                "description": "POS SOFTWARE SUBSCRIPTION",
                "amount": "-50.00",
                "external_id": "BANK-001",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-01",
                "posted_date": "2026-01-01",
                "description": "POS SOFTWARE SUBSCRIPTION",
                "amount": "-50.00",
                "external_id": "BANK-001",
                "check_number": "",
            },
        ],
    )

    assert _duplicate_group_ids(connection)[0] == _duplicate_group_ids(connection)[1]
    assert _duplicate_group_ids(connection)[0] is not None


def test_non_duplicate_import_leaves_group_ids_null(tmp_path):
    connection = _connection(tmp_path)

    _import_csv(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-01",
                "posted_date": "2026-01-01",
                "description": "POS SOFTWARE SUBSCRIPTION",
                "amount": "-50.00",
                "external_id": "BANK-001",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-02",
                "posted_date": "2026-01-02",
                "description": "DEPOSIT OWNER CONTRIBUTION",
                "amount": "5000.00",
                "external_id": "BANK-002",
                "check_number": "",
            },
        ],
    )

    assert _duplicate_group_ids(connection) == [None, None]


def test_duplicate_detection_can_be_scoped_to_one_import(tmp_path):
    connection = _connection(tmp_path)

    first_import_id = _import_csv(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-01",
                "posted_date": "2026-01-01",
                "description": "POS SOFTWARE SUBSCRIPTION",
                "amount": "-50.00",
                "external_id": "BANK-001",
                "check_number": "",
            },
        ],
        name="first.csv",
    )
    _import_csv(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-01",
                "posted_date": "2026-01-01",
                "description": "POS SOFTWARE SUBSCRIPTION",
                "amount": "-50.00",
                "external_id": "BANK-001",
                "check_number": "",
            },
        ],
        name="second.csv",
    )

    scoped = detect_duplicate_bank_transactions(
        connection,
        import_id=first_import_id,
    )
    global_duplicates = detect_duplicate_bank_transactions(connection)

    assert scoped == []
    assert len(global_duplicates) == 2


def test_duplicate_across_imports_is_detected_only_globally(tmp_path):
    connection = _connection(tmp_path)

    first_import_id = _import_csv(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-01",
                "posted_date": "2026-01-01",
                "description": "POS SOFTWARE SUBSCRIPTION",
                "amount": "-50.00",
                "external_id": "BANK-001",
                "check_number": "",
            },
        ],
        name="first.csv",
    )
    _import_csv(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-01",
                "posted_date": "2026-01-01",
                "description": "POS SOFTWARE SUBSCRIPTION",
                "amount": "-50.00",
                "external_id": "BANK-001",
                "check_number": "",
            },
        ],
        name="second.csv",
    )

    assert detect_duplicate_bank_transactions(
        connection,
        import_id=first_import_id,
    ) == []
    assert len(detect_duplicate_bank_transactions(connection)) == 2


def test_no_bank_transactions_returns_empty_duplicate_list(tmp_path):
    connection = _connection(tmp_path)

    assert detect_duplicate_bank_transactions(connection) == []
    assert mark_duplicate_bank_transactions(connection) == []


@pytest.mark.parametrize("bad_import_id", ["", "   "])
def test_blank_import_id_raises_validation_error(tmp_path, bad_import_id):
    connection = _connection(tmp_path)

    with pytest.raises(ValidationError, match="import_id cannot be blank"):
        detect_duplicate_bank_transactions(connection, import_id=bad_import_id)

    with pytest.raises(ValidationError, match="import_id cannot be blank"):
        mark_duplicate_bank_transactions(connection, import_id=bad_import_id)


def test_duplicate_detection_does_not_append_ledger_events(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        row_hash="same-row-hash",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        row_hash="same-row-hash",
    )

    before = connection.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]
    mark_duplicate_bank_transactions(connection)
    after = connection.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]

    assert before == 0
    assert after == 0


def test_duplicate_detection_does_not_modify_accounting_projection_tables(tmp_path):
    connection = _connection(tmp_path)

    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-1",
        row_hash="same-row-hash",
    )
    _insert_bank_transaction(
        connection,
        bank_transaction_id="bt-2",
        row_hash="same-row-hash",
    )

    before = {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in (
            "accounts",
            "journal_entries",
            "journal_entry_lines",
            "account_balances",
        )
    }

    mark_duplicate_bank_transactions(connection)

    after = {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in (
            "accounts",
            "journal_entries",
            "journal_entry_lines",
            "account_balances",
        )
    }

    assert after == before
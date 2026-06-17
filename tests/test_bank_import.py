from __future__ import annotations

import sqlite3

import pytest

from reconcile.db import connect, initialize_schema
from reconcile.exceptions import ValidationError
from reconcile.imports.bank_csv import (
    hash_bank_row,
    import_bank_statement_csv,
    read_bank_statement_csv,
)
from reconcile.imports.normalization import normalize_bank_description


def test_normalization_strips_whitespace():
    assert normalize_bank_description("  Deposit Owner Contribution  ") == (
        "DEPOSIT OWNER CONTRIBUTION"
    )


def test_normalization_collapses_repeated_whitespace():
    assert normalize_bank_description("POS SOFTWARE   SUBSCRIPTION") == (
        "POS SOFTWARE SUBSCRIPTION"
    )


def test_normalization_uppercases_text():
    assert normalize_bank_description("Deposit Owner Contribution") == (
        "DEPOSIT OWNER CONTRIBUTION"
    )


def test_normalization_handles_punctuation_deterministically():
    assert normalize_bank_description("CHECK #1001") == "CHECK 1001"


def test_blank_description_raises_validation_error():
    with pytest.raises(ValidationError, match="description cannot be blank"):
        normalize_bank_description("   ")


def test_non_string_description_raises_validation_error():
    with pytest.raises(ValidationError, match="description must be a string"):
        normalize_bank_description(123)  # type: ignore[arg-type]


def test_valid_csv_rows_are_read(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            "transaction_date,posted_date,description,amount,external_id,check_number",
            "2026-01-01,2026-01-01,Deposit Owner Contribution,5000.00,BANK-001,",
            "2026-01-06,,POS Software Subscription,-50.00,,",
        ],
    )

    rows = read_bank_statement_csv(csv_path)

    assert len(rows) == 2
    assert rows[0]["description"] == "Deposit Owner Contribution"
    assert rows[1]["amount"] == "-50.00"


def test_missing_required_columns_raise_validation_error(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            "transaction_date,description",
            "2026-01-01,Deposit Owner Contribution",
        ],
    )

    with pytest.raises(ValidationError, match="missing columns: amount"):
        read_bank_statement_csv(csv_path)


def test_missing_file_raises_validation_error(tmp_path):
    csv_path = tmp_path / "missing.csv"

    with pytest.raises(ValidationError, match="does not exist"):
        read_bank_statement_csv(csv_path)


def test_empty_csv_raises_validation_error(tmp_path):
    csv_path = _write_csv(tmp_path, [])

    with pytest.raises(ValidationError, match="CSV is empty"):
        read_bank_statement_csv(csv_path)


def test_header_only_csv_raises_validation_error(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        ["transaction_date,description,amount"],
    )

    with pytest.raises(ValidationError, match="headers but no data rows"):
        read_bank_statement_csv(csv_path)


def test_blank_transaction_date_raises_validation_error(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            "transaction_date,description,amount",
            ",Deposit Owner Contribution,5000.00",
        ],
    )

    with pytest.raises(ValidationError, match="transaction_date cannot be blank"):
        read_bank_statement_csv(csv_path)


def test_blank_description_raises_validation_error_when_reading_csv(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            "transaction_date,description,amount",
            "2026-01-01,   ,5000.00",
        ],
    )

    with pytest.raises(ValidationError, match="description cannot be blank"):
        read_bank_statement_csv(csv_path)


def test_blank_amount_raises_validation_error(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            "transaction_date,description,amount",
            "2026-01-01,Deposit Owner Contribution,",
        ],
    )

    with pytest.raises(ValidationError, match="amount cannot be blank"):
        read_bank_statement_csv(csv_path)


def test_invalid_transaction_date_raises_validation_error(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            "transaction_date,description,amount",
            "01/01/2026,Deposit Owner Contribution,5000.00",
        ],
    )

    with pytest.raises(ValidationError, match="transaction_date must be YYYY-MM-DD"):
        read_bank_statement_csv(csv_path)


def test_invalid_posted_date_raises_validation_error(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            "transaction_date,posted_date,description,amount",
            "2026-01-01,01/01/2026,Deposit Owner Contribution,5000.00",
        ],
    )

    with pytest.raises(ValidationError, match="posted_date must be YYYY-MM-DD"):
        read_bank_statement_csv(csv_path)


def test_invalid_amount_raises_validation_error(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            "transaction_date,description,amount",
            "2026-01-01,Deposit Owner Contribution,not-money",
        ],
    )

    with pytest.raises(ValidationError, match="invalid amount"):
        read_bank_statement_csv(csv_path)


def test_import_inserts_bank_statement_import_row(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    row = connection.execute(
        "SELECT * FROM bank_statement_imports WHERE import_id = ?",
        ("import-1",),
    ).fetchone()

    assert row is not None
    assert row["source_name"] == "bank_csv"
    assert row["file_name"] == "bank_statement.csv"
    assert row["file_hash"]


def test_import_inserts_one_bank_transaction_per_csv_row(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    count = connection.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0]

    assert count == 3


def test_returned_import_id_matches_stored_import_id(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    returned_import_id = import_bank_statement_csv(
        connection,
        csv_path,
        import_id="import-1",
    )

    stored_import_id = connection.execute(
        "SELECT import_id FROM bank_statement_imports",
    ).fetchone()[0]

    assert returned_import_id == "import-1"
    assert stored_import_id == returned_import_id


def test_provided_import_id_is_used(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_id = import_bank_statement_csv(
        connection,
        csv_path,
        import_id="manual-import-id",
    )

    assert import_id == "manual-import-id"


def test_generated_import_id_is_nonblank(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_id = import_bank_statement_csv(connection, csv_path)

    assert import_id.startswith("bank-import-")


def test_blank_import_id_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    with pytest.raises(ValidationError, match="import_id cannot be blank"):
        import_bank_statement_csv(connection, csv_path, import_id="   ")


def test_duplicate_import_id_raises_validation_error(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    with pytest.raises(ValidationError, match="already exists"):
        import_bank_statement_csv(connection, csv_path, import_id="import-1")


def test_row_count_matches_imported_row_count(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    row_count = connection.execute(
        "SELECT row_count FROM bank_statement_imports WHERE import_id = ?",
        ("import-1",),
    ).fetchone()[0]

    assert row_count == 3


def test_positive_amount_stores_positive_cents(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    amount = connection.execute(
        """
        SELECT amount_cents
        FROM bank_transactions
        WHERE external_id = ?
        """,
        ("BANK-001",),
    ).fetchone()[0]

    assert amount == 500000


def test_negative_amount_stores_negative_cents(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    amount = connection.execute(
        """
        SELECT amount_cents
        FROM bank_transactions
        WHERE external_id = ?
        """,
        ("BANK-002",),
    ).fetchone()[0]

    assert amount == -5000


def test_raw_description_is_preserved(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _write_csv(
        tmp_path,
        [
            "transaction_date,description,amount",
            "2026-01-01,  Deposit Owner Contribution  ,5000.00",
        ],
    )

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    description_raw = connection.execute(
        "SELECT description_raw FROM bank_transactions",
    ).fetchone()[0]

    assert description_raw == "  Deposit Owner Contribution  "


def test_normalized_description_is_stored(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _write_csv(
        tmp_path,
        [
            "transaction_date,description,amount",
            "2026-01-01,  Deposit Owner   Contribution  ,5000.00",
        ],
    )

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    description_normalized = connection.execute(
        "SELECT description_normalized FROM bank_transactions",
    ).fetchone()[0]

    assert description_normalized == "DEPOSIT OWNER CONTRIBUTION"


def test_optional_posted_date_is_stored_when_present(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    posted_date = connection.execute(
        """
        SELECT posted_date
        FROM bank_transactions
        WHERE external_id = ?
        """,
        ("BANK-001",),
    ).fetchone()[0]

    assert posted_date == "2026-01-01"


def test_optional_posted_date_is_null_when_blank(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    posted_date = connection.execute(
        """
        SELECT posted_date
        FROM bank_transactions
        WHERE check_number = ?
        """,
        ("1001",),
    ).fetchone()[0]

    assert posted_date is None


def test_optional_external_id_is_stored_when_present(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    external_id = connection.execute(
        """
        SELECT external_id
        FROM bank_transactions
        WHERE description_normalized = ?
        """,
        ("DEPOSIT OWNER CONTRIBUTION",),
    ).fetchone()[0]

    assert external_id == "BANK-001"


def test_optional_external_id_is_null_when_blank(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    external_id = connection.execute(
        """
        SELECT external_id
        FROM bank_transactions
        WHERE check_number = ?
        """,
        ("1001",),
    ).fetchone()[0]

    assert external_id is None


def test_optional_check_number_is_stored_when_present(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    check_number = connection.execute(
        """
        SELECT check_number
        FROM bank_transactions
        WHERE description_normalized = ?
        """,
        ("CHECK 1001",),
    ).fetchone()[0]

    assert check_number == "1001"


def test_optional_check_number_is_null_when_blank(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    check_number = connection.execute(
        """
        SELECT check_number
        FROM bank_transactions
        WHERE external_id = ?
        """,
        ("BANK-001",),
    ).fetchone()[0]

    assert check_number is None


def test_row_hash_is_populated(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    row_hash = connection.execute(
        "SELECT row_hash FROM bank_transactions LIMIT 1",
    ).fetchone()[0]

    assert len(row_hash) == 64


def test_same_row_produces_same_row_hash():
    row = {
        "transaction_date": "2026-01-01",
        "posted_date": "2026-01-01",
        "description": "Deposit Owner Contribution",
        "amount": "5000.00",
        "external_id": "BANK-001",
        "check_number": "",
    }

    assert hash_bank_row(row) == hash_bank_row(dict(row))


def test_different_rows_usually_produce_different_row_hashes():
    first = {
        "transaction_date": "2026-01-01",
        "posted_date": "2026-01-01",
        "description": "Deposit Owner Contribution",
        "amount": "5000.00",
        "external_id": "BANK-001",
        "check_number": "",
    }
    second = {
        "transaction_date": "2026-01-02",
        "posted_date": "2026-01-02",
        "description": "Deposit Owner Contribution",
        "amount": "6000.00",
        "external_id": "BANK-002",
        "check_number": "",
    }

    assert hash_bank_row(first) != hash_bank_row(second)


def test_duplicate_group_id_is_null(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    rows = connection.execute(
        "SELECT duplicate_group_id FROM bank_transactions",
    ).fetchall()

    assert [row[0] for row in rows] == [None, None, None]


def test_import_commits_rows(tmp_path):
    db_path = tmp_path / "reconcile.db"
    connection = connect(db_path)
    initialize_schema(connection)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")
    connection.close()

    reopened = connect(db_path)
    count = reopened.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0]

    assert count == 3


def test_failed_import_does_not_leave_partial_rows_when_database_insert_fails(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    with pytest.raises(ValidationError):
        import_bank_statement_csv(connection, csv_path, import_id="import-1")

    import_count = connection.execute(
        "SELECT COUNT(*) FROM bank_statement_imports",
    ).fetchone()[0]
    transaction_count = connection.execute(
        "SELECT COUNT(*) FROM bank_transactions",
    ).fetchone()[0]

    assert import_count == 1
    assert transaction_count == 3


def test_bank_import_does_not_append_ledger_events(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    event_count = connection.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]

    assert event_count == 0


def test_bank_import_does_not_modify_accounting_projection_tables(tmp_path):
    connection = _connection(tmp_path)
    csv_path = _valid_bank_csv(tmp_path)

    before = _accounting_projection_counts(connection)

    import_bank_statement_csv(connection, csv_path, import_id="import-1")

    after = _accounting_projection_counts(connection)

    assert after == before


def _connection(tmp_path):
    connection = connect(tmp_path / "reconcile.db")
    initialize_schema(connection)
    return connection


def _write_csv(tmp_path, lines):
    csv_path = tmp_path / "bank_statement.csv"
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path


def _valid_bank_csv(tmp_path):
    return _write_csv(
        tmp_path,
        [
            "transaction_date,posted_date,description,amount,external_id,check_number",
            "2026-01-01,2026-01-01,Deposit Owner Contribution,5000.00,BANK-001,",
            "2026-01-06,2026-01-06,POS Software Subscription,-50.00,BANK-002,",
            "2026-01-09,,CHECK #1001,-1200.00,,1001",
        ],
    )


def _accounting_projection_counts(connection: sqlite3.Connection):
    tables = (
        "accounts",
        "journal_entries",
        "journal_entry_lines",
        "account_balances",
    )
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in tables
    }
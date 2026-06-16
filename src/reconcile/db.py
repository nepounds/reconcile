"""SQLite connection and schema initialization helpers for Reconcile."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from reconcile.exceptions import ValidationError

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS ledger_events (
        event_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL UNIQUE,
        event_type TEXT NOT NULL,
        event_version INTEGER NOT NULL DEFAULT 1,
        event_timestamp TEXT NOT NULL,
        effective_date TEXT NOT NULL,
        source TEXT NOT NULL,
        actor TEXT,
        correlation_id TEXT,
        causation_id TEXT,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
        account_id TEXT PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        account_type TEXT NOT NULL,
        normal_balance TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        opened_at TEXT NOT NULL,
        closed_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS journal_entries (
        journal_entry_id TEXT PRIMARY KEY,
        event_id TEXT NOT NULL,
        entry_date TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        reversed_by_entry_id TEXT,
        reversal_of_entry_id TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(event_id) REFERENCES ledger_events(event_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS journal_entry_lines (
        line_id TEXT PRIMARY KEY,
        journal_entry_id TEXT NOT NULL,
        account_id TEXT NOT NULL,
        side TEXT NOT NULL CHECK (side IN ('debit', 'credit')),
        amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
        description TEXT,
        line_number INTEGER NOT NULL,
        FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(journal_entry_id),
        FOREIGN KEY(account_id) REFERENCES accounts(account_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS account_balances (
        account_id TEXT PRIMARY KEY,
        debit_total_cents INTEGER NOT NULL DEFAULT 0,
        credit_total_cents INTEGER NOT NULL DEFAULT 0,
        balance_cents INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        last_event_sequence INTEGER,
        FOREIGN KEY(account_id) REFERENCES accounts(account_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bank_statement_imports (
        import_id TEXT PRIMARY KEY,
        source_name TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_hash TEXT,
        imported_at TEXT NOT NULL,
        row_count INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bank_transactions (
        bank_transaction_id TEXT PRIMARY KEY,
        import_id TEXT NOT NULL,
        transaction_date TEXT NOT NULL,
        posted_date TEXT,
        description_raw TEXT NOT NULL,
        description_normalized TEXT,
        amount_cents INTEGER NOT NULL,
        external_id TEXT,
        check_number TEXT,
        row_hash TEXT NOT NULL,
        duplicate_group_id TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(import_id) REFERENCES bank_statement_imports(import_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reconciliation_runs (
        reconciliation_run_id TEXT PRIMARY KEY,
        cash_account_id TEXT NOT NULL,
        statement_start_date TEXT NOT NULL,
        statement_end_date TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        status TEXT NOT NULL,
        config_json TEXT NOT NULL,
        FOREIGN KEY(cash_account_id) REFERENCES accounts(account_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reconciliation_matches (
        reconciliation_match_id TEXT PRIMARY KEY,
        reconciliation_run_id TEXT NOT NULL,
        bank_transaction_id TEXT NOT NULL,
        match_type TEXT NOT NULL,
        score REAL NOT NULL,
        amount_delta_cents INTEGER NOT NULL,
        date_delta_days INTEGER,
        status TEXT NOT NULL,
        explanation_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(reconciliation_run_id)
            REFERENCES reconciliation_runs(reconciliation_run_id),
        FOREIGN KEY(bank_transaction_id)
            REFERENCES bank_transactions(bank_transaction_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reconciliation_match_ledger_links (
        reconciliation_match_id TEXT NOT NULL,
        journal_entry_id TEXT NOT NULL,
        journal_entry_line_id TEXT,
        amount_cents INTEGER NOT NULL,
        PRIMARY KEY (
            reconciliation_match_id,
            journal_entry_id,
            journal_entry_line_id
        ),
        FOREIGN KEY(reconciliation_match_id)
            REFERENCES reconciliation_matches(reconciliation_match_id),
        FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(journal_entry_id)
    )
    """,
)

_INDEX_STATEMENTS = (
    """
    CREATE INDEX IF NOT EXISTS idx_ledger_events_event_type
    ON ledger_events(event_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ledger_events_effective_date
    ON ledger_events(effective_date)
    """,
    "CREATE INDEX IF NOT EXISTS idx_accounts_code ON accounts(code)",
    """
    CREATE INDEX IF NOT EXISTS idx_journal_entries_entry_date
    ON journal_entries(entry_date)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_journal_entry_id
    ON journal_entry_lines(journal_entry_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_account_id
    ON journal_entry_lines(account_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_bank_transactions_import_id
    ON bank_transactions(import_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_bank_transactions_transaction_date
    ON bank_transactions(transaction_date)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_bank_transactions_row_hash
    ON bank_transactions(row_hash)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_reconciliation_matches_reconciliation_run_id
    ON reconciliation_matches(reconciliation_run_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_reconciliation_matches_bank_transaction_id
    ON reconciliation_matches(bank_transaction_id)
    """,
)


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Create a SQLite connection with row access and foreign keys enabled."""
    path = _validate_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create the MVP database schema if it does not already exist."""
    connection.execute("PRAGMA foreign_keys = ON")

    for statement in _SCHEMA_STATEMENTS:
        connection.execute(statement)

    for statement in _INDEX_STATEMENTS:
        connection.execute(statement)

    connection.commit()


def initialize_database(db_path: str | Path) -> sqlite3.Connection:
    """Create a SQLite connection and initialize the MVP schema."""
    connection = connect(db_path)
    initialize_schema(connection)
    return connection


def _validate_db_path(db_path: str | Path) -> Path:
    if isinstance(db_path, bool) or db_path is None:
        raise ValidationError("db_path must be a non-blank string or Path")

    if isinstance(db_path, str):
        if not db_path.strip():
            raise ValidationError("db_path must not be blank")
        return Path(db_path)

    if isinstance(db_path, Path):
        if not str(db_path).strip():
            raise ValidationError("db_path must not be blank")
        return db_path

    raise ValidationError("db_path must be a string or Path")

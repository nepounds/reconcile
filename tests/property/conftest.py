"""Shared Hypothesis helpers for accounting invariant property tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import count
from pathlib import Path
from sqlite3 import Connection
from typing import Any

from hypothesis import strategies as st

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import post_journal_entry

ACCOUNT_DEFINITIONS = {
    "acct_asset": ("1000", "Generated Asset", "asset", "debit"),
    "acct_liability": ("2000", "Generated Liability", "liability", "credit"),
    "acct_equity": ("3000", "Generated Equity", "equity", "credit"),
    "acct_revenue": ("4000", "Generated Revenue", "revenue", "credit"),
    "acct_expense": ("5000", "Generated Expense", "expense", "debit"),
}

ACCOUNT_IDS = tuple(ACCOUNT_DEFINITIONS)
_DB_COUNTER = count(1)

POSTING_SPEC_STRATEGY = st.tuples(
    st.sampled_from(ACCOUNT_IDS),
    st.sampled_from(ACCOUNT_IDS),
    st.integers(min_value=1, max_value=250_000),
).filter(lambda values: values[0] != values[1])

POSTING_SPECS_STRATEGY = st.lists(
    POSTING_SPEC_STRATEGY,
    min_size=1,
    max_size=6,
)


@dataclass(frozen=True)
class GeneratedPosting:
    """Generated two-line journal entry input."""

    journal_entry_id: str
    debit_account_id: str
    credit_account_id: str
    amount_cents: int
    entry_date: date
    description: str


def make_connection(tmp_path: Path) -> Connection:
    """Create a fresh initialized SQLite database for each Hypothesis example."""
    database_number = next(_DB_COUNTER)
    connection = connect(tmp_path / f"property_test_{database_number}.sqlite3")
    initialize_schema(connection)
    return connection


def open_standard_chart(connection: Connection) -> None:
    """Open one generated account for each official account type."""
    for account_id, values in ACCOUNT_DEFINITIONS.items():
        code, name, account_type, normal_balance = values
        account = Account(
            account_id=account_id,
            code=code,
            name=name,
            account_type=account_type,
            normal_balance=normal_balance,
            is_active=True,
            opened_at="2026-01-01T00:00:00+00:00",
            closed_at=None,
        )
        open_account(connection, account=account)


def build_postings(
    specs: list[tuple[str, str, int]],
    *,
    prefix: str = "je",
) -> list[GeneratedPosting]:
    """Turn generated posting specs into deterministic journal postings."""
    return [
        GeneratedPosting(
            journal_entry_id=f"{prefix}-{index:03d}",
            debit_account_id=debit_account_id,
            credit_account_id=credit_account_id,
            amount_cents=amount_cents,
            entry_date=date(2026, 1, 1),
            description=f"Generated posting {index}",
        )
        for index, (debit_account_id, credit_account_id, amount_cents) in enumerate(
            specs,
            start=1,
        )
    ]


def make_journal_entry(posting: GeneratedPosting) -> JournalEntry:
    """Create a balanced two-line journal entry from generated posting data."""
    return JournalEntry(
        journal_entry_id=posting.journal_entry_id,
        entry_date=posting.entry_date,
        description=posting.description,
        lines=[
            JournalLine(
                line_id=f"{posting.journal_entry_id}-line-1",
                journal_entry_id=posting.journal_entry_id,
                account_id=posting.debit_account_id,
                side="debit",
                amount_cents=posting.amount_cents,
                description="Generated debit line",
                line_number=1,
            ),
            JournalLine(
                line_id=f"{posting.journal_entry_id}-line-2",
                journal_entry_id=posting.journal_entry_id,
                account_id=posting.credit_account_id,
                side="credit",
                amount_cents=posting.amount_cents,
                description="Generated credit line",
                line_number=2,
            ),
        ],
        source="property-test",
        external_reference=None,
    )


def make_unbalanced_journal_entry(posting: GeneratedPosting) -> JournalEntry:
    """Create an intentionally unbalanced entry from generated posting data."""
    return JournalEntry(
        journal_entry_id=posting.journal_entry_id,
        entry_date=posting.entry_date,
        description=posting.description,
        lines=[
            JournalLine(
                line_id=f"{posting.journal_entry_id}-line-1",
                journal_entry_id=posting.journal_entry_id,
                account_id=posting.debit_account_id,
                side="debit",
                amount_cents=posting.amount_cents,
                description="Generated debit line",
                line_number=1,
            ),
            JournalLine(
                line_id=f"{posting.journal_entry_id}-line-2",
                journal_entry_id=posting.journal_entry_id,
                account_id=posting.credit_account_id,
                side="credit",
                amount_cents=posting.amount_cents + 1,
                description="Generated credit line",
                line_number=2,
            ),
        ],
        source="property-test",
        external_reference=None,
    )


def post_generated_entries(
    connection: Connection,
    postings: list[GeneratedPosting],
) -> None:
    """Post generated entries through the real journal posting service."""
    for posting in postings:
        post_journal_entry(connection, make_journal_entry(posting))


def account_balance_snapshot(connection: Connection) -> list[dict[str, Any]]:
    """Snapshot account balances as stable plain Python data."""
    rows = connection.execute(
        """
        SELECT
            account_id,
            debit_total_cents,
            credit_total_cents,
            balance_cents,
            last_event_sequence
        FROM account_balances
        ORDER BY account_id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def journal_entry_snapshot(connection: Connection) -> list[dict[str, Any]]:
    """Snapshot journal entries as stable plain Python data."""
    rows = connection.execute(
        """
        SELECT
            journal_entry_id,
            status,
            reversed_by_entry_id,
            reversal_of_entry_id
        FROM journal_entries
        ORDER BY journal_entry_id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def event_snapshot(connection: Connection) -> list[dict[str, Any]]:
    """Snapshot event identity and ordering only."""
    rows = connection.execute(
        """
        SELECT
            event_sequence,
            event_id,
            event_type
        FROM ledger_events
        ORDER BY event_sequence
        """
    ).fetchall()
    return [dict(row) for row in rows]


def trial_balance_snapshot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize trial balance rows for deterministic comparisons."""
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (row["account_code"], row["account_id"]),
    )


def expanded_accounting_equation(connection: Connection) -> tuple[int, int]:
    """Return both sides of Assets + Expenses = Liabilities + Equity + Revenue."""
    rows = connection.execute(
        """
        SELECT
            accounts.account_type,
            COALESCE(account_balances.balance_cents, 0) AS balance_cents
        FROM accounts
        LEFT JOIN account_balances
            ON accounts.account_id = account_balances.account_id
        ORDER BY accounts.account_id
        """
    ).fetchall()

    left_side = 0
    right_side = 0

    for row in rows:
        account_type = row["account_type"]
        balance_cents = row["balance_cents"]

        if account_type in {"asset", "expense"}:
            left_side += balance_cents
        elif account_type in {"liability", "equity", "revenue"}:
            right_side += balance_cents
        else:
            raise AssertionError(f"Unexpected account type: {account_type}")

    return left_side, right_side
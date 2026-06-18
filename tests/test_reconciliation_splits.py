"""Tests for limited split reconciliation matching."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.exceptions import ValidationError
from reconcile.imports.bank_csv import import_bank_statement_csv
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import post_journal_entry
from reconcile.reconciliation.cash_movements import extract_ledger_cash_movements
from reconcile.reconciliation.matcher import (
    get_reconciliation_run,
    run_split_reconciliation,
)
from reconcile.reconciliation.splits import (
    find_split_candidates,
    score_split_candidate,
)


@pytest.fixture
def connection(tmp_path: Path):
    db_path = tmp_path / "reconcile.db"
    connection = connect(db_path)
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


def _open_standard_accounts(connection) -> None:
    open_account(
        connection,
        account=_account("acct-cash", "1000", "Cash", "asset", "debit"),
    )
    open_account(
        connection,
        account=_account("acct-equity", "3000", "Owner Equity", "equity", "credit"),
    )
    open_account(
        connection,
        account=_account("acct-expense", "5000", "Expense", "expense", "debit"),
    )


def _post_cash_deposit(
    connection,
    *,
    entry_id: str,
    cash_line_id: str | None = None,
    entry_date: date = date(2026, 1, 5),
    amount_cents: int,
    description: str = "Owner contribution",
) -> None:
    cash_line_id = cash_line_id or f"{entry_id}-cash"
    post_journal_entry(
        connection,
        journal_entry=JournalEntry(
            journal_entry_id=entry_id,
            entry_date=entry_date,
            description=description,
            source="test",
            external_reference=None,
            lines=[
                JournalLine(
                    line_id=cash_line_id,
                    journal_entry_id=entry_id,
                    account_id="acct-cash",
                    side="debit",
                    amount_cents=amount_cents,
                    description=description,
                    line_number=1,
                ),
                JournalLine(
                    line_id=f"{entry_id}-equity",
                    journal_entry_id=entry_id,
                    account_id="acct-equity",
                    side="credit",
                    amount_cents=amount_cents,
                    description="Owner equity",
                    line_number=2,
                ),
            ],
        ),
    )


def _post_cash_payment(
    connection,
    *,
    entry_id: str,
    cash_line_id: str | None = None,
    entry_date: date = date(2026, 1, 5),
    amount_cents: int,
    description: str = "Software subscription",
) -> None:
    cash_line_id = cash_line_id or f"{entry_id}-cash"
    post_journal_entry(
        connection,
        journal_entry=JournalEntry(
            journal_entry_id=entry_id,
            entry_date=entry_date,
            description=description,
            source="test",
            external_reference=None,
            lines=[
                JournalLine(
                    line_id=f"{entry_id}-expense",
                    journal_entry_id=entry_id,
                    account_id="acct-expense",
                    side="debit",
                    amount_cents=amount_cents,
                    description=description,
                    line_number=1,
                ),
                JournalLine(
                    line_id=cash_line_id,
                    journal_entry_id=entry_id,
                    account_id="acct-cash",
                    side="credit",
                    amount_cents=amount_cents,
                    description=description,
                    line_number=2,
                ),
            ],
        ),
    )


def _write_bank_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "bank.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "transaction_date",
                "posted_date",
                "description",
                "amount",
                "external_id",
                "check_number",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _import_bank_rows(
    connection,
    tmp_path: Path,
    rows: list[dict[str, str]],
    *,
    import_id: str = "import-1",
) -> None:
    path = _write_bank_csv(tmp_path, rows)
    import_bank_statement_csv(
        connection,
        path,
        source_name="test-bank",
        import_id=import_id,
    )


def _movements(connection) -> list[dict[str, object]]:
    return extract_ledger_cash_movements(
        connection,
        cash_account_id="acct-cash",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )


def _bank_transaction(
    *,
    amount_cents: int = 10000,
    transaction_date: object = "2026-01-05",
    description: str = "OWNER CONTRIBUTION",
) -> dict[str, object]:
    return {
        "bank_transaction_id": "bank-1",
        "transaction_date": transaction_date,
        "description_raw": description,
        "description_normalized": description,
        "amount_cents": amount_cents,
    }


def _movement(
    movement_id: str,
    *,
    amount_cents: int,
    entry_date: object = "2026-01-05",
    description: str = "Owner contribution",
) -> dict[str, object]:
    return {
        "ledger_cash_movement_id": movement_id,
        "journal_entry_id": f"{movement_id}-je",
        "journal_entry_line_id": f"{movement_id}-line",
        "entry_date": entry_date,
        "amount_cents": amount_cents,
        "description": description,
        "line_description": description,
    }


def _run_default_split(connection) -> dict[str, object]:
    return run_split_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
    )


def _match_rows(connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT *
        FROM reconciliation_matches
        ORDER BY reconciliation_match_id
        """,
    ).fetchall()
    return [dict(row) for row in rows]


def _ledger_links(connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT *
        FROM reconciliation_match_ledger_links
        ORDER BY journal_entry_id, journal_entry_line_id
        """,
    ).fetchall()
    return [dict(row) for row in rows]


def _table_counts(connection, table_names: tuple[str, ...]) -> dict[str, int]:
    return {
        table_name: int(
            connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name}",
            ).fetchone()["count"]
        )
        for table_name in table_names
    }


def test_two_same_sign_ledger_movements_can_form_split_candidate():
    candidates = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [
            _movement("m1", amount_cents=4000),
            _movement("m2", amount_cents=6000),
        ],
    )

    assert len(candidates) == 1
    assert candidates[0]["component_count"] == 2
    assert candidates[0]["component_total_cents"] == 10000
    assert candidates[0]["component_movement_ids"] == ["m1", "m2"]


def test_three_same_sign_ledger_movements_can_form_split_candidate():
    candidates = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [
            _movement("m1", amount_cents=2000),
            _movement("m2", amount_cents=3000),
            _movement("m3", amount_cents=5000),
        ],
    )

    assert len(candidates) == 1
    assert candidates[0]["component_count"] == 3
    assert candidates[0]["component_total_cents"] == 10000


def test_one_component_candidates_are_not_returned():
    candidates = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [_movement("m1", amount_cents=10000)],
    )

    assert candidates == []


def test_four_component_candidates_are_not_returned():
    candidates = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [
            _movement("m1", amount_cents=2500),
            _movement("m2", amount_cents=2500),
            _movement("m3", amount_cents=2500),
            _movement("m4", amount_cents=2500),
        ],
    )

    assert candidates == []


def test_mixed_sign_components_are_rejected():
    candidates = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [
            _movement("m1", amount_cents=11000),
            _movement("m2", amount_cents=-1000),
        ],
    )

    assert candidates == []


def test_opposite_sign_bank_and_components_are_rejected():
    candidates = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [
            _movement("m1", amount_cents=-4000),
            _movement("m2", amount_cents=-6000),
        ],
    )

    assert candidates == []


def test_component_totals_outside_amount_tolerance_are_rejected():
    candidates = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [
            _movement("m1", amount_cents=4000),
            _movement("m2", amount_cents=5990),
        ],
        amount_tolerance_cents=5,
    )

    assert candidates == []


def test_components_outside_date_window_are_rejected():
    candidates = find_split_candidates(
        _bank_transaction(amount_cents=10000, transaction_date="2026-01-10"),
        [
            _movement("m1", amount_cents=4000, entry_date="2026-01-05"),
            _movement("m2", amount_cents=6000, entry_date="2026-01-10"),
        ],
        date_window_days=3,
    )

    assert candidates == []


def test_exact_component_total_scores_highest():
    candidates = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [
            _movement("m1", amount_cents=4000),
            _movement("m2", amount_cents=6000),
            _movement("m3", amount_cents=3999),
            _movement("m4", amount_cents=6000),
        ],
        amount_tolerance_cents=5,
    )

    assert candidates[0]["component_total_cents"] == 10000
    assert candidates[0]["amount_score"] == 100.0


def test_split_penalty_lowers_score():
    bank = _bank_transaction(amount_cents=10000)
    components = [
        _movement("m1", amount_cents=4000),
        _movement("m2", amount_cents=6000),
    ]

    low_penalty = score_split_candidate(bank, components, split_penalty=1.0)
    high_penalty = score_split_candidate(bank, components, split_penalty=10.0)

    assert high_penalty["score"] < low_penalty["score"]


def test_candidate_result_includes_component_ids_and_details():
    candidate = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [
            _movement("m1", amount_cents=4000),
            _movement("m2", amount_cents=6000),
        ],
    )[0]

    assert candidate["component_movement_ids"] == ["m1", "m2"]
    assert candidate["components"][0]["ledger_cash_movement_id"] == "m1"
    assert candidate["components"][0]["journal_entry_id"] == "m1-je"
    assert candidate["components"][0]["journal_entry_line_id"] == "m1-line"
    assert candidate["score_explanation"]["date_score_method"]


def test_candidate_ordering_is_deterministic():
    first = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [
            _movement("m3", amount_cents=5000),
            _movement("m2", amount_cents=4000),
            _movement("m1", amount_cents=6000),
            _movement("m4", amount_cents=5000),
        ],
    )
    second = find_split_candidates(
        _bank_transaction(amount_cents=10000),
        [
            _movement("m4", amount_cents=5000),
            _movement("m1", amount_cents=6000),
            _movement("m2", amount_cents=4000),
            _movement("m3", amount_cents=5000),
        ],
    )

    assert [item["component_movement_ids"] for item in first] == [
        item["component_movement_ids"] for item in second
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"amount_tolerance_cents": -1},
        {"date_window_days": -1},
    ],
)
def test_invalid_split_candidate_config_raises_validation_error(kwargs):
    with pytest.raises(ValidationError):
        find_split_candidates(
            _bank_transaction(amount_cents=10000),
            [
                _movement("m1", amount_cents=4000),
                _movement("m2", amount_cents=6000),
            ],
            **kwargs,
        )


def test_invalid_split_penalty_raises_validation_error():
    with pytest.raises(ValidationError):
        score_split_candidate(
            _bank_transaction(amount_cents=10000),
            [
                _movement("m1", amount_cents=4000),
                _movement("m2", amount_cents=6000),
            ],
            split_penalty=-1.0,
        )


@pytest.mark.parametrize("max_components", [1, 4])
def test_invalid_max_components_raises_validation_error(max_components):
    with pytest.raises(ValidationError):
        find_split_candidates(
            _bank_transaction(amount_cents=10000),
            [
                _movement("m1", amount_cents=4000),
                _movement("m2", amount_cents=6000),
            ],
            max_components=max_components,
        )


def test_bank_transaction_auto_matches_two_ledger_cash_movements(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = _run_default_split(connection)
    match = _match_rows(connection)[0]
    explanation = json.loads(match["explanation_json"])

    assert result["auto_matched_count"] == 1
    assert match["match_type"] == "split"
    assert match["status"] == "auto_matched"
    assert match["amount_delta_cents"] == 0
    assert match["date_delta_days"] == 0
    assert explanation["component_count"] == 2
    assert len(_ledger_links(connection)) == 2


def test_bank_transaction_auto_matches_three_ledger_cash_movements(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=2000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=3000)
    _post_cash_deposit(connection, entry_id="je-3", amount_cents=5000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = _run_default_split(connection)

    assert result["auto_matched_count"] == 1
    assert len(_ledger_links(connection)) == 3


def test_bank_transaction_can_match_sum_within_tolerance(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_payment(
        connection,
        entry_id="je-1",
        amount_cents=2500,
        description="Software subscription",
    )
    _post_cash_payment(
        connection,
        entry_id="je-2",
        amount_cents=2499,
        description="Software subscription",
    )
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "SOFTWARE SUBSCRIPTION",
                "amount": "-50.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = run_split_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        auto_match_threshold=80.0,
    )
    match = _match_rows(connection)[0]

    assert result["auto_matched_count"] == 1
    assert match["amount_delta_cents"] == -1
    assert len(_ledger_links(connection)) == 2


def test_wrong_sign_split_is_not_matched(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    _post_cash_payment(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_payment(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = _run_default_split(connection)

    assert result["unmatched_count"] == 1
    assert _match_rows(connection)[0]["match_type"] == "unmatched"
    assert _ledger_links(connection) == []


def test_out_of_tolerance_split_is_not_matched(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=5990)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = _run_default_split(connection)

    assert result["unmatched_count"] == 1
    assert _ledger_links(connection) == []


def test_out_of_window_split_is_not_matched(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    _post_cash_deposit(
        connection,
        entry_id="je-1",
        entry_date=date(2026, 1, 1),
        amount_cents=4000,
    )
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = _run_default_split(connection)

    assert result["unmatched_count"] == 1
    assert _ledger_links(connection) == []


def test_top_split_above_auto_threshold_with_sufficient_gap_auto_matches(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = _run_default_split(connection)

    assert result["auto_matched_count"] == 1


def test_top_split_above_auto_threshold_without_sufficient_gap_is_ambiguous(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _post_cash_deposit(connection, entry_id="je-3", amount_cents=3000)
    _post_cash_deposit(connection, entry_id="je-4", amount_cents=7000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = _run_default_split(connection)
    match = _match_rows(connection)[0]

    assert result["ambiguous_count"] == 1
    assert match["status"] == "ambiguous"
    assert _ledger_links(connection) == []


def test_candidate_score_range_creates_candidate(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = run_split_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        auto_match_threshold=99.0,
        candidate_threshold=80.0,
    )
    match = _match_rows(connection)[0]

    assert result["candidate_count"] == 1
    assert match["status"] == "candidate"
    assert _ledger_links(connection) == []


def test_no_split_candidate_creates_unmatched(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "UNKNOWN",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = _run_default_split(connection)
    match = _match_rows(connection)[0]

    assert result["unmatched_count"] == 1
    assert match["match_type"] == "unmatched"
    assert match["status"] == "unmatched"


def test_duplicate_flagged_bank_transaction_does_not_auto_match(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )
    connection.execute(
        "UPDATE bank_transactions SET duplicate_group_id = 'dup-test'"
    )
    connection.commit()

    result = _run_default_split(connection)
    match = _match_rows(connection)[0]

    assert result["candidate_count"] == 1
    assert match["status"] == "candidate"
    assert _ledger_links(connection) == []


def test_split_auto_match_creates_one_link_per_component(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    _run_default_split(connection)

    links = _ledger_links(connection)
    assert len(links) == 2
    assert {link["amount_cents"] for link in links} == {4000, 6000}


@pytest.mark.parametrize(
    ("auto_threshold", "expected_status"),
    [
        (99.0, "candidate"),
        (95.0, "ambiguous"),
    ],
)
def test_non_auto_split_rows_create_no_ledger_links(
    connection,
    tmp_path: Path,
    auto_threshold,
    expected_status,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _post_cash_deposit(connection, entry_id="je-3", amount_cents=3000)
    _post_cash_deposit(connection, entry_id="je-4", amount_cents=7000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    run_split_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        auto_match_threshold=auto_threshold,
    )

    assert _match_rows(connection)[0]["status"] == expected_status
    assert _ledger_links(connection) == []


def test_split_unmatched_creates_no_ledger_links(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "UNKNOWN",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    _run_default_split(connection)

    assert _ledger_links(connection) == []


def test_component_movement_is_not_reused_across_split_auto_matches(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION A",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION B",
                "amount": "100.00",
                "external_id": "BANK-2",
                "check_number": "",
            },
        ],
    )

    result = _run_default_split(connection)

    assert result["auto_matched_count"] == 1
    assert result["unmatched_count"] == 1
    assert len(_ledger_links(connection)) == 2


def test_candidate_rows_do_not_consume_component_movements(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION DUP",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            },
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION CLEAN",
                "amount": "100.00",
                "external_id": "BANK-2",
                "check_number": "",
            },
        ],
    )
    first_bank_id = connection.execute(
        """
        SELECT bank_transaction_id
        FROM bank_transactions
        ORDER BY bank_transaction_id
        LIMIT 1
        """
    ).fetchone()["bank_transaction_id"]
    connection.execute(
        """
        UPDATE bank_transactions
        SET duplicate_group_id = 'dup-test'
        WHERE bank_transaction_id = ?
        """,
        (first_bank_id,),
    )
    connection.commit()

    result = _run_default_split(connection)

    assert result["candidate_count"] == 1
    assert result["auto_matched_count"] == 1
    assert len(_ledger_links(connection)) == 2


def test_split_matching_is_deterministic(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-b", amount_cents=6000)
    _post_cash_deposit(connection, entry_id="je-a", amount_cents=4000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    _run_default_split(connection)
    first_explanation = json.loads(_match_rows(connection)[0]["explanation_json"])

    assert first_explanation["component_movement_ids"] == [
        "cashmov-je-a-cash",
        "cashmov-je-b-cash",
    ]


def test_split_reconciliation_creates_run_row_and_config(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "UNKNOWN",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    result = run_split_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="split-run-1",
        amount_tolerance_cents=7,
        date_window_days=4,
        auto_match_threshold=94.0,
        candidate_threshold=75.0,
        ambiguity_gap=8.0,
        split_penalty=4.0,
        max_components=2,
    )
    run = get_reconciliation_run(connection, "split-run-1")
    config = json.loads(run["config_json"])

    assert result["reconciliation_run_id"] == "split-run-1"
    assert config["algorithm"] == "split_amount_date_description"
    assert config["amount_tolerance_cents"] == 7
    assert config["date_window_days"] == 4
    assert config["auto_match_threshold"] == 94.0
    assert config["candidate_threshold"] == 75.0
    assert config["ambiguity_gap"] == 8.0
    assert config["split_penalty"] == 4.0
    assert config["max_components"] == 2
    assert config["split_matching"] is True


def test_generated_split_run_id_is_nonblank(connection):
    _open_standard_accounts(connection)

    result = _run_default_split(connection)

    assert isinstance(result["reconciliation_run_id"], str)
    assert result["reconciliation_run_id"]


def test_duplicate_split_run_id_raises_validation_error(connection):
    _open_standard_accounts(connection)
    kwargs = {
        "cash_account_id": "acct-cash",
        "statement_start_date": date(2026, 1, 1),
        "statement_end_date": date(2026, 1, 31),
        "reconciliation_run_id": "duplicate-run",
    }
    run_split_reconciliation(connection, **kwargs)

    with pytest.raises(ValidationError):
        run_split_reconciliation(connection, **kwargs)


def test_invalid_split_date_ranges_raise_validation_error(connection):
    _open_standard_accounts(connection)

    with pytest.raises(ValidationError):
        run_split_reconciliation(
            connection,
            cash_account_id="acct-cash",
            statement_start_date=date(2026, 1, 31),
            statement_end_date=date(2026, 1, 1),
        )

    with pytest.raises(ValidationError):
        run_split_reconciliation(
            connection,
            cash_account_id="acct-cash",
            statement_start_date=datetime(2026, 1, 1),
            statement_end_date=date(2026, 1, 31),
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"amount_tolerance_cents": -1},
        {"date_window_days": -1},
        {"auto_match_threshold": 101.0},
        {"candidate_threshold": -1.0},
        {"candidate_threshold": 96.0, "auto_match_threshold": 95.0},
        {"ambiguity_gap": -1.0},
        {"split_penalty": -1.0},
        {"max_components": 1},
        {"max_components": 4},
    ],
)
def test_invalid_split_config_values_raise_validation_error(connection, kwargs):
    _open_standard_accounts(connection)

    with pytest.raises(ValidationError):
        run_split_reconciliation(
            connection,
            cash_account_id="acct-cash",
            statement_start_date=date(2026, 1, 1),
            statement_end_date=date(2026, 1, 31),
            **kwargs,
        )


def test_split_reconciliation_does_not_append_ledger_events(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    before = int(
        connection.execute(
            "SELECT COUNT(*) AS count FROM ledger_events"
        ).fetchone()["count"]
    )
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "UNKNOWN",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )

    after_import = int(
        connection.execute(
            "SELECT COUNT(*) AS count FROM ledger_events"
        ).fetchone()["count"]
    )
    _run_default_split(connection)
    after_reconcile = int(
        connection.execute(
            "SELECT COUNT(*) AS count FROM ledger_events"
        ).fetchone()["count"]
    )

    assert after_import == before
    assert after_reconcile == after_import


def test_split_reconciliation_does_not_modify_bank_transaction_rows(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "UNKNOWN",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )
    before = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM bank_transactions ORDER BY bank_transaction_id"
        ).fetchall()
    ]

    _run_default_split(connection)

    after = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM bank_transactions ORDER BY bank_transaction_id"
        ).fetchall()
    ]
    assert after == before


def test_split_reconciliation_does_not_modify_accounting_projection_tables(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )
    before = _table_counts(
        connection,
        (
            "accounts",
            "journal_entries",
            "journal_entry_lines",
            "account_balances",
        ),
    )

    _run_default_split(connection)

    after = _table_counts(
        connection,
        (
            "accounts",
            "journal_entries",
            "journal_entry_lines",
            "account_balances",
        ),
    )
    assert after == before


def test_split_reconciliation_writes_only_reconciliation_tables(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection, entry_id="je-1", amount_cents=4000)
    _post_cash_deposit(connection, entry_id="je-2", amount_cents=6000)
    _import_bank_rows(
        connection,
        tmp_path,
        [
            {
                "transaction_date": "2026-01-05",
                "posted_date": "2026-01-05",
                "description": "OWNER CONTRIBUTION",
                "amount": "100.00",
                "external_id": "BANK-1",
                "check_number": "",
            }
        ],
    )
    before_non_reconciliation = _table_counts(
        connection,
        (
            "ledger_events",
            "accounts",
            "journal_entries",
            "journal_entry_lines",
            "account_balances",
            "bank_transactions",
        ),
    )

    _run_default_split(connection)

    after_non_reconciliation = _table_counts(
        connection,
        (
            "ledger_events",
            "accounts",
            "journal_entries",
            "journal_entry_lines",
            "account_balances",
            "bank_transactions",
        ),
    )
    reconciliation_counts = _table_counts(
        connection,
        (
            "reconciliation_runs",
            "reconciliation_matches",
            "reconciliation_match_ledger_links",
        ),
    )

    assert after_non_reconciliation == before_non_reconciliation
    assert reconciliation_counts == {
        "reconciliation_runs": 1,
        "reconciliation_matches": 1,
        "reconciliation_match_ledger_links": 2,
    }

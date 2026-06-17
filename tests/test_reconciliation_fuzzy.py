from __future__ import annotations

import inspect
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
from reconcile.reconciliation.matcher import run_fuzzy_reconciliation
from reconcile.reconciliation.scoring import (
    score_amount_match,
    score_date_match,
    score_description_match,
    score_reconciliation_candidate,
)


@pytest.fixture
def connection(tmp_path: Path):
    db_path = tmp_path / "reconcile.db"
    connection = connect(db_path)
    initialize_schema(connection)
    return connection


def _open_account(
    connection,
    *,
    account_id: str,
    code: str,
    name: str,
    account_type: str,
    normal_balance: str,
) -> None:
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


def _open_standard_accounts(connection) -> None:
    _open_account(
        connection,
        account_id="acct-cash",
        code="1000",
        name="Cash",
        account_type="asset",
        normal_balance="debit",
    )
    _open_account(
        connection,
        account_id="acct-equity",
        code="3000",
        name="Owner Equity",
        account_type="equity",
        normal_balance="credit",
    )
    _open_account(
        connection,
        account_id="acct-software",
        code="5100",
        name="Software Expense",
        account_type="expense",
        normal_balance="debit",
    )




def _post_journal_entry(connection, entry: JournalEntry) -> None:
    signature = inspect.signature(post_journal_entry)
    parameters = signature.parameters

    if "entry" in parameters:
        _post_journal_entry(connection, entry)
        return

    if "journal_entry" in parameters:
        post_journal_entry(connection, journal_entry=entry)
        return

    post_journal_entry(connection, entry)


def _post_cash_deposit(
    connection,
    *,
    entry_id: str = "je-owner",
    cash_line_id: str = "line-owner-cash",
    offset_line_id: str = "line-owner-equity",
    entry_date: date = date(2026, 1, 5),
    amount_cents: int = 10000,
    description: str = "Owner contribution",
) -> None:
    entry = JournalEntry(
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
                line_id=offset_line_id,
                journal_entry_id=entry_id,
                account_id="acct-equity",
                side="credit",
                amount_cents=amount_cents,
                description="Owner equity",
                line_number=2,
            ),
        ],
    )
    _post_journal_entry(connection, entry)


def _post_cash_payment(
    connection,
    *,
    entry_id: str = "je-software",
    cash_line_id: str = "line-software-cash",
    offset_line_id: str = "line-software-expense",
    entry_date: date = date(2026, 1, 5),
    amount_cents: int = 5000,
    description: str = "Software subscription",
) -> None:
    entry = JournalEntry(
        journal_entry_id=entry_id,
        entry_date=entry_date,
        description=description,
        source="test",
        external_reference=None,
        lines=[
            JournalLine(
                line_id=offset_line_id,
                journal_entry_id=entry_id,
                account_id="acct-software",
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
    )
    _post_journal_entry(connection, entry)


def _write_bank_csv(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "bank.csv"
    header = (
        "transaction_date,posted_date,description,amount,"
        "external_id,check_number\n"
    )
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def _import_bank_csv(
    connection,
    path: Path,
    *,
    import_id: str = "import-1",
) -> None:
    signature = inspect.signature(import_bank_statement_csv)
    kwargs = {}
    for name in signature.parameters:
        if name == "connection":
            continue
        if name in {"csv_path", "path", "file_path"}:
            kwargs[name] = path
        elif name == "source_name":
            kwargs[name] = "test-bank"
        elif name == "file_name":
            kwargs[name] = path.name
        elif name == "file_hash":
            kwargs[name] = None
        elif name == "import_id":
            kwargs[name] = import_id
        elif name == "imported_at":
            kwargs[name] = "2026-01-06T00:00:00+00:00"

    try:
        import_bank_statement_csv(connection, **kwargs)
    except TypeError:
        import_bank_statement_csv(
            connection,
            path,
            source_name="test-bank",
            file_name=path.name,
            import_id=import_id,
            imported_at="2026-01-06T00:00:00+00:00",
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


def _ledger_link_count(connection) -> int:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM reconciliation_match_ledger_links"
    ).fetchone()
    return int(row["count"])


def _run_default_fuzzy(connection) -> dict[str, object]:
    return run_fuzzy_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
    )


def test_exact_amount_scores_100():
    assert score_amount_match(10000, 10000) == 100.0


def test_same_sign_amount_within_tolerance_gets_partial_score():
    score = score_amount_match(10000, 9999, tolerance_cents=5)

    assert 0.0 < score < 100.0


def test_amount_outside_tolerance_scores_zero():
    assert score_amount_match(10000, 9990, tolerance_cents=5) == 0.0


def test_opposite_sign_amount_scores_zero():
    assert score_amount_match(10000, -10000) == 0.0


@pytest.mark.parametrize("bad_value", [True, 1.25, "100", None])
def test_invalid_amount_inputs_raise_validation_error(bad_value):
    with pytest.raises(ValidationError):
        score_amount_match(bad_value, 10000)


def test_negative_amount_tolerance_raises_validation_error():
    with pytest.raises(ValidationError):
        score_amount_match(10000, 10000, tolerance_cents=-1)


def test_exact_date_scores_100():
    assert score_date_match(date(2026, 1, 5), date(2026, 1, 5)) == 100.0


def test_date_within_window_gets_partial_score():
    score = score_date_match(
        date(2026, 1, 6),
        date(2026, 1, 5),
        date_window_days=3,
    )

    assert 0.0 < score < 100.0


def test_date_outside_window_scores_zero():
    assert (
        score_date_match(
            date(2026, 1, 9),
            date(2026, 1, 5),
            date_window_days=3,
        )
        == 0.0
    )


@pytest.mark.parametrize("bad_value", [datetime(2026, 1, 5), "2026-01-05"])
def test_invalid_date_inputs_raise_validation_error(bad_value):
    with pytest.raises(ValidationError):
        score_date_match(bad_value, date(2026, 1, 5))


def test_negative_date_window_raises_validation_error():
    with pytest.raises(ValidationError):
        score_date_match(
            date(2026, 1, 5),
            date(2026, 1, 5),
            date_window_days=-1,
        )


def test_exact_normalized_description_scores_100():
    assert (
        score_description_match(
            "Software subscription",
            "software subscription",
        )
        == 100.0
    )


def test_case_whitespace_and_punctuation_do_not_block_description_match():
    assert (
        score_description_match(
            "POS   SOFTWARE-SUBSCRIPTION!!!",
            "software subscription",
        )
        == 100.0
    )


def test_token_overlap_gets_partial_description_score():
    score = score_description_match(
        "POS SOFTWARE SUBSCRIPTION",
        "software vendor",
    )

    assert 0.0 < score < 100.0


def test_no_token_overlap_scores_zero():
    assert score_description_match("Grocery store", "Software") == 0.0


def test_missing_descriptions_score_zero():
    assert score_description_match(None, "software") == 0.0
    assert score_description_match("software", None) == 0.0
    assert score_description_match("", "") == 0.0


def test_candidate_score_combines_weighted_components():
    result = score_reconciliation_candidate(
        bank_amount_cents=10000,
        ledger_amount_cents=10000,
        bank_date=date(2026, 1, 5),
        ledger_date=date(2026, 1, 5),
        bank_description="Owner contribution",
        ledger_description="Owner contribution",
    )

    assert result["score"] == 100.0
    assert result["amount_score"] == 100.0
    assert result["date_score"] == 100.0
    assert result["description_score"] == 100.0


def test_duplicate_penalty_lowers_final_score():
    clean = score_reconciliation_candidate(
        bank_amount_cents=10000,
        ledger_amount_cents=10000,
        bank_date=date(2026, 1, 5),
        ledger_date=date(2026, 1, 5),
        bank_description="Owner contribution",
        ledger_description="Owner contribution",
    )
    duplicate = score_reconciliation_candidate(
        bank_amount_cents=10000,
        ledger_amount_cents=10000,
        bank_date=date(2026, 1, 5),
        ledger_date=date(2026, 1, 5),
        bank_description="Owner contribution",
        ledger_description="Owner contribution",
        bank_duplicate_group_id="dup-test",
    )

    assert duplicate["score"] < clean["score"]
    assert duplicate["duplicate_penalty"] > 0


def test_final_candidate_score_is_clamped():
    low = score_reconciliation_candidate(
        bank_amount_cents=10000,
        ledger_amount_cents=10000,
        bank_date=date(2026, 1, 5),
        ledger_date=date(2026, 1, 5),
        bank_description="Owner contribution",
        ledger_description="Owner contribution",
        bank_duplicate_group_id="dup-test",
        duplicate_penalty_amount=200.0,
    )

    assert low["score"] == 0.0


def test_exact_same_amount_and_date_auto_matches_in_fuzzy(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,DEPOSIT OWNER CONTRIBUTION,"
            "100.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    result = _run_default_fuzzy(connection)

    assert result["auto_matched_count"] == 1
    matches = _match_rows(connection)
    assert matches[0]["match_type"] == "fuzzy"
    assert matches[0]["status"] == "auto_matched"
    assert _ledger_link_count(connection) == 1


def test_amount_off_within_tolerance_can_auto_match(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_payment(connection, amount_cents=5000)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,SOFTWARE SUBSCRIPTION,"
            "-50.01,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    result = run_fuzzy_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        auto_match_threshold=90.0,
    )

    assert result["auto_matched_count"] == 1
    assert _ledger_link_count(connection) == 1


def test_date_off_by_one_day_can_auto_match(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    _post_cash_payment(connection, amount_cents=5000)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-06,2026-01-06,SOFTWARE SUBSCRIPTION,"
            "-50.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    result = run_fuzzy_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        auto_match_threshold=93.0,
    )

    assert result["auto_matched_count"] == 1
    assert _ledger_link_count(connection) == 1


def test_description_similarity_cannot_override_bad_amount(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_payment(connection, amount_cents=5000)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,SOFTWARE SUBSCRIPTION,"
            "-60.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    _run_default_fuzzy(connection)

    match = _match_rows(connection)[0]
    assert match["status"] == "unmatched"
    assert _ledger_link_count(connection) == 0


def test_date_outside_window_does_not_become_candidate(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_payment(connection, amount_cents=5000)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-10,2026-01-10,SOFTWARE SUBSCRIPTION,"
            "-50.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    _run_default_fuzzy(connection)

    match = _match_rows(connection)[0]
    assert match["status"] == "unmatched"
    assert _ledger_link_count(connection) == 0


def test_candidate_score_range_creates_candidate_status(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_payment(connection, amount_cents=5000)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-06,2026-01-06,SOFTWARE,"
            "-50.01,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    run_fuzzy_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        auto_match_threshold=95.0,
        candidate_threshold=70.0,
    )

    match = _match_rows(connection)[0]
    assert match["status"] == "candidate"
    assert _ledger_link_count(connection) == 0


def test_close_top_candidates_create_ambiguous_status(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(
        connection,
        entry_id="je-owner-1",
        cash_line_id="line-owner-cash-1",
        offset_line_id="line-owner-equity-1",
    )
    _post_cash_deposit(
        connection,
        entry_id="je-owner-2",
        cash_line_id="line-owner-cash-2",
        offset_line_id="line-owner-equity-2",
    )
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,OWNER CONTRIBUTION,"
            "100.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    result = _run_default_fuzzy(connection)

    assert result["ambiguous_count"] == 1
    match = _match_rows(connection)[0]
    assert match["status"] == "ambiguous"
    assert _ledger_link_count(connection) == 0


def test_unmatched_bank_transaction_creates_unmatched_record(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,UNKNOWN DEPOSIT,"
            "100.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    result = _run_default_fuzzy(connection)

    assert result["unmatched_count"] == 1
    match = _match_rows(connection)[0]
    assert match["match_type"] == "unmatched"
    assert match["status"] == "unmatched"


def test_duplicate_flagged_bank_transaction_does_not_auto_match(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,OWNER CONTRIBUTION,"
            "100.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)
    connection.execute(
        """
        UPDATE bank_transactions
        SET duplicate_group_id = 'dup-test'
        """
    )
    connection.commit()

    run_fuzzy_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        candidate_threshold=70.0,
    )

    match = _match_rows(connection)[0]
    explanation = json.loads(match["explanation_json"])
    assert match["status"] != "auto_matched"
    assert explanation["duplicate_penalty"] > 0
    assert "Duplicate" in explanation["reason"]


def test_one_ledger_movement_is_not_reused(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,OWNER CONTRIBUTION,100.00,BANK-1,",
            "2026-01-05,2026-01-05,OWNER CAPITAL,100.00,BANK-2,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    result = run_fuzzy_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        auto_match_threshold=85.0,
        candidate_threshold=70.0,
    )

    assert result["auto_matched_count"] == 1
    assert result["unmatched_count"] == 1
    assert _ledger_link_count(connection) == 1


def test_fuzzy_run_creates_run_row_and_config(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,UNKNOWN,100.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    result = run_fuzzy_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="fuzzy-run-1",
        amount_tolerance_cents=7,
        date_window_days=4,
        auto_match_threshold=94.0,
        candidate_threshold=75.0,
        ambiguity_gap=8.0,
    )

    row = connection.execute(
        """
        SELECT *
        FROM reconciliation_runs
        WHERE reconciliation_run_id = 'fuzzy-run-1'
        """
    ).fetchone()
    config = json.loads(row["config_json"])
    assert result["reconciliation_run_id"] == "fuzzy-run-1"
    assert config["amount_tolerance_cents"] == 7
    assert config["date_window_days"] == 4
    assert config["auto_match_threshold"] == 94.0
    assert config["candidate_threshold"] == 75.0
    assert config["ambiguity_gap"] == 8.0


def test_generated_fuzzy_run_id_is_nonblank(connection, tmp_path: Path):
    _open_standard_accounts(connection)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,UNKNOWN,100.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    result = _run_default_fuzzy(connection)

    assert isinstance(result["reconciliation_run_id"], str)
    assert result["reconciliation_run_id"]


def test_duplicate_fuzzy_run_id_raises_validation_error(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,UNKNOWN,100.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    run_fuzzy_reconciliation(
        connection,
        cash_account_id="acct-cash",
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 1, 31),
        reconciliation_run_id="duplicate-run",
    )

    with pytest.raises(ValidationError):
        run_fuzzy_reconciliation(
            connection,
            cash_account_id="acct-cash",
            statement_start_date=date(2026, 1, 1),
            statement_end_date=date(2026, 1, 31),
            reconciliation_run_id="duplicate-run",
        )


def test_invalid_date_ranges_raise_validation_error(connection):
    _open_standard_accounts(connection)

    with pytest.raises(ValidationError):
        run_fuzzy_reconciliation(
            connection,
            cash_account_id="acct-cash",
            statement_start_date=date(2026, 1, 31),
            statement_end_date=date(2026, 1, 1),
        )


@pytest.mark.parametrize(
    ("kwargs"),
    [
        {"amount_tolerance_cents": -1},
        {"date_window_days": -1},
        {"auto_match_threshold": 101.0},
        {"candidate_threshold": -1.0},
        {"candidate_threshold": 96.0, "auto_match_threshold": 95.0},
        {"ambiguity_gap": -1.0},
    ],
)
def test_invalid_fuzzy_config_values_raise_validation_error(
    connection,
    kwargs,
):
    _open_standard_accounts(connection)

    with pytest.raises(ValidationError):
        run_fuzzy_reconciliation(
            connection,
            cash_account_id="acct-cash",
            statement_start_date=date(2026, 1, 1),
            statement_end_date=date(2026, 1, 31),
            **kwargs,
        )


def test_fuzzy_reconciliation_does_not_append_ledger_events(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    before = connection.execute(
        "SELECT COUNT(*) AS count FROM ledger_events"
    ).fetchone()["count"]
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,UNKNOWN,100.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)

    after_import = connection.execute(
        "SELECT COUNT(*) AS count FROM ledger_events"
    ).fetchone()["count"]
    _run_default_fuzzy(connection)
    after_reconcile = connection.execute(
        "SELECT COUNT(*) AS count FROM ledger_events"
    ).fetchone()["count"]

    assert after_import == before
    assert after_reconcile == after_import


def test_fuzzy_reconciliation_does_not_modify_bank_rows(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,UNKNOWN,100.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)
    before = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM bank_transactions ORDER BY bank_transaction_id"
        ).fetchall()
    ]

    _run_default_fuzzy(connection)

    after = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM bank_transactions ORDER BY bank_transaction_id"
        ).fetchall()
    ]
    assert after == before


def test_fuzzy_reconciliation_does_not_modify_accounting_tables(
    connection,
    tmp_path: Path,
):
    _open_standard_accounts(connection)
    _post_cash_deposit(connection)
    bank_path = _write_bank_csv(
        tmp_path,
        [
            "2026-01-05,2026-01-05,OWNER CONTRIBUTION,"
            "100.00,BANK-1,",
        ],
    )
    _import_bank_csv(connection, bank_path)
    before_accounts = connection.execute(
        "SELECT COUNT(*) AS count FROM accounts"
    ).fetchone()["count"]
    before_entries = connection.execute(
        "SELECT COUNT(*) AS count FROM journal_entries"
    ).fetchone()["count"]
    before_lines = connection.execute(
        "SELECT COUNT(*) AS count FROM journal_entry_lines"
    ).fetchone()["count"]
    before_balances = connection.execute(
        "SELECT COUNT(*) AS count FROM account_balances"
    ).fetchone()["count"]

    _run_default_fuzzy(connection)

    assert before_accounts == connection.execute(
        "SELECT COUNT(*) AS count FROM accounts"
    ).fetchone()["count"]
    assert before_entries == connection.execute(
        "SELECT COUNT(*) AS count FROM journal_entries"
    ).fetchone()["count"]
    assert before_lines == connection.execute(
        "SELECT COUNT(*) AS count FROM journal_entry_lines"
    ).fetchone()["count"]
    assert before_balances == connection.execute(
        "SELECT COUNT(*) AS count FROM account_balances"
    ).fetchone()["count"]

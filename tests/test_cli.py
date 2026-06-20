from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from reconcile.cli import main
from reconcile.db import connect, initialize_schema


def _tmp_db(tmp_path: Path) -> str:
    return str(tmp_path / "reconcile.db")


def _cash_account_id() -> str:
    return "acct-cash"


def _seeded_db(tmp_path: Path) -> str:
    db_path = _tmp_db(tmp_path)
    assert main(["seed-demo", "--db-path", db_path]) == 0
    return db_path


def _seeded_db_with_bank(tmp_path: Path) -> str:
    db_path = _seeded_db(tmp_path)
    assert (
        main(
            [
                "import-bank",
                "examples/demo_company/bank_statement.csv",
                "--db-path",
                db_path,
            ]
        )
        == 0
    )
    return db_path


def test_help_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "init-db" in captured.out


def test_init_db_creates_database(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    ) -> None:
    db_path = _tmp_db(tmp_path)

    result = main(["init-db", "--db-path", db_path])

    assert result == 0
    assert Path(db_path).exists()
    assert "Initialized database" in capsys.readouterr().out


def test_init_db_creates_expected_schema_tables(tmp_path: Path) -> None:
    db_path = _tmp_db(tmp_path)

    assert main(["init-db", "--db-path", db_path]) == 0

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "ledger_events" in table_names
    assert "accounts" in table_names
    assert "journal_entries" in table_names
    assert "journal_entry_lines" in table_names
    assert "account_balances" in table_names


def test_seed_demo_opens_accounts_through_events(tmp_path: Path) -> None:
    db_path = _seeded_db(tmp_path)

    with sqlite3.connect(db_path) as connection:
        account_count = connection.execute(
            "SELECT COUNT(*) FROM accounts"
        ).fetchone()[0]
        event_count = connection.execute(
            "SELECT COUNT(*) FROM ledger_events WHERE event_type = 'AccountOpened'"
        ).fetchone()[0]

    assert account_count > 0
    assert event_count == account_count


def test_seed_demo_posts_journal_entries_through_events(tmp_path: Path) -> None:
    db_path = _seeded_db(tmp_path)

    with sqlite3.connect(db_path) as connection:
        journal_count = connection.execute(
            "SELECT COUNT(*) FROM journal_entries"
        ).fetchone()[0]
        event_count = connection.execute(
            "SELECT COUNT(*) FROM ledger_events WHERE event_type = 'JournalEntryPosted'"
        ).fetchone()[0]

    assert journal_count > 0
    assert event_count == journal_count


def test_seed_demo_fails_clearly_when_run_twice(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = _seeded_db(tmp_path)

    result = main(["seed-demo", "--db-path", db_path])

    assert result != 0
    assert "error:" in capsys.readouterr().err


def test_rebuild_projections_succeeds_after_seed(tmp_path: Path) -> None:
    db_path = _seeded_db(tmp_path)

    result = main(["rebuild-projections", "--db-path", db_path])

    assert result == 0


def test_report_trial_balance_succeeds_after_seed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = _seeded_db(tmp_path)

    result = main(["report", "trial-balance", "--db-path", db_path])

    assert result == 0
    output = capsys.readouterr().out
    assert "Trial Balance" in output
    assert "Balanced" in output


def test_report_income_statement_succeeds_after_seed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = _seeded_db(tmp_path)

    result = main(
        [
            "report",
            "income-statement",
            "--db-path",
            db_path,
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
        ]
    )

    assert result == 0
    output = capsys.readouterr().out
    assert "Income Statement" in output
    assert "Net income" in output


def test_report_balance_sheet_succeeds_after_seed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = _seeded_db(tmp_path)

    result = main(
        [
            "report",
            "balance-sheet",
            "--db-path",
            db_path,
            "--as-of",
            "2026-01-31",
        ]
    )

    assert result == 0
    output = capsys.readouterr().out
    assert "Balance Sheet" in output
    assert "Balanced" in output


def test_invalid_report_date_fails_with_nonzero_return(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = _seeded_db(tmp_path)

    result = main(
        [
            "report",
            "income-statement",
            "--db-path",
            db_path,
            "--from",
            "2026-01-01T00:00:00",
            "--to",
            "2026-01-31",
        ]
    )

    assert result != 0
    assert "YYYY-MM-DD" in capsys.readouterr().err


def test_import_bank_imports_demo_csv(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = _seeded_db(tmp_path)

    result = main(
        [
            "import-bank",
            "examples/demo_company/bank_statement.csv",
            "--db-path",
            db_path,
            "--source-name",
            "demo-bank",
        ]
    )

    assert result == 0
    assert "Imported bank statement" in capsys.readouterr().out

    with sqlite3.connect(db_path) as connection:
        row_count = connection.execute(
            "SELECT COUNT(*) FROM bank_transactions"
        ).fetchone()[0]

    assert row_count > 0


def test_reconcile_exact_succeeds_with_demo_data_and_bank_data(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = _seeded_db_with_bank(tmp_path)

    result = main(
        [
            "reconcile",
            "exact",
            "--db-path",
            db_path,
            "--cash-account-id",
            _cash_account_id(),
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
        ]
    )

    assert result == 0
    assert "Exact reconciliation" in capsys.readouterr().out


def test_reconcile_fuzzy_succeeds_with_demo_data_and_bank_data(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = _seeded_db_with_bank(tmp_path)

    result = main(
        [
            "reconcile",
            "fuzzy",
            "--db-path",
            db_path,
            "--cash-account-id",
            _cash_account_id(),
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
        ]
    )

    assert result == 0
    assert "Fuzzy reconciliation" in capsys.readouterr().out


def test_reconcile_split_is_wired_and_succeeds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = _seeded_db_with_bank(tmp_path)

    result = main(
        [
            "reconcile",
            "split",
            "--db-path",
            db_path,
            "--cash-account-id",
            _cash_account_id(),
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
        ]
    )

    assert result == 0
    assert "Split reconciliation" in capsys.readouterr().out


def test_expected_validation_errors_return_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = _seeded_db(tmp_path)

    result = main(
        [
            "reconcile",
            "exact",
            "--db-path",
            db_path,
            "--cash-account-id",
            "",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
        ]
    )

    assert result != 0
    assert "error:" in capsys.readouterr().err


def test_wrapper_script_help_smoke() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_reconcile.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "init-db" in result.stdout


def test_cli_does_not_require_existing_exports_folder(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "folder" / "reconcile.db"

    result = main(["init-db", "--db-path", str(db_path)])

    assert result == 0
    assert db_path.exists()


def test_init_db_can_be_opened_by_package_connection(tmp_path: Path) -> None:
    db_path = _tmp_db(tmp_path)

    assert main(["init-db", "--db-path", db_path]) == 0

    with connect(db_path) as connection:
        initialize_schema(connection)
        count = connection.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]

    assert count == 0
from __future__ import annotations

import csv
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from reconcile.cli import main
from reconcile.db import connect
from reconcile.exceptions import ValidationError
from reconcile.reports.export import (
    BALANCE_SHEET_COLUMNS,
    INCOME_STATEMENT_COLUMNS,
    RECONCILIATION_RESULTS_COLUMNS,
    TRIAL_BALANCE_COLUMNS,
    export_all_reports,
    export_balance_sheet_csv,
    export_income_statement_csv,
    export_reconciliation_results_csv,
    export_trial_balance_csv,
)


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


def _run_exact_reconciliation(db_path: str) -> str:
    assert (
        main(
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
        == 0
    )

    with sqlite3.connect(db_path) as connection:
        return connection.execute(
            """
            SELECT reconciliation_run_id
            FROM reconciliation_runs
            ORDER BY started_at DESC, reconciliation_run_id DESC
            LIMIT 1
            """
        ).fetchone()[0]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file_obj:
        return list(csv.DictReader(file_obj))


def _csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as file_obj:
        reader = csv.reader(file_obj)
        return next(reader)


def _table_count(connection: sqlite3.Connection, table_name: str) -> int:
    return connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def _projection_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table_name: _table_count(connection, table_name)
        for table_name in [
            "ledger_events",
            "accounts",
            "journal_entries",
            "journal_entry_lines",
            "account_balances",
            "bank_transactions",
            "reconciliation_runs",
            "reconciliation_matches",
            "reconciliation_match_ledger_links",
        ]
    }


def test_trial_balance_export_writes_expected_csv_and_summary(
    tmp_path: Path,
) -> None:
    db_path = _seeded_db(tmp_path)
    output_path = tmp_path / "nested" / "trial_balance.csv"

    with connect(db_path) as connection:
        before_counts = _projection_counts(connection)
        summary = export_trial_balance_csv(connection, output_path)
        after_counts = _projection_counts(connection)

    assert output_path.exists()
    assert output_path.parent.exists()
    assert _csv_header(output_path) == TRIAL_BALANCE_COLUMNS

    rows = _read_csv(output_path)
    assert rows
    assert summary["row_count"] == len(rows)
    assert summary["is_balanced"] is True
    assert summary["total_debit_balance_cents"] == summary[
        "total_credit_balance_cents"
    ]
    assert [row["account_code"] for row in rows] == sorted(
        row["account_code"] for row in rows
    )
    assert before_counts == after_counts


def test_income_statement_export_writes_sections_and_summary(
    tmp_path: Path,
) -> None:
    db_path = _seeded_db(tmp_path)
    output_path = tmp_path / "income_statement.csv"

    with connect(db_path) as connection:
        summary = export_income_statement_csv(
            connection,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            output_path=output_path,
        )

    assert output_path.exists()
    assert _csv_header(output_path) == INCOME_STATEMENT_COLUMNS

    rows = _read_csv(output_path)
    sections = {row["section"] for row in rows}

    assert "revenue" in sections
    assert "expense" in sections
    assert summary["row_count"] == len(rows)
    assert summary["total_revenue_cents"] > 0
    assert summary["total_expense_cents"] > 0
    assert summary["net_income_cents"] == (
        summary["total_revenue_cents"] - summary["total_expense_cents"]
    )


def test_income_statement_export_invalid_date_range_raises(
    tmp_path: Path,
) -> None:
    db_path = _seeded_db(tmp_path)

    with connect(db_path) as connection:
        with pytest.raises(ValidationError):
            export_income_statement_csv(
                connection,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 1, 1),
                output_path=tmp_path / "income_statement.csv",
            )


def test_balance_sheet_export_writes_sections_net_income_and_summary(
    tmp_path: Path,
) -> None:
    db_path = _seeded_db(tmp_path)
    output_path = tmp_path / "balance_sheet.csv"

    with connect(db_path) as connection:
        summary = export_balance_sheet_csv(
            connection,
            as_of_date=date(2026, 1, 31),
            output_path=output_path,
        )

    assert output_path.exists()
    assert _csv_header(output_path) == BALANCE_SHEET_COLUMNS

    rows = _read_csv(output_path)
    sections = {row["section"] for row in rows}

    assert "asset" in sections
    assert "liability" in sections
    assert "equity" in sections
    assert any(row["account_name"] == "Current Period Net Income" for row in rows)
    assert summary["row_count"] == len(rows)
    assert summary["total_assets_cents"] == summary[
        "total_liabilities_and_equity_cents"
    ]
    assert summary["is_balanced"] is True


def test_balance_sheet_export_invalid_as_of_date_raises(
    tmp_path: Path,
) -> None:
    db_path = _seeded_db(tmp_path)

    with connect(db_path) as connection:
        with pytest.raises(ValidationError):
            export_balance_sheet_csv(
                connection,
                as_of_date="2026-01-31",  # type: ignore[arg-type]
                output_path=tmp_path / "balance_sheet.csv",
            )


def test_reconciliation_export_writes_bank_match_and_link_fields(
    tmp_path: Path,
) -> None:
    db_path = _seeded_db_with_bank(tmp_path)
    run_id = _run_exact_reconciliation(db_path)
    output_path = tmp_path / "reconciliation_results.csv"

    with connect(db_path) as connection:
        summary = export_reconciliation_results_csv(
            connection,
            reconciliation_run_id=run_id,
            output_path=output_path,
        )

    assert output_path.exists()
    assert _csv_header(output_path) == RECONCILIATION_RESULTS_COLUMNS

    rows = _read_csv(output_path)
    assert rows
    assert summary["row_count"] == len(rows)
    assert summary["reconciliation_run_id"] == run_id

    first = rows[0]
    assert first["reconciliation_run_id"] == run_id
    assert first["bank_transaction_id"]
    assert first["bank_transaction_date"]
    assert first["bank_description_raw"]
    assert first["bank_amount_cents"]
    assert first["match_type"]
    assert first["status"]
    assert first["score"]
    assert first["amount_delta_cents"]
    assert first["ledger_link_count"]
    assert first["explanation_json"]


def test_reconciliation_export_missing_and_blank_run_ids_raise(
    tmp_path: Path,
) -> None:
    db_path = _seeded_db_with_bank(tmp_path)

    with connect(db_path) as connection:
        with pytest.raises(ValidationError):
            export_reconciliation_results_csv(
                connection,
                reconciliation_run_id="missing-run",
                output_path=tmp_path / "missing.csv",
            )

        with pytest.raises(ValidationError):
            export_reconciliation_results_csv(
                connection,
                reconciliation_run_id=" ",
                output_path=tmp_path / "blank.csv",
            )


def test_export_all_reports_skips_reconciliation_without_run_id(
    tmp_path: Path,
) -> None:
    db_path = _seeded_db(tmp_path)
    output_dir = tmp_path / "sample_output"

    with connect(db_path) as connection:
        summary = export_all_reports(
            connection,
            output_dir=output_dir,
            income_start_date=date(2026, 1, 1),
            income_end_date=date(2026, 1, 31),
            balance_sheet_as_of_date=date(2026, 1, 31),
        )

    assert (output_dir / "trial_balance.csv").exists()
    assert (output_dir / "income_statement.csv").exists()
    assert (output_dir / "balance_sheet.csv").exists()
    assert not (output_dir / "reconciliation_results.csv").exists()

    reconciliation_summary = summary["reconciliation_results"]
    assert isinstance(reconciliation_summary, dict)
    assert reconciliation_summary["skipped"] is True


def test_export_all_reports_writes_reconciliation_when_run_id_is_provided(
    tmp_path: Path,
) -> None:
    db_path = _seeded_db_with_bank(tmp_path)
    run_id = _run_exact_reconciliation(db_path)
    output_dir = tmp_path / "sample_output"

    with connect(db_path) as connection:
        summary = export_all_reports(
            connection,
            output_dir=output_dir,
            income_start_date=date(2026, 1, 1),
            income_end_date=date(2026, 1, 31),
            balance_sheet_as_of_date=date(2026, 1, 31),
            reconciliation_run_id=run_id,
        )

    assert (output_dir / "trial_balance.csv").exists()
    assert (output_dir / "income_statement.csv").exists()
    assert (output_dir / "balance_sheet.csv").exists()
    assert (output_dir / "reconciliation_results.csv").exists()

    reconciliation_summary = summary["reconciliation_results"]
    assert isinstance(reconciliation_summary, dict)
    assert reconciliation_summary["skipped"] is False
    assert reconciliation_summary["reconciliation_run_id"] == run_id
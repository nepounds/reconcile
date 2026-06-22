"""Command-line interface for Reconcile."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, cast

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account
from reconcile.db import connect, initialize_schema
from reconcile.exceptions import ReconcileError, ValidationError
from reconcile.imports.bank_csv import import_bank_statement_csv
from reconcile.journal.models import JournalEntry, JournalLine
from reconcile.journal.service import post_journal_entry
from reconcile.money import format_cents, parse_money_to_cents
from reconcile.projections.rebuild import projection_row_counts, rebuild_projections
from reconcile.reconciliation.matcher import (
    run_exact_reconciliation,
    run_fuzzy_reconciliation,
    run_split_reconciliation,
)
from reconcile.reports.balance_sheet import generate_balance_sheet
from reconcile.reports.cash_flow import generate_cash_flow_statement
from reconcile.reports.export import export_all_reports
from reconcile.reports.income_statement import (
    generate_income_statement,
)
from reconcile.reports.trial_balance import generate_trial_balance, trial_balance_totals

DEFAULT_DB_PATH = "exports/reconcile.db"
DEMO_CHART_PATH = Path("examples/demo_company/chart_of_accounts.csv")
DEMO_JOURNAL_PATH = Path("examples/demo_company/journal_entries.csv")


def main(argv: list[str] | None = None) -> int:
    """Run the Reconcile CLI and return an exit code."""
    parser = _build_parser()

    try:
        args = parser.parse_args(argv)
        if not hasattr(args, "handler"):
            parser.print_help()
            return 0
        return args.handler(args)
    except ReconcileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        missing = exc.filename or str(exc)
        print(f"error: file not found: {missing}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"error: database error: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_reconcile.py",
        description="Run local Reconcile accounting workflows.",
    )
    subparsers = parser.add_subparsers(dest="command")

    init_db = subparsers.add_parser("init-db", help="Initialize a Reconcile database.")
    _add_db_path(init_db)
    init_db.set_defaults(handler=_handle_init_db)

    seed_demo = subparsers.add_parser(
        "seed-demo",
        help="Seed fake demo accounts and journal entries.",
    )
    _add_db_path(seed_demo)
    seed_demo.set_defaults(handler=_handle_seed_demo)

    rebuild = subparsers.add_parser(
        "rebuild-projections",
        help="Rebuild SQL projections from ledger events.",
    )
    _add_db_path(rebuild)
    rebuild.set_defaults(handler=_handle_rebuild_projections)

    export_reports = subparsers.add_parser(
        "export-reports",
        help="Export implemented reports to CSV files.",
    )
    _add_db_path(export_reports)
    export_reports.add_argument("--output-dir", default="exports")
    export_reports.add_argument("--from", dest="from_date", required=True)
    export_reports.add_argument("--to", dest="to_date", required=True)
    export_reports.add_argument("--as-of", dest="as_of_date", required=True)
    export_reports.add_argument("--reconciliation-run-id")
    export_reports.set_defaults(handler=_handle_export_reports)

    report = subparsers.add_parser("report", help="Generate text reports.")
    report_subparsers = report.add_subparsers(dest="report_command", required=True)

    trial_balance = report_subparsers.add_parser(
        "trial-balance",
        help="Print trial balance rows and totals.",
    )
    _add_db_path(trial_balance)
    trial_balance.set_defaults(handler=_handle_report_trial_balance)

    income_statement = report_subparsers.add_parser(
        "income-statement",
        help="Print income statement totals.",
    )
    _add_db_path(income_statement)
    income_statement.add_argument("--from", dest="from_date", required=True)
    income_statement.add_argument("--to", dest="to_date", required=True)
    income_statement.set_defaults(handler=_handle_report_income_statement)

    balance_sheet = report_subparsers.add_parser(
        "balance-sheet",
        help="Print balance sheet totals.",
    )
    _add_db_path(balance_sheet)
    balance_sheet.add_argument("--as-of", dest="as_of_date", required=True)
    balance_sheet.set_defaults(handler=_handle_report_balance_sheet)

    cash_flow = report_subparsers.add_parser(
        "cash-flow",
        help="Print direct-method cash flow totals.",
    )
    _add_db_path(cash_flow)
    cash_flow.add_argument("--from", dest="from_date", required=True)
    cash_flow.add_argument("--to", dest="to_date", required=True)
    cash_flow.add_argument("--cash-account-id")
    cash_flow.set_defaults(handler=_handle_report_cash_flow)

    import_bank = subparsers.add_parser(
        "import-bank",
        help="Import a bank statement CSV.",
    )
    import_bank.add_argument("csv_path")
    _add_db_path(import_bank)
    import_bank.add_argument("--source-name", default="demo-bank")
    import_bank.add_argument(
        "--file-name",
        help=(
            "Accepted for CLI compatibility. The existing importer uses the "
            "input CSV path name internally."
        ),
    )
    import_bank.set_defaults(handler=_handle_import_bank)

    reconcile = subparsers.add_parser(
        "reconcile",
        help="Run reconciliation workflows.",
    )
    reconcile_subparsers = reconcile.add_subparsers(
        dest="reconcile_command",
        required=True,
    )

    exact = reconcile_subparsers.add_parser("exact", help="Run exact reconciliation.")
    _add_reconcile_common_options(exact)
    exact.set_defaults(handler=_handle_reconcile_exact)

    fuzzy = reconcile_subparsers.add_parser("fuzzy", help="Run fuzzy reconciliation.")
    _add_reconcile_common_options(fuzzy)
    _add_fuzzy_options(fuzzy)
    fuzzy.set_defaults(handler=_handle_reconcile_fuzzy)

    split = reconcile_subparsers.add_parser("split", help="Run split reconciliation.")
    _add_reconcile_common_options(split)
    _add_fuzzy_options(split)
    split.add_argument("--split-penalty", type=float, default=5.0)
    split.add_argument("--max-components", type=int, default=3)
    split.set_defaults(handler=_handle_reconcile_split)

    return parser


def _add_db_path(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH)


def _add_reconcile_common_options(parser: argparse.ArgumentParser) -> None:
    _add_db_path(parser)
    parser.add_argument("--cash-account-id", required=True)
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)


def _add_fuzzy_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--amount-tolerance-cents", type=int, default=5)
    parser.add_argument("--date-window-days", type=int, default=3)
    parser.add_argument("--auto-match-threshold", type=float, default=95.0)
    parser.add_argument("--candidate-threshold", type=float, default=80.0)
    parser.add_argument("--ambiguity-gap", type=float, default=10.0)


def _connection(db_path: str) -> sqlite3.Connection:
    connection = connect(db_path)
    initialize_schema(connection)
    return connection


def _handle_init_db(args: argparse.Namespace) -> int:
    with _connection(args.db_path):
        pass

    print(f"Initialized database: {args.db_path}")
    return 0


def _handle_seed_demo(args: argparse.Namespace) -> int:
    with _connection(args.db_path) as connection:
        account_code_to_id = _seed_demo_accounts(connection, DEMO_CHART_PATH)
        journal_count = _seed_demo_journal_entries(
            connection,
            DEMO_JOURNAL_PATH,
            account_code_to_id,
        )

    print(f"Seeded demo data into: {args.db_path}")
    print(f"Accounts opened: {len(account_code_to_id)}")
    print(f"Journal entries posted: {journal_count}")
    return 0


def _handle_rebuild_projections(args: argparse.Namespace) -> int:
    with _connection(args.db_path) as connection:
        rebuild_projections(connection)
        counts = projection_row_counts(connection)

    print(f"Rebuilt projections for: {args.db_path}")
    for table_name in sorted(counts):
        print(f"{table_name}: {counts[table_name]}")
    return 0


def _handle_export_reports(args: argparse.Namespace) -> int:
    start_date = _parse_iso_date(args.from_date)
    end_date = _parse_iso_date(args.to_date)
    as_of_date = _parse_iso_date(args.as_of_date)

    with _connection(args.db_path) as connection:
        summary = export_all_reports(
            connection,
            output_dir=args.output_dir,
            income_start_date=start_date,
            income_end_date=end_date,
            balance_sheet_as_of_date=as_of_date,
            reconciliation_run_id=args.reconciliation_run_id,
        )

    print(f"Exported reports to: {summary['output_dir']}")
    _print_export_summary("trial_balance", summary["trial_balance"])
    _print_export_summary("income_statement", summary["income_statement"])
    _print_export_summary("balance_sheet", summary["balance_sheet"])
    _print_export_summary("cash_flow", summary["cash_flow"])

    reconciliation_summary = summary["reconciliation_results"]
    if isinstance(reconciliation_summary, dict) and reconciliation_summary.get(
        "skipped"
    ):
        print("reconciliation_results: skipped")
    else:
        _print_export_summary("reconciliation_results", reconciliation_summary)

    return 0


def _handle_report_trial_balance(args: argparse.Namespace) -> int:
    with _connection(args.db_path) as connection:
        rows = generate_trial_balance(connection)
        totals = trial_balance_totals(rows)

    print("Trial Balance")
    print("Code | Account | Type | Debits | Credits | Ending Debit | Ending Credit")

    for row in rows:
        print(
            " | ".join(
                [
                    str(row["account_code"]),
                    str(row["account_name"]),
                    str(row["account_type"]),
                    format_cents(_int_value(row["debit_total_cents"])),
                    format_cents(_int_value(row["credit_total_cents"])),
                    format_cents(_int_value(row["ending_debit_balance_cents"])),
                    format_cents(_int_value(row["ending_credit_balance_cents"])),
                ]
            )
        )

    total_debits = totals.get("total_debits_cents", totals.get("debit_total_cents", 0))
    total_credits = totals.get(
        "total_credits_cents",
        totals.get("credit_total_cents", 0),
    )
    ending_debits = totals.get(
        "total_ending_debit_balance_cents",
        totals.get("ending_debit_balance_cents", 0),
    )
    ending_credits = totals.get(
        "total_ending_credit_balance_cents",
        totals.get("ending_credit_balance_cents", 0),
    )

    print("Totals")
    print(f"Debit totals: {format_cents(_int_value(total_debits))}")
    print(f"Credit totals: {format_cents(_int_value(total_credits))}")
    print(f"Ending debit balances: {format_cents(_int_value(ending_debits))}")
    print(f"Ending credit balances: {format_cents(_int_value(ending_credits))}")
    print(f"Balanced: {totals['is_balanced']}")
    return 0


def _handle_report_income_statement(args: argparse.Namespace) -> int:
    start_date = _parse_iso_date(args.from_date)
    end_date = _parse_iso_date(args.to_date)

    with _connection(args.db_path) as connection:
        report = generate_income_statement(
            connection,
            start_date=start_date,
            end_date=end_date,
        )

    print(f"Income Statement: {start_date.isoformat()} to {end_date.isoformat()}")
    print(f"Total revenue: {format_cents(_int_value(report['total_revenue_cents']))}")
    print(f"Total expenses: {format_cents(_int_value(report['total_expenses_cents']))}")
    print(f"Net income: {format_cents(_int_value(report['net_income_cents']))}")

    for row in _dict_rows(report.get("revenue_accounts")):
        print(
            " | ".join(
                [
                    str(row.get("account_code", "")),
                    str(row.get("account_name", "")),
                    "revenue",
                    format_cents(_int_value(row.get("amount_cents", 0))),
                ]
            )
        )

    for row in _dict_rows(report.get("expense_accounts")):
        print(
            " | ".join(
                [
                    str(row.get("account_code", "")),
                    str(row.get("account_name", "")),
                    "expense",
                    format_cents(_int_value(row.get("amount_cents", 0))),
                ]
            )
        )

    return 0


def _handle_report_balance_sheet(args: argparse.Namespace) -> int:
    as_of_date = _parse_iso_date(args.as_of_date)

    with _connection(args.db_path) as connection:
        report = generate_balance_sheet(connection, as_of_date=as_of_date)

    print(f"Balance Sheet: {as_of_date.isoformat()}")
    print(f"Total assets: {format_cents(_int_value(report['total_assets_cents']))}")
    print(
        "Total liabilities: "
        f"{format_cents(_int_value(report['total_liabilities_cents']))}"
    )
    print(f"Total equity: {format_cents(_int_value(report['total_equity_cents']))}")
    print(
        "Total liabilities and equity: "
        f"{format_cents(_int_value(report['total_liabilities_and_equity_cents']))}"
    )
    print(f"Balanced: {report['is_balanced']}")

    for section_name in ("assets", "liabilities", "equity"):
        for row in _dict_rows(report.get(section_name)):
            amount = row.get("amount_cents", row.get("balance_cents", 0))
            print(
                " | ".join(
                    [
                        section_name,
                        str(row.get("account_code", "")),
                        str(row.get("account_name", "")),
                        format_cents(_int_value(amount)),
                    ]
                )
            )

    return 0


def _handle_report_cash_flow(args: argparse.Namespace) -> int:
    start_date = _parse_iso_date(args.from_date)
    end_date = _parse_iso_date(args.to_date)

    with _connection(args.db_path) as connection:
        statement = generate_cash_flow_statement(
            connection,
            start_date=start_date,
            end_date=end_date,
            cash_account_id=args.cash_account_id,
        )

    totals = _dict_value(statement["totals"], "totals")

    print(f"Cash Flow Statement: {start_date.isoformat()} to {end_date.isoformat()}")
    print(
        "Operating cash flow: "
        f"{format_cents(_int_value(totals['operating_cash_flow_cents']))}"
    )
    print(
        "Investing cash flow: "
        f"{format_cents(_int_value(totals['investing_cash_flow_cents']))}"
    )
    print(
        "Financing cash flow: "
        f"{format_cents(_int_value(totals['financing_cash_flow_cents']))}"
    )
    print(
        "Net cash change: "
        f"{format_cents(_int_value(totals['net_cash_change_cents']))}"
    )
    print(f"Beginning cash: {format_cents(_int_value(totals['beginning_cash_cents']))}")
    print(f"Ending cash: {format_cents(_int_value(totals['ending_cash_cents']))}")
    print(f"Cash balances tie: {totals['cash_balances_tie']}")
    return 0


def _handle_import_bank(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv_path)

    with _connection(args.db_path) as connection:
        import_id = import_bank_statement_csv(
            connection,
            csv_path,
            source_name=args.source_name,
        )

        row = connection.execute(
            "SELECT row_count FROM bank_statement_imports WHERE import_id = ?",
            (import_id,),
        ).fetchone()

    print("Imported bank statement")
    print(f"Import ID: {import_id}")
    if row is not None:
        print(f"Rows imported: {row['row_count']}")

    return 0


def _handle_reconcile_exact(args: argparse.Namespace) -> int:
    start_date = _parse_iso_date(args.from_date)
    end_date = _parse_iso_date(args.to_date)

    with _connection(args.db_path) as connection:
        result = run_exact_reconciliation(
            connection,
            cash_account_id=args.cash_account_id,
            statement_start_date=start_date,
            statement_end_date=end_date,
        )

    _print_reconciliation_result("Exact reconciliation", result)
    return 0


def _handle_reconcile_fuzzy(args: argparse.Namespace) -> int:
    start_date = _parse_iso_date(args.from_date)
    end_date = _parse_iso_date(args.to_date)

    with _connection(args.db_path) as connection:
        result = run_fuzzy_reconciliation(
            connection,
            cash_account_id=args.cash_account_id,
            statement_start_date=start_date,
            statement_end_date=end_date,
            amount_tolerance_cents=args.amount_tolerance_cents,
            date_window_days=args.date_window_days,
            auto_match_threshold=args.auto_match_threshold,
            candidate_threshold=args.candidate_threshold,
            ambiguity_gap=args.ambiguity_gap,
        )

    _print_reconciliation_result("Fuzzy reconciliation", result)
    return 0


def _handle_reconcile_split(args: argparse.Namespace) -> int:
    start_date = _parse_iso_date(args.from_date)
    end_date = _parse_iso_date(args.to_date)

    with _connection(args.db_path) as connection:
        result = run_split_reconciliation(
            connection,
            cash_account_id=args.cash_account_id,
            statement_start_date=start_date,
            statement_end_date=end_date,
            amount_tolerance_cents=args.amount_tolerance_cents,
            date_window_days=args.date_window_days,
            auto_match_threshold=args.auto_match_threshold,
            candidate_threshold=args.candidate_threshold,
            ambiguity_gap=args.ambiguity_gap,
            split_penalty=args.split_penalty,
            max_components=args.max_components,
        )

    _print_reconciliation_result("Split reconciliation", result)
    return 0


def _seed_demo_accounts(
    connection: sqlite3.Connection,
    csv_path: Path,
) -> dict[str, str]:
    if not csv_path.exists():
        raise FileNotFoundError(str(csv_path))

    account_code_to_id: dict[str, str] = {}

    with csv_path.open(newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)

        for row in reader:
            account_code = _required_csv_value(row, "account_code")
            account_name = _required_csv_value(row, "account_name")

            account_id = _demo_account_id(account_code, account_name)
            account = Account(
                account_id=account_id,
                code=account_code,
                name=account_name,
                account_type=_required_csv_value(row, "account_type"),
                normal_balance=_required_csv_value(row, "normal_balance"),
                is_active=_parse_csv_bool(row.get("is_active", "true")),
                opened_at="2026-01-01T00:00:00+00:00",
                closed_at=None,
            )
            open_account(connection, account=account)
            account_code_to_id[account_code] = account_id

    return account_code_to_id


def _seed_demo_journal_entries(
    connection: sqlite3.Connection,
    csv_path: Path,
    account_code_to_id: dict[str, str],
) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(str(csv_path))

    grouped_rows: dict[str, list[dict[str, str]]] = defaultdict(list)

    with csv_path.open(newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)

        for row in reader:
            grouped_rows[_required_csv_value(row, "entry_id")].append(row)

    posted_count = 0

    for entry_id in sorted(grouped_rows):
        rows = sorted(
            grouped_rows[entry_id],
            key=lambda item: int(_required_csv_value(item, "line_number")),
        )
        first = rows[0]
        journal_entry_id = _required_csv_value(first, "entry_id")

        lines = []
        for row in rows:
            account_code = _required_csv_value(row, "account_code")
            try:
                account_id = account_code_to_id[account_code]
            except KeyError as exc:
                raise ValidationError(
                    f"Journal entry {journal_entry_id} references unknown "
                    f"account code {account_code!r}."
                ) from exc

            line_number = int(_required_csv_value(row, "line_number"))
            lines.append(
                JournalLine(
                    line_id=f"{journal_entry_id}-line-{line_number}",
                    journal_entry_id=journal_entry_id,
                    account_id=account_id,
                    side=_required_csv_value(row, "side"),
                    amount_cents=parse_money_to_cents(
                        _required_csv_value(row, "amount")
                    ),
                    description=row.get("line_description") or None,
                    line_number=line_number,
                )
            )

        entry = JournalEntry(
            journal_entry_id=journal_entry_id,
            entry_date=_parse_iso_date(_required_csv_value(first, "entry_date")),
            description=_required_csv_value(first, "description"),
            lines=lines,
            source="demo",
            external_reference=first.get("external_reference") or None,
        )
        post_journal_entry(connection, journal_entry=entry)
        posted_count += 1

    return posted_count


def _demo_account_id(account_code: str, account_name: str) -> str:
    normalized_name = account_name.strip().lower()
    if account_code == "1000" or normalized_name == "cash":
        return "acct-cash"
    return f"acct-{account_code}"


def _parse_csv_bool(value: str | None) -> bool:
    if value is None or value.strip() == "":
        return True

    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False

    raise ValidationError(f"Invalid boolean value in demo CSV: {value!r}")


def _required_csv_value(row: dict[str, str], column: str) -> str:
    value = row.get(column)
    if value is None or value.strip() == "":
        raise ValidationError(f"Missing required CSV value: {column}")
    return value.strip()



def _int_value(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("Expected an integer cent value.")
    return value


def _dict_value(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must be a dictionary")
    return cast(dict[str, object], value)


def _dict_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    return [
        cast(dict[str, object], row)
        for row in value
        if isinstance(row, dict)
    ]

def _parse_iso_date(value: str) -> date:
    if "T" in value or " " in value:
        raise ValidationError(f"Expected date in YYYY-MM-DD format: {value!r}")

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"Expected date in YYYY-MM-DD format: {value!r}") from exc

    if parsed.isoformat() != value:
        raise ValidationError(f"Expected date in YYYY-MM-DD format: {value!r}")

    return parsed


def _get_result_value(result: Any, key: str) -> Any:
    if isinstance(result, dict):
        return result.get(key)
    return getattr(result, key, None)


def _print_reconciliation_result(title: str, result: Any) -> None:
    print(title)

    run_id = _get_result_value(result, "reconciliation_run_id")
    if run_id is None:
        run_id = _get_result_value(result, "run_id")

    if run_id is not None:
        print(f"Run ID: {run_id}")

    summary = _get_result_value(result, "summary")
    if isinstance(summary, dict):
        for key in sorted(summary):
            print(f"{key}: {summary[key]}")
        return

    for key in (
        "auto_matched_count",
        "candidate_count",
        "ambiguous_count",
        "unmatched_count",
        "match_count",
    ):
        value = _get_result_value(result, key)
        if value is not None:
            print(f"{key}: {value}")


def _print_export_summary(name: str, summary: object) -> None:
    if not isinstance(summary, dict):
        print(f"{name}: unavailable")
        return

    output_path = summary.get("output_path")
    row_count = summary.get("row_count", 0)
    print(f"{name}: {output_path} ({row_count} rows)")
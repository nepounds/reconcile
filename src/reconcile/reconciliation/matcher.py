"""Exact bank-to-ledger reconciliation matching."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

from reconcile.exceptions import ValidationError
from reconcile.reconciliation.cash_movements import extract_ledger_cash_movements
from reconcile.reconciliation.explanations import (
    build_exact_match_explanation,
    build_unmatched_explanation,
)
from reconcile.reconciliation.models import (
    MATCH_STATUS_AUTO_MATCHED,
    MATCH_STATUS_CANDIDATE,
    MATCH_STATUS_UNMATCHED,
    MATCH_TYPE_EXACT,
    MATCH_TYPE_UNMATCHED,
    RECONCILIATION_RUN_STATUS_COMPLETED,
)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _validate_nonblank(value: str | None, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a nonblank string")
    return value.strip()


def _validate_date(value: object, field_name: str) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValidationError(f"{field_name} must be a date")
    return value


def _date_key(value: object, field_name: str) -> str:
    if isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a date, not datetime")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValidationError(f"{field_name} must be a date string or date")


def _movement_id(movement: dict[str, Any]) -> str:
    for key in (
        "ledger_cash_movement_id",
        "cash_movement_id",
        "journal_entry_line_id",
        "line_id",
    ):
        value = movement.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    journal_entry_id = movement.get("journal_entry_id")
    amount_cents = movement.get("amount_cents")
    entry_date = movement.get("entry_date")
    return f"movement:{journal_entry_id}:{entry_date}:{amount_cents}"


def _movement_line_id(movement: dict[str, Any]) -> str | None:
    for key in ("journal_entry_line_id", "line_id"):
        value = movement.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _movement_sort_key(movement: dict[str, Any]) -> tuple[object, ...]:
    return (
        _date_key(movement.get("entry_date"), "entry_date"),
        int(movement["amount_cents"]),
        str(movement.get("journal_entry_id") or ""),
        str(_movement_line_id(movement) or ""),
        _movement_id(movement),
    )


def _validate_cash_account_exists(
    connection: sqlite3.Connection, cash_account_id: str
) -> None:
    row = connection.execute(
        "SELECT account_id FROM accounts WHERE account_id = ?",
        (cash_account_id,),
    ).fetchone()
    if row is None:
        raise ValidationError("cash_account_id must reference an existing account")


def _load_bank_transactions(
    connection: sqlite3.Connection,
    *,
    start_date: date,
    end_date: date,
) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT
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
            FROM bank_transactions
            WHERE transaction_date BETWEEN ? AND ?
            ORDER BY transaction_date, bank_transaction_id
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    )


def _insert_run(
    connection: sqlite3.Connection,
    *,
    reconciliation_run_id: str,
    cash_account_id: str,
    statement_start_date: date,
    statement_end_date: date,
    started_at: str,
    completed_at: str,
) -> None:
    config = {
        "algorithm": "exact_amount_date",
        "match_types": [MATCH_TYPE_EXACT, MATCH_TYPE_UNMATCHED],
        "amount_tolerance_cents": 0,
        "date_window_days": 0,
        "description_scoring": False,
        "split_matching": False,
        "duplicate_flagged_rows_auto_match": False,
    }
    try:
        connection.execute(
            """
            INSERT INTO reconciliation_runs (
                reconciliation_run_id,
                cash_account_id,
                statement_start_date,
                statement_end_date,
                started_at,
                completed_at,
                status,
                config_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reconciliation_run_id,
                cash_account_id,
                statement_start_date.isoformat(),
                statement_end_date.isoformat(),
                started_at,
                completed_at,
                RECONCILIATION_RUN_STATUS_COMPLETED,
                json.dumps(config, sort_keys=True),
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise ValidationError("reconciliation_run_id already exists") from exc


def _insert_match(
    connection: sqlite3.Connection,
    *,
    reconciliation_match_id: str,
    reconciliation_run_id: str,
    bank_transaction_id: str,
    match_type: str,
    score: float,
    amount_delta_cents: int,
    date_delta_days: int | None,
    status: str,
    explanation: dict[str, object],
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO reconciliation_matches (
            reconciliation_match_id,
            reconciliation_run_id,
            bank_transaction_id,
            match_type,
            score,
            amount_delta_cents,
            date_delta_days,
            status,
            explanation_json,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reconciliation_match_id,
            reconciliation_run_id,
            bank_transaction_id,
            match_type,
            score,
            amount_delta_cents,
            date_delta_days,
            status,
            json.dumps(explanation, sort_keys=True),
            created_at,
        ),
    )


def _insert_ledger_link(
    connection: sqlite3.Connection,
    *,
    reconciliation_match_id: str,
    movement: dict[str, Any],
) -> None:
    journal_entry_id = _validate_nonblank(
        movement.get("journal_entry_id"), "journal_entry_id"
    )
    connection.execute(
        """
        INSERT INTO reconciliation_match_ledger_links (
            reconciliation_match_id,
            journal_entry_id,
            journal_entry_line_id,
            amount_cents
        ) VALUES (?, ?, ?, ?)
        """,
        (
            reconciliation_match_id,
            journal_entry_id,
            _movement_line_id(movement),
            int(movement["amount_cents"]),
        ),
    )


def run_exact_reconciliation(
    connection: sqlite3.Connection,
    *,
    cash_account_id: str,
    statement_start_date: date,
    statement_end_date: date,
    reconciliation_run_id: str | None = None,
    started_at: str | None = None,
) -> dict[str, object]:
    """Run exact amount/date reconciliation and persist the results."""
    cash_account_id = _validate_nonblank(cash_account_id, "cash_account_id")
    statement_start_date = _validate_date(
        statement_start_date, "statement_start_date"
    )
    statement_end_date = _validate_date(statement_end_date, "statement_end_date")
    if statement_start_date > statement_end_date:
        raise ValidationError("statement_start_date cannot be after statement_end_date")

    _validate_cash_account_exists(connection, cash_account_id)

    if reconciliation_run_id is None:
        reconciliation_run_id = f"recon-run-{uuid.uuid4().hex}"
    else:
        reconciliation_run_id = _validate_nonblank(
            reconciliation_run_id, "reconciliation_run_id"
        )

    if started_at is None:
        started_at = _utc_now()
    else:
        started_at = _validate_nonblank(started_at, "started_at")
    completed_at = _utc_now()
    created_at = completed_at

    bank_transactions = _load_bank_transactions(
        connection,
        start_date=statement_start_date,
        end_date=statement_end_date,
    )
    ledger_movements = extract_ledger_cash_movements(
        connection,
        cash_account_id=cash_account_id,
        start_date=statement_start_date,
        end_date=statement_end_date,
    )
    ledger_movements = sorted(ledger_movements, key=_movement_sort_key)

    movements_by_key: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for movement in ledger_movements:
        key = (
            int(movement["amount_cents"]),
            _date_key(movement.get("entry_date"), "entry_date"),
        )
        movements_by_key[key].append(movement)

    auto_matched_count = 0
    candidate_count = 0
    unmatched_count = 0
    used_movement_ids: set[str] = set()

    try:
        with connection:
            _insert_run(
                connection,
                reconciliation_run_id=reconciliation_run_id,
                cash_account_id=cash_account_id,
                statement_start_date=statement_start_date,
                statement_end_date=statement_end_date,
                started_at=started_at,
                completed_at=completed_at,
            )

            for index, bank_row in enumerate(bank_transactions, start=1):
                bank_transaction_id = bank_row["bank_transaction_id"]
                bank_amount = int(bank_row["amount_cents"])
                transaction_date = bank_row["transaction_date"]
                duplicate_group_id = bank_row["duplicate_group_id"]
                match_id = f"recon-match-{reconciliation_run_id}-{index:05d}"
                key = (bank_amount, transaction_date)
                exact_candidates = movements_by_key.get(key, [])
                unused_candidates = [
                    movement
                    for movement in exact_candidates
                    if _movement_id(movement) not in used_movement_ids
                ]

                if duplicate_group_id:
                    candidate_count += 1
                    if exact_candidates:
                        first = exact_candidates[0]
                        explanation = build_exact_match_explanation(
                            bank_transaction_id=bank_transaction_id,
                            ledger_cash_movement_id=_movement_id(first),
                            amount_cents=bank_amount,
                            transaction_date=transaction_date,
                            entry_date=first.get("entry_date"),
                            reason="duplicate_flagged_bank_transaction",
                            blocked_reason=(
                                "duplicate-flagged bank rows are not "
                                "auto-matched in exact reconciliation"
                            ),
                            duplicate_group_id=duplicate_group_id,
                            candidate_count=len(exact_candidates),
                        )
                        _insert_match(
                            connection,
                            reconciliation_match_id=match_id,
                            reconciliation_run_id=reconciliation_run_id,
                            bank_transaction_id=bank_transaction_id,
                            match_type=MATCH_TYPE_EXACT,
                            score=100.0,
                            amount_delta_cents=0,
                            date_delta_days=0,
                            status=MATCH_STATUS_CANDIDATE,
                            explanation=explanation,
                            created_at=created_at,
                        )
                    else:
                        explanation = build_unmatched_explanation(
                            bank_transaction_id=bank_transaction_id,
                            amount_cents=bank_amount,
                            transaction_date=transaction_date,
                            reason="duplicate_flagged_bank_transaction_no_exact_match",
                            duplicate_group_id=duplicate_group_id,
                            blocked_reason=(
                                "duplicate-flagged bank row had no exact "
                                "unused ledger cash movement"
                            ),
                        )
                        _insert_match(
                            connection,
                            reconciliation_match_id=match_id,
                            reconciliation_run_id=reconciliation_run_id,
                            bank_transaction_id=bank_transaction_id,
                            match_type=MATCH_TYPE_UNMATCHED,
                            score=0.0,
                            amount_delta_cents=bank_amount,
                            date_delta_days=None,
                            status=MATCH_STATUS_CANDIDATE,
                            explanation=explanation,
                            created_at=created_at,
                        )
                    continue

                if len(unused_candidates) == 1:
                    movement = unused_candidates[0]
                    used_movement_ids.add(_movement_id(movement))
                    auto_matched_count += 1
                    explanation = build_exact_match_explanation(
                        bank_transaction_id=bank_transaction_id,
                        ledger_cash_movement_id=_movement_id(movement),
                        amount_cents=bank_amount,
                        transaction_date=transaction_date,
                        entry_date=movement.get("entry_date"),
                    )
                    _insert_match(
                        connection,
                        reconciliation_match_id=match_id,
                        reconciliation_run_id=reconciliation_run_id,
                        bank_transaction_id=bank_transaction_id,
                        match_type=MATCH_TYPE_EXACT,
                        score=100.0,
                        amount_delta_cents=0,
                        date_delta_days=0,
                        status=MATCH_STATUS_AUTO_MATCHED,
                        explanation=explanation,
                        created_at=created_at,
                    )
                    _insert_ledger_link(
                        connection,
                        reconciliation_match_id=match_id,
                        movement=movement,
                    )
                    continue

                if len(unused_candidates) > 1:
                    candidate_count += 1
                    first = unused_candidates[0]
                    explanation = build_exact_match_explanation(
                        bank_transaction_id=bank_transaction_id,
                        ledger_cash_movement_id=_movement_id(first),
                        amount_cents=bank_amount,
                        transaction_date=transaction_date,
                        entry_date=first.get("entry_date"),
                        reason="multiple_exact_ledger_cash_movements_matched",
                        blocked_reason=(
                            "more than one unused ledger movement matched "
                            "the bank amount and date exactly"
                        ),
                        candidate_count=len(unused_candidates),
                    )
                    _insert_match(
                        connection,
                        reconciliation_match_id=match_id,
                        reconciliation_run_id=reconciliation_run_id,
                        bank_transaction_id=bank_transaction_id,
                        match_type=MATCH_TYPE_EXACT,
                        score=100.0,
                        amount_delta_cents=0,
                        date_delta_days=0,
                        status=MATCH_STATUS_CANDIDATE,
                        explanation=explanation,
                        created_at=created_at,
                    )
                    continue

                if exact_candidates:
                    candidate_count += 1
                    first = exact_candidates[0]
                    explanation = build_exact_match_explanation(
                        bank_transaction_id=bank_transaction_id,
                        ledger_cash_movement_id=_movement_id(first),
                        amount_cents=bank_amount,
                        transaction_date=transaction_date,
                        entry_date=first.get("entry_date"),
                        reason="exact_ledger_cash_movement_already_used",
                        blocked_reason=(
                            "the exact ledger movement was already consumed "
                            "by an earlier deterministic auto-match"
                        ),
                        candidate_count=len(exact_candidates),
                    )
                    _insert_match(
                        connection,
                        reconciliation_match_id=match_id,
                        reconciliation_run_id=reconciliation_run_id,
                        bank_transaction_id=bank_transaction_id,
                        match_type=MATCH_TYPE_EXACT,
                        score=100.0,
                        amount_delta_cents=0,
                        date_delta_days=0,
                        status=MATCH_STATUS_CANDIDATE,
                        explanation=explanation,
                        created_at=created_at,
                    )
                    continue

                unmatched_count += 1
                explanation = build_unmatched_explanation(
                    bank_transaction_id=bank_transaction_id,
                    amount_cents=bank_amount,
                    transaction_date=transaction_date,
                )
                _insert_match(
                    connection,
                    reconciliation_match_id=match_id,
                    reconciliation_run_id=reconciliation_run_id,
                    bank_transaction_id=bank_transaction_id,
                    match_type=MATCH_TYPE_UNMATCHED,
                    score=0.0,
                    amount_delta_cents=bank_amount,
                    date_delta_days=None,
                    status=MATCH_STATUS_UNMATCHED,
                    explanation=explanation,
                    created_at=created_at,
                )
    except sqlite3.IntegrityError as exc:
        raise ValidationError("could not save reconciliation results") from exc

    total_matches = auto_matched_count + candidate_count + unmatched_count
    return {
        "reconciliation_run_id": reconciliation_run_id,
        "cash_account_id": cash_account_id,
        "statement_start_date": statement_start_date.isoformat(),
        "statement_end_date": statement_end_date.isoformat(),
        "status": RECONCILIATION_RUN_STATUS_COMPLETED,
        "auto_matched_count": auto_matched_count,
        "candidate_count": candidate_count,
        "unmatched_count": unmatched_count,
        "total_bank_transactions": len(bank_transactions),
        "total_matches": total_matches,
    }


def get_reconciliation_run(
    connection: sqlite3.Connection, reconciliation_run_id: str
) -> dict[str, object] | None:
    """Return one reconciliation run row as a dictionary."""
    reconciliation_run_id = _validate_nonblank(
        reconciliation_run_id, "reconciliation_run_id"
    )
    row = connection.execute(
        """
        SELECT
            reconciliation_run_id,
            cash_account_id,
            statement_start_date,
            statement_end_date,
            started_at,
            completed_at,
            status,
            config_json
        FROM reconciliation_runs
        WHERE reconciliation_run_id = ?
        """,
        (reconciliation_run_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def list_reconciliation_matches(
    connection: sqlite3.Connection, reconciliation_run_id: str
) -> list[dict[str, object]]:
    """Return reconciliation matches for a run in deterministic order."""
    reconciliation_run_id = _validate_nonblank(
        reconciliation_run_id, "reconciliation_run_id"
    )
    rows = connection.execute(
        """
        SELECT
            reconciliation_match_id,
            reconciliation_run_id,
            bank_transaction_id,
            match_type,
            score,
            amount_delta_cents,
            date_delta_days,
            status,
            explanation_json,
            created_at
        FROM reconciliation_matches
        WHERE reconciliation_run_id = ?
        ORDER BY reconciliation_match_id
        """,
        (reconciliation_run_id,),
    ).fetchall()
    return [dict(row) for row in rows]


__all__ = [
    "get_reconciliation_run",
    "list_reconciliation_matches",
    "run_exact_reconciliation",
]

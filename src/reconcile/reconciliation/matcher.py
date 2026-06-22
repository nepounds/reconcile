"""Bank-to-ledger reconciliation matching."""

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
    build_fuzzy_match_explanation,
    build_split_match_explanation,
    build_unmatched_explanation,
)
from reconcile.reconciliation.models import (
    MATCH_STATUS_AMBIGUOUS,
    MATCH_STATUS_AUTO_MATCHED,
    MATCH_STATUS_CANDIDATE,
    MATCH_STATUS_UNMATCHED,
    MATCH_TYPE_EXACT,
    MATCH_TYPE_FUZZY,
    MATCH_TYPE_SPLIT,
    MATCH_TYPE_UNMATCHED,
    RECONCILIATION_RUN_STATUS_COMPLETED,
)
from reconcile.reconciliation.scoring import score_reconciliation_candidate
from reconcile.reconciliation.splits import (
    find_split_candidates,
    score_split_candidate,
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


def _date_value(value: object, field_name: str) -> date:
    if isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a date, not datetime")
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an ISO date") from exc
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
    connection: sqlite3.Connection,
    cash_account_id: str,
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


def _insert_fuzzy_run(
    connection: sqlite3.Connection,
    *,
    reconciliation_run_id: str,
    cash_account_id: str,
    statement_start_date: date,
    statement_end_date: date,
    started_at: str,
    completed_at: str,
    config: dict[str, object],
) -> None:
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
        movement.get("journal_entry_id"),
        "journal_entry_id",
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


def _same_sign(left: int, right: int) -> bool:
    if left == 0 or right == 0:
        return left == right
    return (left > 0 and right > 0) or (left < 0 and right < 0)


def _ledger_description(movement: dict[str, Any]) -> str | None:
    description = movement.get("description")
    line_description = movement.get("line_description")
    if isinstance(description, str) and description.strip():
        return description
    if isinstance(line_description, str) and line_description.strip():
        return line_description
    return None


def _bank_description(bank_row: sqlite3.Row) -> str | None:
    normalized = bank_row["description_normalized"]
    raw = bank_row["description_raw"]
    if isinstance(normalized, str) and normalized.strip():
        return normalized
    if isinstance(raw, str) and raw.strip():
        return raw
    return None


def _candidate_summary(candidate: dict[str, Any]) -> dict[str, object]:
    return {
        "ledger_cash_movement_id": candidate["ledger_cash_movement_id"],
        "journal_entry_id": candidate["journal_entry_id"],
        "journal_entry_line_id": candidate["journal_entry_line_id"],
        "score": candidate["score"],
        "amount_score": candidate["amount_score"],
        "date_score": candidate["date_score"],
        "description_score": candidate["description_score"],
        "amount_delta_cents": candidate["amount_delta_cents"],
        "date_delta_days": candidate["date_delta_days"],
        "duplicate_penalty": candidate["duplicate_penalty"],
    }


def _validate_threshold_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValidationError(f"{field_name} must be a number")
    return float(value)


def _validate_fuzzy_thresholds(
    *,
    amount_tolerance_cents: int,
    date_window_days: int,
    auto_match_threshold: float,
    candidate_threshold: float,
    ambiguity_gap: float,
) -> None:
    if isinstance(amount_tolerance_cents, bool) or not isinstance(
        amount_tolerance_cents,
        int,
    ):
        raise ValidationError("amount_tolerance_cents must be an integer")
    if amount_tolerance_cents < 0:
        raise ValidationError("amount_tolerance_cents cannot be negative")

    if isinstance(date_window_days, bool) or not isinstance(date_window_days, int):
        raise ValidationError("date_window_days must be an integer")
    if date_window_days < 0:
        raise ValidationError("date_window_days cannot be negative")

    auto_threshold = _validate_threshold_number(
        auto_match_threshold,
        "auto_match_threshold",
    )
    candidate_threshold = _validate_threshold_number(
        candidate_threshold,
        "candidate_threshold",
    )
    gap = _validate_threshold_number(ambiguity_gap, "ambiguity_gap")

    if not 0.0 <= candidate_threshold <= 100.0:
        raise ValidationError("candidate_threshold must be between 0 and 100")
    if not 0.0 <= auto_threshold <= 100.0:
        raise ValidationError("auto_match_threshold must be between 0 and 100")
    if candidate_threshold > auto_threshold:
        raise ValidationError(
            "candidate_threshold cannot be greater than auto_match_threshold"
        )
    if gap < 0.0:
        raise ValidationError("ambiguity_gap cannot be negative")



def _validate_split_thresholds(
    *,
    amount_tolerance_cents: int,
    date_window_days: int,
    auto_match_threshold: float,
    candidate_threshold: float,
    ambiguity_gap: float,
    split_penalty: float,
    max_components: int,
) -> None:
    _validate_fuzzy_thresholds(
        amount_tolerance_cents=amount_tolerance_cents,
        date_window_days=date_window_days,
        auto_match_threshold=auto_match_threshold,
        candidate_threshold=candidate_threshold,
        ambiguity_gap=ambiguity_gap,
    )

    if isinstance(split_penalty, bool) or not isinstance(split_penalty, int | float):
        raise ValidationError("split_penalty must be a number")
    if float(split_penalty) < 0.0:
        raise ValidationError("split_penalty cannot be negative")

    if isinstance(max_components, bool) or not isinstance(max_components, int):
        raise ValidationError("max_components must be an integer")
    if max_components < 2:
        raise ValidationError("max_components cannot be less than 2")
    if max_components > 3:
        raise ValidationError("max_components cannot be greater than 3")


def _fuzzy_candidate_sort_key(candidate: dict[str, Any]) -> tuple[object, ...]:
    return (
        -_object_float(candidate.get("score"), "score"),
        abs(_object_int(candidate.get("amount_delta_cents"), "amount_delta_cents")),
        abs(_object_int(candidate.get("date_delta_days"), "date_delta_days")),
        str(candidate["ledger_cash_movement_id"]),
    )


def _build_fuzzy_candidates(
    *,
    bank_row: sqlite3.Row,
    bank_date: date,
    ledger_movements: list[dict[str, Any]],
    used_movement_ids: set[str],
    amount_tolerance_cents: int,
    date_window_days: int,
) -> list[dict[str, Any]]:
    bank_amount = int(bank_row["amount_cents"])
    bank_duplicate_group_id = bank_row["duplicate_group_id"]
    candidates: list[dict[str, Any]] = []

    for movement in ledger_movements:
        ledger_movement_id = _movement_id(movement)
        if ledger_movement_id in used_movement_ids:
            continue

        ledger_amount = int(movement["amount_cents"])
        if not _same_sign(bank_amount, ledger_amount):
            continue

        amount_delta = bank_amount - ledger_amount
        if abs(amount_delta) > amount_tolerance_cents:
            continue

        ledger_date = _date_value(movement.get("entry_date"), "entry_date")
        date_delta = (bank_date - ledger_date).days
        if abs(date_delta) > date_window_days:
            continue

        score_details = score_reconciliation_candidate(
            bank_amount_cents=bank_amount,
            ledger_amount_cents=ledger_amount,
            bank_date=bank_date,
            ledger_date=ledger_date,
            bank_description=_bank_description(bank_row),
            ledger_description=_ledger_description(movement),
            bank_duplicate_group_id=bank_duplicate_group_id,
            tolerance_cents=amount_tolerance_cents,
            date_window_days=date_window_days,
        )
        candidate: dict[str, Any] = {
            **score_details,
            "ledger_cash_movement_id": ledger_movement_id,
            "journal_entry_id": movement["journal_entry_id"],
            "journal_entry_line_id": _movement_line_id(movement),
            "ledger_amount_cents": ledger_amount,
            "ledger_date": ledger_date.isoformat(),
        }
        candidates.append(candidate)

    candidates.sort(key=_fuzzy_candidate_sort_key)
    return candidates


def _empty_fuzzy_score(
    *,
    amount_delta_cents: int,
    date_delta_days: int | None,
    reason: str,
) -> dict[str, object]:
    return {
        "score": 0.0,
        "amount_score": 0.0,
        "date_score": 0.0,
        "description_score": 0.0,
        "amount_delta_cents": amount_delta_cents,
        "date_delta_days": date_delta_days,
        "duplicate_penalty": 0.0,
        "score_explanation": {
            "reason": reason,
            "reasons": [reason],
        },
    }


def _split_candidate_summary(candidate: dict[str, Any]) -> dict[str, object]:
    return {
        "score": candidate["score"],
        "amount_score": candidate["amount_score"],
        "date_score": candidate["date_score"],
        "description_score": candidate["description_score"],
        "split_penalty": candidate["split_penalty"],
        "amount_delta_cents": candidate["amount_delta_cents"],
        "date_delta_days": candidate["date_delta_days"],
        "component_count": candidate["component_count"],
        "component_total_cents": candidate["component_total_cents"],
        "component_movement_ids": candidate["component_movement_ids"],
    }


def _empty_split_score(
    *,
    amount_delta_cents: int,
    date_delta_days: int | None,
    reason: str,
) -> dict[str, object]:
    return {
        "score": 0.0,
        "amount_score": 0.0,
        "date_score": 0.0,
        "description_score": 0.0,
        "split_penalty": 0.0,
        "amount_delta_cents": amount_delta_cents,
        "date_delta_days": date_delta_days,
        "component_count": 0,
        "component_total_cents": 0,
        "component_movement_ids": [],
        "components": [],
        "score_explanation": {
            "reason": reason,
            "reasons": [reason],
        },
    }



def _object_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list")
    return value


def _object_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValidationError(f"{field_name} must be a number")
    return float(value)


def _object_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an integer")
    return value


def _movement_dicts(value: object, field_name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list")
    if not all(isinstance(item, dict) for item in value):
        raise ValidationError(f"{field_name} must contain dictionaries")
    return [dict(item) for item in value]

def _score_split_candidates_with_penalty(
    *,
    bank_row: sqlite3.Row,
    available_movements: list[dict[str, Any]],
    amount_tolerance_cents: int,
    date_window_days: int,
    split_penalty: float,
    max_components: int,
) -> list[dict[str, object]]:
    raw_candidates = find_split_candidates(
        dict(bank_row),
        available_movements,
        amount_tolerance_cents=amount_tolerance_cents,
        date_window_days=date_window_days,
        max_components=max_components,
    )
    movements_by_id = {
        _movement_id(movement): movement for movement in available_movements
    }

    candidates: list[dict[str, object]] = []
    for raw_candidate in raw_candidates:
        components = [
            movements_by_id[str(component_id)]
            for component_id in _object_list(
                raw_candidate["component_movement_ids"],
                "component_movement_ids",
            )
        ]
        candidates.append(
            score_split_candidate(
                dict(bank_row),
                components,
                amount_tolerance_cents=amount_tolerance_cents,
                date_window_days=date_window_days,
                split_penalty=split_penalty,
            )
        )

    candidates.sort(
        key=lambda candidate: (
            -_object_float(candidate.get("score"), "score"),
            abs(_object_int(candidate.get("amount_delta_cents"), "amount_delta_cents")),
            _object_int(candidate.get("date_delta_days"), "date_delta_days"),
            _object_int(candidate.get("component_count"), "component_count"),
            tuple(
                str(value)
                for value in _object_list(
                    candidate.get("component_movement_ids"),
                    "component_movement_ids",
                )
            ),
        )
    )
    return candidates


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
        statement_start_date,
        "statement_start_date",
    )
    statement_end_date = _validate_date(statement_end_date, "statement_end_date")
    if statement_start_date > statement_end_date:
        raise ValidationError("statement_start_date cannot be after statement_end_date")

    _validate_cash_account_exists(connection, cash_account_id)

    if reconciliation_run_id is None:
        reconciliation_run_id = f"recon-run-{uuid.uuid4().hex}"
    else:
        reconciliation_run_id = _validate_nonblank(
            reconciliation_run_id,
            "reconciliation_run_id",
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
            _object_int(movement.get("amount_cents"), "amount_cents"),
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
                            reason=(
                                "duplicate_flagged_bank_transaction_no_"
                                "exact_match"
                            ),
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


def run_fuzzy_reconciliation(
    connection: sqlite3.Connection,
    *,
    cash_account_id: str,
    statement_start_date: date,
    statement_end_date: date,
    reconciliation_run_id: str | None = None,
    started_at: str | None = None,
    amount_tolerance_cents: int = 5,
    date_window_days: int = 3,
    auto_match_threshold: float = 95.0,
    candidate_threshold: float = 80.0,
    ambiguity_gap: float = 10.0,
) -> dict[str, object]:
    """Run fuzzy reconciliation and persist the results."""
    cash_account_id = _validate_nonblank(cash_account_id, "cash_account_id")
    statement_start_date = _validate_date(
        statement_start_date,
        "statement_start_date",
    )
    statement_end_date = _validate_date(statement_end_date, "statement_end_date")
    if statement_start_date > statement_end_date:
        raise ValidationError("statement_start_date cannot be after statement_end_date")

    _validate_fuzzy_thresholds(
        amount_tolerance_cents=amount_tolerance_cents,
        date_window_days=date_window_days,
        auto_match_threshold=auto_match_threshold,
        candidate_threshold=candidate_threshold,
        ambiguity_gap=ambiguity_gap,
    )
    _validate_cash_account_exists(connection, cash_account_id)

    if reconciliation_run_id is None:
        reconciliation_run_id = f"recon-run-{uuid.uuid4().hex}"
    else:
        reconciliation_run_id = _validate_nonblank(
            reconciliation_run_id,
            "reconciliation_run_id",
        )

    if started_at is None:
        started_at = _utc_now()
    else:
        started_at = _validate_nonblank(started_at, "started_at")
    completed_at = _utc_now()
    created_at = completed_at

    config = {
        "algorithm": "fuzzy_amount_date_description",
        "match_types": [MATCH_TYPE_FUZZY, MATCH_TYPE_UNMATCHED],
        "amount_tolerance_cents": amount_tolerance_cents,
        "date_window_days": date_window_days,
        "auto_match_threshold": float(auto_match_threshold),
        "candidate_threshold": float(candidate_threshold),
        "ambiguity_gap": float(ambiguity_gap),
        "description_scoring": True,
        "split_matching": False,
        "duplicate_flagged_rows_auto_match": False,
    }

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

    auto_matched_count = 0
    candidate_count = 0
    ambiguous_count = 0
    unmatched_count = 0
    used_movement_ids: set[str] = set()

    try:
        with connection:
            _insert_fuzzy_run(
                connection,
                reconciliation_run_id=reconciliation_run_id,
                cash_account_id=cash_account_id,
                statement_start_date=statement_start_date,
                statement_end_date=statement_end_date,
                started_at=started_at,
                completed_at=completed_at,
                config=config,
            )

            for index, bank_row in enumerate(bank_transactions, start=1):
                bank_transaction_id = bank_row["bank_transaction_id"]
                bank_amount = int(bank_row["amount_cents"])
                bank_date = _date_value(
                    bank_row["transaction_date"],
                    "transaction_date",
                )
                duplicate_group_id = bank_row["duplicate_group_id"]
                match_id = f"recon-match-{reconciliation_run_id}-{index:05d}"

                candidates = _build_fuzzy_candidates(
                    bank_row=bank_row,
                    bank_date=bank_date,
                    ledger_movements=ledger_movements,
                    used_movement_ids=used_movement_ids,
                    amount_tolerance_cents=amount_tolerance_cents,
                    date_window_days=date_window_days,
                )
                top = candidates[0] if candidates else None
                near = candidates[1] if len(candidates) > 1 else None

                if top is None:
                    match_type = MATCH_TYPE_UNMATCHED
                    status = MATCH_STATUS_UNMATCHED
                    score = 0.0
                    amount_delta = bank_amount
                    date_delta = None
                    ledger_movement_id = None
                    auto_matched = False
                    unmatched_count += 1
                    reason = "No fuzzy candidates were found."
                    score_details = _empty_fuzzy_score(
                        amount_delta_cents=amount_delta,
                        date_delta_days=date_delta,
                        reason=reason,
                    )
                else:
                    top_score = _object_float(top.get("score"), "score")
                    near_score = (
                        _object_float(near.get("score"), "score")
                        if near
                        else None
                    )
                    score_gap = (
                        top_score - near_score
                        if near_score is not None
                        else 100.0
                    )
                    duplicate_flagged = duplicate_group_id is not None

                    if (
                        top_score >= auto_match_threshold
                        and score_gap >= ambiguity_gap
                        and not duplicate_flagged
                    ):
                        match_type = MATCH_TYPE_FUZZY
                        status = MATCH_STATUS_AUTO_MATCHED
                        auto_matched = True
                        auto_matched_count += 1
                        reason = (
                            "Top fuzzy candidate exceeded auto-match "
                            "threshold with a sufficient score gap."
                        )
                    elif top_score >= auto_match_threshold and (
                        score_gap < ambiguity_gap
                    ):
                        match_type = MATCH_TYPE_FUZZY
                        status = MATCH_STATUS_AMBIGUOUS
                        auto_matched = False
                        ambiguous_count += 1
                        reason = (
                            "Top fuzzy candidates were too close to "
                            "auto-match safely."
                        )
                    elif duplicate_flagged and top_score >= candidate_threshold:
                        match_type = MATCH_TYPE_FUZZY
                        status = MATCH_STATUS_CANDIDATE
                        auto_matched = False
                        candidate_count += 1
                        reason = (
                            "Duplicate-flagged bank transaction cannot be "
                            "auto-matched."
                        )
                    elif candidate_threshold <= top_score < auto_match_threshold:
                        match_type = MATCH_TYPE_FUZZY
                        status = MATCH_STATUS_CANDIDATE
                        auto_matched = False
                        candidate_count += 1
                        reason = (
                            "Top fuzzy candidate met candidate threshold "
                            "but not auto-match threshold."
                        )
                    else:
                        match_type = MATCH_TYPE_UNMATCHED
                        status = MATCH_STATUS_UNMATCHED
                        auto_matched = False
                        unmatched_count += 1
                        reason = (
                            "Top fuzzy candidate did not meet candidate "
                            "threshold."
                        )

                    score = top_score if status != MATCH_STATUS_UNMATCHED else 0.0
                    amount_delta = _object_int(
                        top.get("amount_delta_cents"),
                        "amount_delta_cents",
                    )
                    date_delta = _object_int(
                        top.get("date_delta_days"),
                        "date_delta_days",
                    )
                    ledger_movement_id = str(top["ledger_cash_movement_id"])
                    score_details = top

                explanation = build_fuzzy_match_explanation(
                    bank_transaction_id=bank_transaction_id,
                    ledger_cash_movement_id=ledger_movement_id,
                    score_details=score_details,
                    decision_status=status,
                    auto_matched=auto_matched,
                    reason=reason,
                    top_candidate=(
                        _candidate_summary(top)
                        if top is not None
                        else None
                    ),
                    near_candidate=(
                        _candidate_summary(near)
                        if near is not None
                        else None
                    ),
                )
                _insert_match(
                    connection,
                    reconciliation_match_id=match_id,
                    reconciliation_run_id=reconciliation_run_id,
                    bank_transaction_id=bank_transaction_id,
                    match_type=match_type,
                    score=score,
                    amount_delta_cents=amount_delta,
                    date_delta_days=date_delta,
                    status=status,
                    explanation=explanation,
                    created_at=created_at,
                )

                if auto_matched and top is not None:
                    movement = next(
                        item
                        for item in ledger_movements
                        if _movement_id(item) == top["ledger_cash_movement_id"]
                    )
                    _insert_ledger_link(
                        connection,
                        reconciliation_match_id=match_id,
                        movement=movement,
                    )
                    used_movement_ids.add(str(top["ledger_cash_movement_id"]))
    except sqlite3.IntegrityError as exc:
        raise ValidationError("could not save reconciliation results") from exc

    total_matches = (
        auto_matched_count
        + candidate_count
        + ambiguous_count
        + unmatched_count
    )
    return {
        "reconciliation_run_id": reconciliation_run_id,
        "cash_account_id": cash_account_id,
        "statement_start_date": statement_start_date.isoformat(),
        "statement_end_date": statement_end_date.isoformat(),
        "status": RECONCILIATION_RUN_STATUS_COMPLETED,
        "auto_matched_count": auto_matched_count,
        "candidate_count": candidate_count,
        "ambiguous_count": ambiguous_count,
        "unmatched_count": unmatched_count,
        "total_bank_transactions": len(bank_transactions),
        "total_matches": total_matches,
    }


def run_split_reconciliation(
    connection: sqlite3.Connection,
    *,
    cash_account_id: str,
    statement_start_date: date,
    statement_end_date: date,
    reconciliation_run_id: str | None = None,
    started_at: str | None = None,
    amount_tolerance_cents: int = 5,
    date_window_days: int = 3,
    auto_match_threshold: float = 95.0,
    candidate_threshold: float = 80.0,
    ambiguity_gap: float = 10.0,
    split_penalty: float = 5.0,
    max_components: int = 3,
) -> dict[str, object]:
    """Run limited split reconciliation and persist the results."""
    cash_account_id = _validate_nonblank(cash_account_id, "cash_account_id")
    statement_start_date = _validate_date(
        statement_start_date,
        "statement_start_date",
    )
    statement_end_date = _validate_date(statement_end_date, "statement_end_date")
    if statement_start_date > statement_end_date:
        raise ValidationError("statement_start_date cannot be after statement_end_date")

    _validate_split_thresholds(
        amount_tolerance_cents=amount_tolerance_cents,
        date_window_days=date_window_days,
        auto_match_threshold=auto_match_threshold,
        candidate_threshold=candidate_threshold,
        ambiguity_gap=ambiguity_gap,
        split_penalty=split_penalty,
        max_components=max_components,
    )
    _validate_cash_account_exists(connection, cash_account_id)

    if reconciliation_run_id is None:
        reconciliation_run_id = f"recon-run-{uuid.uuid4().hex}"
    else:
        reconciliation_run_id = _validate_nonblank(
            reconciliation_run_id,
            "reconciliation_run_id",
        )

    if started_at is None:
        started_at = _utc_now()
    else:
        started_at = _validate_nonblank(started_at, "started_at")
    completed_at = _utc_now()
    created_at = completed_at

    config = {
        "algorithm": "split_amount_date_description",
        "match_types": [MATCH_TYPE_SPLIT, MATCH_TYPE_UNMATCHED],
        "amount_tolerance_cents": amount_tolerance_cents,
        "date_window_days": date_window_days,
        "auto_match_threshold": float(auto_match_threshold),
        "candidate_threshold": float(candidate_threshold),
        "ambiguity_gap": float(ambiguity_gap),
        "split_penalty": float(split_penalty),
        "max_components": max_components,
        "description_scoring": True,
        "split_matching": True,
        "duplicate_flagged_rows_auto_match": False,
    }

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

    auto_matched_count = 0
    candidate_count = 0
    ambiguous_count = 0
    unmatched_count = 0
    used_movement_ids: set[str] = set()

    try:
        with connection:
            _insert_fuzzy_run(
                connection,
                reconciliation_run_id=reconciliation_run_id,
                cash_account_id=cash_account_id,
                statement_start_date=statement_start_date,
                statement_end_date=statement_end_date,
                started_at=started_at,
                completed_at=completed_at,
                config=config,
            )

            for index, bank_row in enumerate(bank_transactions, start=1):
                bank_transaction_id = bank_row["bank_transaction_id"]
                bank_amount = int(bank_row["amount_cents"])
                duplicate_group_id = bank_row["duplicate_group_id"]
                match_id = f"recon-match-{reconciliation_run_id}-{index:05d}"

                available_movements = [
                    movement
                    for movement in ledger_movements
                    if _movement_id(movement) not in used_movement_ids
                ]
                candidates = _score_split_candidates_with_penalty(
                    bank_row=bank_row,
                    available_movements=available_movements,
                    amount_tolerance_cents=amount_tolerance_cents,
                    date_window_days=date_window_days,
                    split_penalty=split_penalty,
                    max_components=max_components,
                )
                top = candidates[0] if candidates else None
                near = candidates[1] if len(candidates) > 1 else None

                if top is None:
                    match_type = MATCH_TYPE_UNMATCHED
                    status = MATCH_STATUS_UNMATCHED
                    score = 0.0
                    amount_delta = bank_amount
                    date_delta = None
                    auto_matched = False
                    unmatched_count += 1
                    reason = "No split candidates were found."
                    score_details = _empty_split_score(
                        amount_delta_cents=amount_delta,
                        date_delta_days=date_delta,
                        reason=reason,
                    )
                else:
                    top_score = _object_float(top.get("score"), "score")
                    near_score = (
                        _object_float(near.get("score"), "score")
                        if near
                        else None
                    )
                    score_gap = (
                        top_score - near_score
                        if near_score is not None
                        else 100.0
                    )
                    duplicate_flagged = duplicate_group_id is not None

                    if (
                        top_score >= auto_match_threshold
                        and score_gap >= ambiguity_gap
                        and not duplicate_flagged
                    ):
                        match_type = MATCH_TYPE_SPLIT
                        status = MATCH_STATUS_AUTO_MATCHED
                        auto_matched = True
                        auto_matched_count += 1
                        reason = (
                            "Top split candidate exceeded auto-match threshold "
                            "with a sufficient score gap."
                        )
                    elif top_score >= auto_match_threshold and (
                        score_gap < ambiguity_gap
                    ):
                        match_type = MATCH_TYPE_SPLIT
                        status = MATCH_STATUS_AMBIGUOUS
                        auto_matched = False
                        ambiguous_count += 1
                        reason = (
                            "Top split candidates were too close to "
                            "auto-match safely."
                        )
                    elif duplicate_flagged and top_score >= candidate_threshold:
                        match_type = MATCH_TYPE_SPLIT
                        status = MATCH_STATUS_CANDIDATE
                        auto_matched = False
                        candidate_count += 1
                        reason = (
                            "Duplicate-flagged bank transaction cannot be "
                            "auto-matched."
                        )
                    elif candidate_threshold <= top_score < auto_match_threshold:
                        match_type = MATCH_TYPE_SPLIT
                        status = MATCH_STATUS_CANDIDATE
                        auto_matched = False
                        candidate_count += 1
                        reason = (
                            "Top split candidate met candidate threshold "
                            "but not auto-match threshold."
                        )
                    else:
                        match_type = MATCH_TYPE_UNMATCHED
                        status = MATCH_STATUS_UNMATCHED
                        auto_matched = False
                        unmatched_count += 1
                        reason = (
                            "Top split candidate did not meet candidate "
                            "threshold."
                        )

                    score = top_score if status != MATCH_STATUS_UNMATCHED else 0.0
                    amount_delta = _object_int(
                        top.get("amount_delta_cents"),
                        "amount_delta_cents",
                    )
                    date_delta = _object_int(
                        top.get("date_delta_days"),
                        "date_delta_days",
                    )
                    score_details = top

                explanation = build_split_match_explanation(
                    bank_transaction_id=bank_transaction_id,
                    score_details=score_details,
                    decision_status=status,
                    auto_matched=auto_matched,
                    reason=reason,
                    top_candidate=(
                        _split_candidate_summary(top)
                        if top is not None
                        else None
                    ),
                    near_candidate=(
                        _split_candidate_summary(near)
                        if near is not None
                        else None
                    ),
                )
                _insert_match(
                    connection,
                    reconciliation_match_id=match_id,
                    reconciliation_run_id=reconciliation_run_id,
                    bank_transaction_id=bank_transaction_id,
                    match_type=match_type,
                    score=score,
                    amount_delta_cents=amount_delta,
                    date_delta_days=date_delta,
                    status=status,
                    explanation=explanation,
                    created_at=created_at,
                )

                if auto_matched and top is not None:
                    for component in _movement_dicts(top["components"], "components"):
                        _insert_ledger_link(
                            connection,
                            reconciliation_match_id=match_id,
                            movement=component,
                        )
                    used_movement_ids.update(
                        str(value)
                        for value in _object_list(
                            top["component_movement_ids"],
                            "component_movement_ids",
                        )
                    )
    except sqlite3.IntegrityError as exc:
        raise ValidationError("could not save reconciliation results") from exc

    total_matches = (
        auto_matched_count
        + candidate_count
        + ambiguous_count
        + unmatched_count
    )
    return {
        "reconciliation_run_id": reconciliation_run_id,
        "cash_account_id": cash_account_id,
        "statement_start_date": statement_start_date.isoformat(),
        "statement_end_date": statement_end_date.isoformat(),
        "status": RECONCILIATION_RUN_STATUS_COMPLETED,
        "auto_matched_count": auto_matched_count,
        "candidate_count": candidate_count,
        "ambiguous_count": ambiguous_count,
        "unmatched_count": unmatched_count,
        "total_bank_transactions": len(bank_transactions),
        "total_matches": total_matches,
    }


def get_reconciliation_run(
    connection: sqlite3.Connection,
    reconciliation_run_id: str,
) -> dict[str, object] | None:
    """Return one reconciliation run row as a dictionary."""
    reconciliation_run_id = _validate_nonblank(
        reconciliation_run_id,
        "reconciliation_run_id",
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
    connection: sqlite3.Connection,
    reconciliation_run_id: str,
) -> list[dict[str, object]]:
    """Return reconciliation matches for a run in deterministic order."""
    reconciliation_run_id = _validate_nonblank(
        reconciliation_run_id,
        "reconciliation_run_id",
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
    "run_fuzzy_reconciliation",
    "run_split_reconciliation",
]
